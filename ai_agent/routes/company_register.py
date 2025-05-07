from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.responses import HTMLResponse
import os
import secrets

from database.models import Company, ZApiInstance
from database.crud import get_db
from utils.crypto import encrypt_value, decrypt_value
from whatsapp.zapi import get_instance_qrcode  # ✅ função para buscar QR Code
from ai_agent.routes.dashboard import send_dashboard_link

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

COMPANY_REGISTRATION_KEY = os.getenv("COMPANY_REGISTRATION_KEY", "your_secret_key")
DEFAULT_WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
DEFAULT_WEBHOOK_SECRET = os.getenv("WHATSAPP_APP_SECRET")
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
    phone_number_id: str = Form(None),
    provider: str = Form("zapi"),
    ai_prompt: str = Form(None),
    tone: str = Form("Formal"),
    language: str = Form("Portuguese"),
    session: AsyncSession = Depends(get_db)
):
    if key != COMPANY_REGISTRATION_KEY:
        raise HTTPException(status_code=403, detail="Invalid registration key.")

    if provider == "meta" and not phone_number_id:
        raise HTTPException(status_code=422, detail="Phone Number ID is required for Meta provider.")

    final_prompt = ai_prompt or "Você é um assistente virtual educado e objetivo."
    verify_token = secrets.token_urlsafe(32)

    new_company = Company(
        name=name,
        display_number=display_number,
        provider=provider,
        ai_prompt=final_prompt,
        tone=tone,
        language=language,
        verify_token=encrypt_value(verify_token),
        phone_number_id=phone_number_id
    )

    qrcode = None

    if provider == "meta":
        if not DEFAULT_WHATSAPP_TOKEN or not DEFAULT_WEBHOOK_SECRET:
            raise HTTPException(status_code=500, detail="Meta API credentials are not configured.")
        new_company.whatsapp_token = encrypt_value(DEFAULT_WHATSAPP_TOKEN)
        new_company.webhook_secret = encrypt_value(DEFAULT_WEBHOOK_SECRET)

    elif provider == "zapi":
        if not BASE_DOMAIN:
            raise HTTPException(status_code=500, detail="RAILWAY_PUBLIC_DOMAIN not set.")

        result = await session.execute(
            select(ZApiInstance).where(ZApiInstance.assigned == False)
        )
        instance = result.scalars().first()

        if not instance:
            raise HTTPException(status_code=500, detail="No available Z-API instance.")

        instance.assigned = True
        session.add(instance)

        def is_encrypted(value: str) -> bool:
            return isinstance(value, str) and value.startswith("gAAAAA")

        new_company.zapi_instance_id = instance.instance_id if is_encrypted(instance.instance_id) else encrypt_value(instance.instance_id)
        new_company.zapi_token = instance.token if is_encrypted(instance.token) else encrypt_value(instance.token)

    session.add(new_company)
    await session.commit()

    if provider == "zapi":
        instance_id = decrypt_value(new_company.zapi_instance_id)
        api_token = decrypt_value(new_company.zapi_token)
        try:
            qrcode = await get_instance_qrcode(instance_id, api_token)
        except Exception as e:
            print("⚠️ Failed to fetch QR Code:", str(e))
            qrcode = None

    await send_dashboard_link(new_company)

    print("✅ Instância ID (descriptografada):", decrypt_value(new_company.zapi_instance_id))
    print("✅ QR Code final:", qrcode)
    print("📸 QR CODE RETORNADO:", qrcode)
    print("👀 QRCode tipo:", type(qrcode))
    print("🔗 QRCode valor:", qrcode)   
    return templates.TemplateResponse("registration_success.html", {
        "request": request,
        "qrcode": qrcode
    })
