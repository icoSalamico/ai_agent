from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import os

from database import init_db, get_company_by_phone
from whatsapp import handle_message

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic for FastAPI app."""
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def home() -> dict:
    """Root endpoint for health check."""
    return {"message": "WhatsApp AI Agent is running!"}


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    phone_number_id: str = Query(...),
) -> PlainTextResponse:
    """
    Verify webhook for WhatsApp Cloud API.

    Meta (GET) request used to verify connection.
    """
    company = await get_company_by_phone(phone_number_id)
    if not company:
        return PlainTextResponse("Company not found", status_code=404)
    
    if hub_mode == "subscribe" and hub_verify_token == company.verify_token:
        return PlainTextResponse(hub_challenge)
    
    return PlainTextResponse("Invalid verification token", status_code=403)


@app.post("/webhook")
async def receive_webhook(request: Request) -> dict:
    """
    Handle incoming webhook events from WhatsApp.
    """
    data = await request.json()
    await handle_message(data)
    return {"status": "received"}
