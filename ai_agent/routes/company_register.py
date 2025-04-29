from fastapi import APIRouter, Request, Form, Depends, HTTPException # type: ignore
from fastapi.responses import RedirectResponse # type: ignore
from fastapi.templating import Jinja2Templates # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse
import os

from database.models import Company
from database.crud import get_db
from utils.crypto import encrypt_value
from ai_agent.utils.email import send_admin_notification

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

# Secret key to protect the form
COMPANY_REGISTRATION_KEY = os.getenv("COMPANY_REGISTRATION_KEY", "your_secret_key")

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
    phone_number_id: str = Form(...),
    whatsapp_token: str = Form(...),
    webhook_secret: str = Form(...),
    ai_prompt: str = Form(None),
    tone: str = Form("Formal"),
    language: str = Form("Portuguese"),
    session: AsyncSession = Depends(get_db)
):
    if key != COMPANY_REGISTRATION_KEY:
        raise HTTPException(status_code=403, detail="Invalid registration key.")

    # Create and save the new company
    new_company = Company(
        name=name,
        phone_number_id=phone_number_id,
        whatsapp_token=encrypt_value(whatsapp_token),
        webhook_secret=encrypt_value(webhook_secret),
        ai_prompt=ai_prompt,
        tone=tone,
        language=language,
    )
    session.add(new_company)
    await session.commit()

    await send_admin_notification({
        "name": name,
        "phone_number_id": phone_number_id,
        "language": language,
        "tone": tone,
        "ai_prompt": ai_prompt
    })

    return templates.TemplateResponse("registration_success.html", {"request": request})

