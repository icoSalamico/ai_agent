from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query, Header, HTTPException, Depends, Response
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import json
import hmac
import hashlib
import logging

from database.core import init_db, SessionLocal
from database.crud import get_company_by_phone, get_db
from services.whatsapp import handle_message
from dependencies.security import verify_admin_key
from dependencies.security import verify_signature

from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

limiter = Limiter(key_func=get_remote_address)


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SecureHeadersMiddleware)
app.add_middleware(HTTPSRedirectMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


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
    from database.models import Company

    if DEBUG_MODE:
        logger.info("⚠️ DEBUG_MODE ativo. Usando empresa fictícia para testes.")
        company = Company(
            id=999,
            name="Debug Company",
            phone_number_id="test-id",
            ai_prompt="You are a test assistant.",
            language="Portuguese",
            tone="Informal",
            whatsapp_token="test",
            verify_token="test",
            webhook_secret="test"
        )
    else:
        company = await get_company_by_phone(phone_number_id)
        if not company or not company.decrypted_webhook_secret:
            logger.warning("Company not found for phone_number_id: %s", phone_number_id)
            raise HTTPException(status_code=404, detail="Company not found")

    if hub_mode == "subscribe" and hub_verify_token == company.verify_token:
        return PlainTextResponse(hub_challenge)
    else:
        raise HTTPException(status_code=403, detail="Invalid verification token")


@app.post("/webhook")
@limiter.limit("5/minute")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
):
    raw_body = await request.body()

    try:
        data = json.loads(raw_body)
        if not isinstance(data.get("entry"), list):
            raise ValueError("Invalid structure: 'entry' must be a list.")
        if not data["entry"][0].get("changes"):
            raise ValueError("Invalid structure: 'changes' missing.")
        if not data["entry"][0]["changes"][0].get("value", {}).get("messages"):
            raise ValueError("Invalid structure: 'messages' missing.")
    except Exception as e:
        logger.error("Error parsing webhook data: %s", e)
        raise HTTPException(status_code=400, detail="Invalid webhook structure.")

    phone_number_id = (
        data["entry"][0]["changes"][0]["value"]
        .get("metadata", {})
        .get("phone_number_id")
    )

    if not phone_number_id:
        logger.warning("Missing phone_number_id in webhook data")
        raise HTTPException(status_code=400, detail="Missing phone_number_id")

    company = await get_company_by_phone(phone_number_id)
    if not company or not company.decrypted_webhook_secret:
        logger.warning("Company not found for phone_number_id: %s", phone_number_id)
        raise HTTPException(status_code=404, detail="Company not found")

    verify_signature(company.decrypted_webhook_secret, raw_body, x_hub_signature_256)
    await handle_message(data)
    return JSONResponse({"status": "received"})


@app.get("/ping-db", dependencies=[Depends(verify_admin_key)])
async def ping_db(session: AsyncSession = Depends(get_db)):
    try:
        await session.execute(text("SELECT 1"))
        logger.info("✅ DB connection OK")
        return {"db": "ok"}
    except Exception as e:
        logger.error("❌ DB error: %s", e)
        return {"db": "error", "detail": str(e)}


@app.get("/health")
def health():
    return {"status": "ok"}
