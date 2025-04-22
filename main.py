from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query, Header, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from starlette.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from slowapi.middleware import SlowAPIMiddleware
import os
import json
import hmac
import hashlib

from database import init_db, get_company_by_phone, get_db, SessionLocal
from whatsapp import handle_message
from dotenv import load_dotenv

load_dotenv()

DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter

app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"error": "Too many requests"})


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
    if DEBUG_MODE:
        print("⚠️ DEBUG_MODE ativo. Usando empresa fictícia para testes.")
        from database import Company
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
        if not company or not company.webhook_secret:
            raise HTTPException(status_code=404, detail="Company not found")

    if hub_mode == "subscribe" and hub_verify_token == company.verify_token:
        return PlainTextResponse(hub_challenge)
    else:
        raise HTTPException(status_code=403, detail="Invalid verification token")


def verify_signature(app_secret: str, request_body: bytes, signature: str | None):
    if DEBUG_MODE:
        print("⚠️ DEBUG_MODE ativo. Ignorando verificação de assinatura.")
        return

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
@limiter.limit("5/second")  # 5 requisições por segundo por IP
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
):
    raw_body = await request.body()

    try:
        data = json.loads(raw_body)
        phone_number_id = (
            data["entry"][0]["changes"][0]["value"]
            .get("metadata", {})
            .get("phone_number_id")
        )
        if not phone_number_id:
            raise ValueError("Missing phone_number_id")

        company = await get_company_by_phone(phone_number_id)
        if not company:
            raise ValueError("Company not found")

        verify_signature(company.webhook_secret, raw_body, x_hub_signature_256)

    except Exception as e:
        print(f"🔐 Webhook validation failed: {e}")
        raise HTTPException(status_code=403, detail="Unauthorized webhook request")

    await handle_message(data)
    return JSONResponse({"status": "received"})



@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ping-db")
async def ping_db(session: AsyncSession = Depends(get_db)):
    try:
        await session.execute(text("SELECT 1"))
        print("✅ DB connection OK")
        return {"db": "ok"}
    except Exception as e:
        print("❌ DB error:", e)
        return {"db": "error", "detail": str(e)}
