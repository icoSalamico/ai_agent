from fastapi import APIRouter, Request, Header, HTTPException, Depends
from starlette.responses import JSONResponse
from sqlalchemy import select
import os
import json
import traceback
import logging

from database import get_company_by_display_number, get_company_by_phone, get_company_by_instance_id
from ai_agent.utils.signature import verify_signature
from ai_agent.utils.debug import get_debug_company
from database.models import Conversation, ClientSession
from ai_agent.services.ai import generate_response
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import get_db
from whatsapp.provider_factory import get_provider
from utils.crypto import decrypt_value


webhook_router = APIRouter()
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

logger = logging.getLogger(__name__)


@webhook_router.post("/webhook")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    raw_body = await request.body()
    try:
        data = json.loads(raw_body)
        print("📨 Payload recebido:")
        print(json.dumps(data, indent=2))

        for key, value in data.items():
            print(f"🔍 {key} => {type(value).__name__}")

        if "entry" in data:
            phone_number_id = data["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]
            from_number = message["from"]
            user_message = message["text"]["body"]
            provider_type = "meta"

        elif "messages" in data:
            message = data["messages"][0]
            from_number = message["from"]
            user_message = message["text"]["body"]
            phone_number_id = None
            provider_type = "zapi"

        elif "event" in data and data["event"] == "message" and "message" in data:
            message = data["message"]
            from_number = message["from"]
            user_message = message["text"]
            phone_number_id = None
            provider_type = "zapi"

        elif data.get("type") == "ReceivedCallback":
            if (
                data.get("fromMe") is False
                and "text" in data
                and isinstance(data["text"], dict)
                and "message" in data["text"]
            ):
                from_number = data["phone"]
                user_message = data["text"]["message"]
                phone_number_id = None
                provider_type = "zapi"
            else:
                return JSONResponse({"status": "ignored", "reason": "non-user message or system notification"})

        else:
            raise ValueError("Unrecognized webhook payload format.")

    except Exception as e:
        print("📎 Erro ao processar o payload:")
        print(traceback.format_exc())
        logger.exception("💥 Unhandled Exception")
        raise HTTPException(status_code=500, detail=f"Unhandled error: {str(e)}")

    if DEBUG_MODE:
        company = get_debug_company()
    else:
        if provider_type == "meta":
            company = await get_company_by_phone(phone_number_id)
        else:
            instance_id = data.get("instanceId")
            company = await get_company_by_instance_id(instance_id, db)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not DEBUG_MODE and provider_type == "meta":
        verify_signature(company.decrypted_webhook_secret, raw_body, x_hub_signature_256)

    if not DEBUG_MODE:
        if not company.active:
            return JSONResponse({"status": "ignored", "reason": "company deactivated"})

        result = await db.execute(
            select(ClientSession).where(
                ClientSession.company_id == company.id,
                ClientSession.phone_number == from_number
            )
        )
        session = result.scalar_one_or_none()

        command = user_message.strip().lower()
        if command in ["/humano", "!humano", "#humano"]:
            if session:
                session.ai_enabled = False
            else:
                session = ClientSession(company_id=company.id, phone_number=from_number, ai_enabled=False)
                db.add(session)
            await db.commit()
            return JSONResponse({"status": "AI disabled for this user"})

        if command in ["/ia", "!ia", "#ia"]:
            if session:
                session.ai_enabled = True
                await db.commit()
                return JSONResponse({"status": "AI re-enabled for this user"})
            else:
                return JSONResponse({"status": "AI already active by default"})

        if session and not session.ai_enabled:
            return JSONResponse({"status": "ignored", "reason": "AI disabled for this user"})

    ai_response = await generate_response(
        user_input=user_message,
        prompt=company.ai_prompt or "Você é um assistente virtual educado e objetivo.",
        language=company.language or "Portuguese",
        tone=company.tone or "formal"
    ) if not DEBUG_MODE else "🧪 [DEBUG] This is a test response."

    if not DEBUG_MODE:
        db.add(Conversation(
            company_id=company.id,
            phone_number=from_number,
            user_message=user_message,
            ai_response=ai_response
        ))
        await db.commit()

        try:
            whatsapp_token = decrypt_value(company.whatsapp_token) if company.whatsapp_token else ""
            zapi_instance_id = decrypt_value(company.zapi_instance_id) if company.zapi_instance_id else ""
            zapi_token = decrypt_value(company.zapi_token) if company.zapi_token else ""
        except Exception as e:
            print("❗ Erro ao descriptografar credenciais:", str(e))
            raise HTTPException(status_code=500, detail="Erro ao descriptografar credenciais do provedor")

        print("🔧 Provider setup:")
        print("Instance ID:", zapi_instance_id)
        print("API Token:", zapi_token)

        provider = get_provider(company.provider, {
            "token": company.whatsapp_token,
            "phone_number_id": company.phone_number_id,
            "instance_id": company.zapi_instance_id,
            "api_token": company.zapi_token
        })
        await provider.send_message(phone_number=from_number, message=ai_response)
    else:
        print("🧪 DEBUG_MODE enabled. Skipping DB insert, provider setup, and message sending.")

    return JSONResponse({"status": "received"})


@webhook_router.post("/webhook/delivery")
async def delivery_status(request: Request):
    data = await request.json()
    print("🚚 Delivery status received:", json.dumps(data, indent=2))
    return {"status": "ok"}


@webhook_router.post("/webhook/connected")
async def connected_status(request: Request):
    data = await request.json()
    print("🔌 Connected status received:", json.dumps(data, indent=2))
    return {"status": "ok"}


@webhook_router.post("/webhook/disconnected")
async def disconnected_status(request: Request):
    data = await request.json()
    print("❌ Disconnected status received:", json.dumps(data, indent=2))
    return {"status": "ok"}


@webhook_router.post("/webhook/status")
async def message_status(request: Request):
    data = await request.json()
    print("📊 Message status received:", json.dumps(data, indent=2))
    return {"status": "ok"}