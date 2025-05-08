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
from google_calendar.scheduler import MeetingScheduler
from google_calendar.session_state import MeetingSessionState

webhook_router = APIRouter()
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
logger = logging.getLogger(__name__)
session_states = {}


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

    # Google Calendar logic
    if "agendar reunião" in user_message.lower():
        scheduler = MeetingScheduler(company.id)
        slots = await scheduler.suggest_slots()
        session_states[from_number] = MeetingSessionState(company.id, from_number)
        session_states[from_number].last_suggested_slots = slots

        formatted = "\n".join([f"{i+1}. {s['start'][11:16]} às {s['end'][11:16]}" for i, s in enumerate(slots)])
        ai_response = f"Claro! Aqui estão algumas opções:\n{formatted}\nResponda com o horário desejado para confirmar."

    elif from_number in session_states:
        state = session_states[from_number]
        scheduler = MeetingScheduler(company.id)
        status, slot = await scheduler.handle_user_response(user_message, state.last_suggested_slots)

        if status == "confirm":
            await scheduler.schedule_event(slot)
            ai_response = f"✅ Sua reunião foi marcada para {slot['start'][11:16]}"
            del session_states[from_number]
        elif status == "retry":
            state.advance_window()
            new_slots = await scheduler.suggest_slots()
            state.last_suggested_slots = new_slots
            formatted = "\n".join([f"{i+1}. {s['start'][11:16]} às {s['end'][11:16]}" for i, s in enumerate(new_slots)])
            ai_response = f"Sem problemas. Que tal essas novas opções?\n{formatted}"
        elif status == "abort":
            ai_response = "Tudo bem, deixaremos para outro momento."
            del session_states[from_number]
        else:
            ai_response = "Desculpe, não entendi. Você pode repetir o horário desejado?"

    else:
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
