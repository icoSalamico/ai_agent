from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query, Header, HTTPException
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query, Header, HTTPException
from fastapi.responses import PlainTextResponse
from database import init_db, get_company_by_phone
from dotenv import load_dotenv
import os
import hmac
import hashlib
from whatsapp import handle_message, logger
from starlette.responses import JSONResponse
import json

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def home():
    return {"message": "WhatsApp AI Agent is running!"}


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    phone_number_id: str = Query(...),
):
    company = await get_company_by_phone(phone_number_id)
    if not company:
        return PlainTextResponse("Company not found", status_code=404)

    if hub_mode == "subscribe" and hub_verify_token == company.verify_token:
        return PlainTextResponse(hub_challenge)
    else:
        return PlainTextResponse("Invalid verification token", status_code=403)


def verify_signature(app_secret: str, request_body: bytes, signature: str):
    """Validate X-Hub-Signature-256 using your app secret."""
    if not signature or "=" not in signature:
        raise HTTPException(status_code=403, detail="Missing or invalid signature format")

    signature_hash = signature.split("=")[1]
    expected_hash = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=request_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, signature_hash):
        raise HTTPException(status_code=403, detail="Invalid signature")


@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
):
    raw_body = await request.body()

    # Try to parse JSON and validate structure
    try:
        data = json.loads(raw_body)
        if not isinstance(data.get("entry"), list):
            raise ValueError("Invalid structure: 'entry' must be a list.")
        if not data["entry"][0].get("changes"):
            raise ValueError("Invalid structure: 'changes' missing.")
        if not data["entry"][0]["changes"][0].get("value", {}).get("messages"):
            raise ValueError("Invalid structure: 'messages' missing.")
    except Exception as e:
        logger.warning(f"Malformed webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook structure.")

    # Extract phone_number_id to find the right company
    phone_number_id = (
        data["entry"][0]["changes"][0]["value"]
        .get("metadata", {})
        .get("phone_number_id")
    )

    if not phone_number_id:
        logger.warning("Missing phone_number_id in webhook payload")
        raise HTTPException(status_code=400, detail="Missing phone_number_id")

    company = await get_company_by_phone(phone_number_id)
    if not company or not company.webhook_secret:
        logger.warning(f"Unknown company or missing secret for phone: {phone_number_id}")
        raise HTTPException(status_code=404, detail="Company not found")

    # Validate signature
    if not x_hub_signature_256:
        logger.warning("Missing signature header")
        raise HTTPException(status_code=401, detail="Missing signature")

    expected_signature = "sha256=" + hmac.new(
        key=company.webhook_secret.encode(),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        logger.warning(f"Invalid signature for company {company.name}")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Signature is valid, handle the message
    await handle_message(data)
    return JSONResponse({"status": "received"})


@app.get("/health")
def health():
    return {"status": "ok"}
