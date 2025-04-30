# routes/webhook.py
from fastapi import APIRouter, Request, Header, HTTPException, Query, Depends
from starlette.responses import PlainTextResponse, JSONResponse
import os
import json
import traceback

from database import get_company_by_phone
from ai_agent.utils.signature import verify_signature
from ai_agent.utils.debug import get_debug_company
from database.models import Conversation
from ai_agent.services.ai import generate_response
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import get_db
from whatsapp.provider_factory import get_provider

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
        print("📛 Erro ao processar o payload:")
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


