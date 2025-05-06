from fastapi import APIRouter, Request, Header, HTTPException, Depends
from starlette.responses import JSONResponse
import os
import json
import traceback

from database import get_company_by_phone
from ai_agent.utils.signature import verify_signature
from ai_agent.utils.debug import get_debug_company
from database.models import Conversation, ClientSession
from ai_agent.services.ai import generate_response
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import get_db
from whatsapp.provider_factory import get_provider
from sqlalchemy import select

webhook_router = APIRouter()
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"


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

        # Meta (Cloud API)
        if "entry" in data:
            phone_number_id = data["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]
            from_number = message["from"]
            user_message = message["text"]["body"]
            provider_type = "meta"

        # Z-API: formato clássico
        elif "messages" in data:
            message = data["messages"][0]
            from_number = message["from"]
            user_message = message["text"]["body"]
            phone_number_id = None
            provider_type = "zapi"

        # Z-API: formato com "event": "message"
        elif "event" in data and data["event"] == "message" and "message" in data:
            message = data["message"]
            from_number = message["from"]
            user_message = message["text"]
            phone_number_id = None
            provider_type = "zapi"

        # ✅ Z-API: formato real que você recebeu
        elif data.get("type") == "ReceivedCallback" and "text" in data:
            from_number = data["phone"]
            user_message = data["text"]["message"]
            phone_number_id = None
            provider_type = "zapi"

        else:
            raise ValueError("Unrecognized webhook payload format.")

    except Exception as e:
        print("📎 Erro ao processar o payload:")
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Invalid webhook structure: {e}")

    # Get company
    if DEBUG_MODE:
        company = get_debug_company()
    else:
        if provider_type == "meta":
            company = await get_company_by_phone(phone_number_id)
        else:
            company = await get_company_by_phone(from_number)

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

    ai_response = await generate_response(company, user_message) if not DEBUG_MODE else "🧪 [DEBUG] This is a test response."

    if not DEBUG_MODE:
        db.add(Conversation(
            company_id=company.id,
            phone_number=from_number,
            user_message=user_message,
            ai_response=ai_response
        ))
        await db.commit()

        provider = get_provider(company.provider, {
            "token": company.decrypted_whatsapp_token,
            "phone_number_id": company.phone_number_id,
            "instance_id": company.decrypted_zapi_instance_id,
            "api_token": company.decrypted_zapi_token
        })
        await provider.send_message(phone_number=from_number, message=ai_response)
    else:
        print("🧪 DEBUG_MODE enabled. Skipping DB insert, provider setup, and message sending.")

    return JSONResponse({"status": "received"})


# --- Additional endpoints for Z-API events ---
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
