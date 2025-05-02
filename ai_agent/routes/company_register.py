from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse
import os

from database.models import Company
from database.crud import get_db
from utils.crypto import encrypt_value
from whatsapp.zapi import create_zapi_instance

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

# Secret key to protect the form
COMPANY_REGISTRATION_KEY = os.getenv("COMPANY_REGISTRATION_KEY", "your_secret_key")
# Default shared credentials for Meta
DEFAULT_WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
DEFAULT_WEBHOOK_SECRET = os.getenv("WHATSAPP_APP_SECRET")
# Base domain for Z-API callback URLs
BASE_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")

@router.get("/register-company", response_class=HTMLResponse)
async def register_company_form(request: Request, key: str = None):
    if key != COMPANY_REGISTRATION_KEY:
        raise HTTPException(status_code=403, detail="Invalid registration key.")
    return templates.TemplateResponse("register_company.html", {"request": request, "key": key})

@router.post("/register-company", response_class=HTMLResponse)
async def register_company(
    request: Request,
    key: str = Form(...),
    name: str = Form(...),
    display_number: str = Form(...),
    phone_number_id: str = Form(...),
    provider: str = Form(...),
    ai_prompt: str = Form(None),
    tone: str = Form("Formal"),
    language: str = Form("Portuguese"),
    session: AsyncSession = Depends(get_db)
):
    if key != COMPANY_REGISTRATION_KEY:
        raise HTTPException(status_code=403, detail="Invalid registration key.")

    final_prompt = ai_prompt or "Você é um assistente virtual educado e objetivo."

    new_company = Company(
        name=name,
        display_number=display_number,
        phone_number_id=phone_number_id,
        provider=provider,
        ai_prompt=final_prompt,
        tone=tone,
        language=language
    )

    if provider == "meta":
        if not DEFAULT_WHATSAPP_TOKEN or not DEFAULT_WEBHOOK_SECRET:
            raise HTTPException(status_code=500, detail="Meta API credentials are not configured.")
        new_company.whatsapp_token = encrypt_value(DEFAULT_WHATSAPP_TOKEN)
        new_company.webhook_secret = encrypt_value(DEFAULT_WEBHOOK_SECRET)

    elif provider == "zapi":
        if not BASE_DOMAIN:
            raise HTTPException(status_code=500, detail="RAILWAY_PUBLIC_DOMAIN not set.")
        try:
            instance_info = await create_zapi_instance(name, session_name=display_number, callback_base_url=f"https://{BASE_DOMAIN}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create Z-API instance: {str(e)}")

        new_company.zapi_instance_id = encrypt_value(instance_info["instance_id"])
        new_company.zapi_token = encrypt_value(instance_info["token"])

    session.add(new_company)
    await session.commit()

    return templates.TemplateResponse("registration_success.html", {"request": request})

