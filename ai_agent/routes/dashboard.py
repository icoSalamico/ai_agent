from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.status import HTTP_303_SEE_OTHER

from database.crud import get_db
from database.models import Company
from utils.crypto import encrypt_value, decrypt_value
from whatsapp.meta_cloud import MetaCloudProvider  # or a unified provider in future

import os

admin_router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

MY_COMPANY_PHONE = os.getenv("MY_COMPANY_PHONE")
MY_COMPANY_TOKEN = os.getenv("MY_COMPANY_TOKEN")
MY_COMPANY_PHONE_ID = os.getenv("MY_COMPANY_PHONE_ID")
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")

@admin_router.get("/dashboard", response_class=HTMLResponse)
async def view_company_settings(request: Request, token: str = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company))
    for company in result.scalars():
        if decrypt_value(company.verify_token) == token:
            return templates.TemplateResponse("dashboard.html", {"request": request, "company": company})
    raise HTTPException(status_code=403, detail="Invalid or missing token")


@admin_router.post("/dashboard/update", response_class=HTMLResponse)
async def update_company_settings(
    request: Request,
    company_id: int = Form(...),
    token: str = Form(...),
    ai_prompt: str = Form(...),
    tone: str = Form(...),
    language: str = Form(...),
    active: bool = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if decrypt_value(company.verify_token) != token:
        raise HTTPException(status_code=403, detail="Invalid token")

    company.ai_prompt = ai_prompt
    company.tone = tone
    company.language = language
    company.active = active

    await db.commit()
    return RedirectResponse(url=f"/dashboard?token={token}", status_code=HTTP_303_SEE_OTHER)


@admin_router.post("/notify-dashboard-url")
async def notify_dashboard_url(company_id: int = Form(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    dashboard_url = f"https://{RAILWAY_PUBLIC_DOMAIN}/dashboard?token={decrypt_value(company.verify_token)}"
    message = f"Este é o link para editar algumas configurações da sua empresa no nosso sistema: {dashboard_url}"

    provider = MetaCloudProvider(token=MY_COMPANY_TOKEN, phone_number_id=MY_COMPANY_PHONE_ID)
    await provider.send_message(phone_number=company.phone_number_id, message=message)

    return {"detail": "Dashboard link sent to company."}
