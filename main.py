from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from database import init_db, get_company_by_phone
from dotenv import load_dotenv
import os
from whatsapp import handle_message, send_reply

load_dotenv()
app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


@app.get("/")
def home():
    return {"message": "WhatsApp AI Agent is running!"}


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = "",
    hub_challenge: str = "",
    hub_verify_token: str = "",
    phone_number_id: str = ""
):
    company = await get_company_by_phone(phone_number_id)
    if not company:
        return PlainTextResponse("Company not found", status_code=404)
    
    if hub_mode == "subscribe" and hub_verify_token == company.verify_token:
        return PlainTextResponse(hub_challenge)
    else:
        return PlainTextResponse("Invalid verification token", status_code=403)
    

@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    await handle_message(data)
    return {"status": "received"}