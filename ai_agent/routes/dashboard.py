from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.status import HTTP_303_SEE_OTHER
from cryptography.fernet import Fernet
import os

from database.crud import get_db
from database.models import Company
from whatsapp.meta_cloud import MetaCloudProvider

# Set up encryption/decryption
FERNET_SECRET_KEY = os.getenv("FERNET_SECRET_KEY")
fernet = Fernet(FERNET_SECRET_KEY.encode())

def decrypt_value(value: str) -> str:
    return fernet.decrypt(value.encode()).decode()

def encrypt_value(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()

# FastAPI and template setup
admin_router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

MY_COMPANY_PHONE = os.getenv("MY_COMPANY_PHONE")
MY_COMPANY_TOKEN = os.getenv("MY_COMPANY_TOKEN")
MY_COMPANY_PHONE_ID = os.getenv("MY_COMPANY_PHONE_ID")
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")

@admin_router.get("/dashboard", response_class=HTMLResponse)
async def view_company_settings(request: Request, token: str = Query(...), db: AsyncSession = Depends(get_db)):
    print(f"🔑 Received token: '{token}'")

    result = await db.execute(select(Company))
    for company in result.scalars():
        try:
            decrypted = decrypt_value(company.verify_token).strip()
            print(f"🔍 Comparing decrypted: '{decrypted}' == '{token.strip()}'")
            if decrypted == token.strip():
                print(f"✅ Token matched for company: {company.name}")
                return templates.TemplateResponse(
                    "dashboard.html",
                    {
                        "request": request,
                        "company": company,
                        "decrypted_token": decrypted
                    }
                )
        except Exception as e:
            print(f"⚠️ Could not decrypt token for {company.name}: {e}")
            continue

    raise HTTPException(status_code=403, detail="Invalid or missing token")


@admin_router.post("/dashboard/update", response_class=HTMLResponse)
async def update_company_settings(
    request: Request,
    company_id: int = Form(...),
    ai_prompt: str = Form(...),
    tone: str = Form(...),
    language: str = Form(...),
    active: str = Form(None),
    token: str = Form(...),  # still used for redirect
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.ai_prompt = ai_prompt
    company.tone = tone
    company.language = language
    company.active = active == "on"

    await db.commit()
    return RedirectResponse(url=f"/dashboard?token={token}", status_code=HTTP_303_SEE_OTHER)



@admin_router.post("/notify-dashboard-url")
async def notify_dashboard_url(company_id: int = Form(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if not company.verify_token:
        raise HTTPException(status_code=400, detail="Company has no verify token")

    dashboard_url = f"https://{RAILWAY_PUBLIC_DOMAIN}/dashboard?token={decrypt_value(company.verify_token).strip()}"
    message = f"Este é o link para editar algumas configurações da sua empresa no nosso sistema: {dashboard_url}"

    provider = MetaCloudProvider(token=MY_COMPANY_TOKEN, phone_number_id=MY_COMPANY_PHONE_ID)
    await provider.send_message(phone_number=company.phone_number_id, message=message)

    return {"detail": "Dashboard link sent to company."}
