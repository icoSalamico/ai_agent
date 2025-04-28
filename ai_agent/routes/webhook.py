from fastapi import APIRouter, Request, Header, HTTPException, Query
from starlette.responses import PlainTextResponse, JSONResponse
from database.crud import get_company_by_phone, get_company_by_verify_token
from ai_agent.utils.signature import verify_signature
from ai_agent.utils.debug import get_debug_company
from ai_agent.services.whatsapp import handle_message
import logging
import json
import os

webhook_router = APIRouter()

DEBUG_MODE = os.getenv("DEBUG_MODE", "False") == "True"

logger = logging.getLogger(__name__)  # Use FastAPI logger

@webhook_router.get("/webhook")
async def verify_webhook(
    request: Request,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    phone_number_id: str = Query(None),
):
    logger.info("📨 Received webhook verification request with params:")
    logger.info(f"  hub.mode = {hub_mode}")
    logger.info(f"  hub.challenge = {hub_challenge}")
    logger.info(f"  hub.verify_token = {hub_verify_token}")
    logger.info(f"  phone_number_id = {phone_number_id}")

    if not hub_mode or not hub_challenge or not hub_verify_token or not phone_number_id:
        logger.warning("❌ Missing required verification query parameters.")
        raise HTTPException(status_code=400, detail="Missing query parameters.")

    company = get_debug_company() if DEBUG_MODE else await get_company_by_phone(phone_number_id)
    if not company:
        logger.warning(f"❌ Company not found for phone_number_id: {phone_number_id}")
        raise HTTPException(status_code=404, detail="Company not found.")

    if hub_verify_token != company.decrypted_verify_token:
        logger.warning(f"❌ Invalid verify token. Received: {hub_verify_token}, Expected: {company.decrypted_verify_token}")
        raise HTTPException(status_code=403, detail="Invalid verification token.")

    logger.info("✅ Webhook verified successfully! Returning challenge...")
    return PlainTextResponse(hub_challenge)


@webhook_router.post("/webhook")
async def receive_webhook(request: Request, x_hub_signature_256: str = Header(None)):
    raw_body = await request.body()

    try:
        data = json.loads(raw_body)
        phone_number_id = data["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook structure")

    company = get_debug_company() if DEBUG_MODE else await get_company_by_phone(phone_number_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not DEBUG_MODE:
        verify_signature(company.decrypted_webhook_secret, raw_body, x_hub_signature_256)

    await handle_message(data)
    return JSONResponse({"status": "received"})