from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from database import get_db
from database.models import Company
from utils.crypto import encrypt_value
import uuid
import os

router = APIRouter()

# --- SECURITY ---
async def verify_admin_key(request: Request):
    admin_key = request.headers.get("x-admin-key")
    if not admin_key or admin_key != os.getenv("ADMIN_API_KEY", "admin123"):  # Define ADMIN_API_KEY in .env
        raise HTTPException(status_code=401, detail="Unauthorized")

# --- Request Body Model ---
class CompanyCreateRequest(BaseModel):
    name: str
    phone_number_id: str
    whatsapp_token: str
    verify_token: str
    webhook_secret: str
    ai_prompt: str = "You are an assistant."
    language: str = "Portuguese"
    tone: str = "Friendly"

# --- Route ---
@router.post("/admin/create-company", dependencies=[Depends(verify_admin_key)])
async def create_company(company_data: CompanyCreateRequest, session: AsyncSession = Depends(get_db)):
    try:
        new_company = Company(
            name=company_data.name,
            phone_number_id=company_data.phone_number_id,
            whatsapp_token=encrypt_value(company_data.whatsapp_token),
            verify_token=encrypt_value(company_data.verify_token),
            webhook_secret=encrypt_value(company_data.webhook_secret),
            ai_prompt=company_data.ai_prompt,
            language=company_data.language,
            tone=company_data.tone,
        )
        session.add(new_company)
        await session.commit()
        await session.refresh(new_company)
        return {"message": "Company created successfully", "company_id": new_company.id}
    
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
