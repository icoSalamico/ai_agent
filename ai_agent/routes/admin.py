from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from database.models import Conversation, Company
from database.crud import get_db
from dependencies.security import verify_admin_key
from pydantic import BaseModel
from typing import Optional, List
from utils.crypto import encrypt_value

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_admin_key)]
)

@router.get("/companies/{company_id}/conversations")
async def get_conversations(company_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.company_id == company_id)
        .order_by(Conversation.timestamp.desc())
    )
    conversations = result.scalars().all()
    return [
        {
            "user_message": c.user_message,
            "ai_response": c.ai_response,
            "timestamp": c.timestamp
        } for c in conversations
    ]

@router.get("/companies/{company_id}/status")
async def get_company_status(company_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return {
        "id": company.id,
        "name": company.name,
        "phone_number_id": company.phone_number_id,
        "language": company.language,
        "tone": company.tone,
        "business_hours": company.business_hours,
    }

@router.get("/companies")
async def list_companies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).order_by(Company.id))
    companies = result.scalars().all()
    return [
        {
            "id": company.id,
            "name": company.name,
            "phone_number_id": company.phone_number_id,
            "language": company.language,
            "tone": company.tone,
            "business_hours": company.business_hours,
        } for company in companies
    ]

class CompanyUpdate(BaseModel):
    ai_prompt: Optional[str]
    language: Optional[str]
    tone: Optional[str]
    business_hours: Optional[str]

@router.patch("/companies/{company_id}")
async def update_company(company_id: int, update: CompanyUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    for field, value in update.dict(exclude_unset=True).items():
        setattr(company, field, value)

    await db.commit()
    return {"message": "Company updated successfully"}

@router.delete("/companies/{company_id}")
async def delete_company(company_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    await db.delete(company)
    await db.commit()
    return {"message": "Company deleted successfully"}

class CompanyCreate(BaseModel):
    name: str
    phone_number_id: str
    whatsapp_token: str
    verify_token: str
    ai_prompt: str
    language: Optional[str] = "Portuguese"
    tone: Optional[str] = "Formal"
    business_hours: Optional[str]
    webhook_secret: str

@router.post("/companies")
async def create_company(company: CompanyCreate, db: AsyncSession = Depends(get_db)):
    new_company = Company(
        name=company.name,
        phone_number_id=company.phone_number_id,
        whatsapp_token=encrypt_value(company.whatsapp_token),
        verify_token=encrypt_value(company.verify_token),
        ai_prompt=company.ai_prompt,
        language=company.language,
        tone=company.tone,
        business_hours=company.business_hours,
        webhook_secret=encrypt_value(company.webhook_secret),
    )
    db.add(new_company)
    try:
        await db.commit()
        return {"message": "Company created successfully", "company_id": new_company.id}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error creating company")
