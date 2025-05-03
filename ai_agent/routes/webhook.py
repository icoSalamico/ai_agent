from fastapi import APIRouter, Request, Header, HTTPException, Query, Depends
from starlette.responses import PlainTextResponse, JSONResponse
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

        # Meta-style structure (has metadata)
        if "entry" in data:
            phone_number_id = data["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]
            from_number = message["from"]
            user_message = message["text"]["body"]
            provider_type = "meta"
        # Z-Api structure (has message directly)
        elif "messages" in data:
            message = data["messages"][0]
            from_number = message["from"]
            user_message = message["text"]["body"]
            phone_number_id = None  # Not used here
            provider_type = "zapi"
        else:
            raise ValueError("Unrecognized webhook payload format.")

    except Exception as e:
        print("\ud83d\udccb Erro ao processar o payload:")
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Invalid webhook structure: {e}")

    # Lookup company
    if DEBUG_MODE:
        company = get_debug_company()
    else:
        if provider_type == "meta":
            company = await get_company_by_phone(phone_number_id)
        else:
            company = await get_company_by_phone(from_number)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Only Meta needs signature verification
    if not DEBUG_MODE and provider_type == "meta":
        verify_signature(company.decrypted_webhook_secret, raw_body, x_hub_signature_256)

    # 🔒 AI Deactivation logic
    if not DEBUG_MODE:
        # Check company-wide activation
        if not company.active:
            return JSONResponse({"status": "ignored", "reason": "company deactivated"})

        # Check per-client deactivation
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

    # Get AI response
    ai_response = await generate_response(company, user_message) if not DEBUG_MODE else "🧪 [DEBUG] This is a test response."

    # Save and respond
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
