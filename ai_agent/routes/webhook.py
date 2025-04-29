# routes/webhook.py
from fastapi import APIRouter, Request, Header, HTTPException, Query # type: ignore
from starlette.responses import PlainTextResponse, JSONResponse
import os
import json

from database import get_company_by_phone
from ai_agent.utils.signature import verify_signature
from ai_agent.utils.debug import get_debug_company
from ai_agent.services.whatsapp import handle_message

webhook_router = APIRouter()

DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

@webhook_router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    print(f"🔵 VERIFY: hub_mode={hub_mode}, hub_challenge={hub_challenge}, hub_verify_token={hub_verify_token}")

    # In debug mode, skip DB
    company = get_debug_company()

    # Check token
    if hub_mode == "subscribe" and hub_verify_token == company.decrypted_verify_token:
        print("✅ Token matched. Returning challenge.")
        return PlainTextResponse(hub_challenge)
    else:
        print("❌ Invalid token.")
        raise HTTPException(status_code=403, detail="Invalid verification token")


@webhook_router.post("/webhook")
async def receive_webhook(request: Request, x_hub_signature_256: str = Header(None)):
    raw_body = await request.body()
    try:
        data = json.loads(raw_body)
        phone_number_id = data["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook structure: {e}")

    company = get_debug_company() if DEBUG_MODE else await get_company_by_phone(phone_number_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not DEBUG_MODE:
        verify_signature(company.decrypted_webhook_secret, raw_body, x_hub_signature_256)

    await handle_message(data)
    return JSONResponse({"status": "received"})
