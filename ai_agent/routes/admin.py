from fastapi import APIRouter, Depends, HTTPException
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
        "provider": company.provider,
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
            "provider": company.provider,
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
    display_number: str
    provider: str = "meta"
    whatsapp_token: Optional[str]
    webhook_secret: Optional[str]
    verify_token: Optional[str]
    zapi_instance_id: Optional[str]
    zapi_token: Optional[str]
    ai_prompt: Optional[str]
    language: Optional[str] = "Portuguese"
    tone: Optional[str] = "Formal"
    business_hours: Optional[str]

@router.post("/companies")
async def create_company(company: CompanyCreate, db: AsyncSession = Depends(get_db)):
    new_company = Company(
        name=company.name,
        phone_number_id=company.phone_number_id,
        display_number=company.display_number,
        provider=company.provider,
        ai_prompt=company.ai_prompt,
        language=company.language,
        tone=company.tone,
        business_hours=company.business_hours,
    )

    if company.provider == "meta":
        if not company.whatsapp_token or not company.webhook_secret or not company.verify_token:
            raise HTTPException(status_code=400, detail="Missing Meta API credentials")
        new_company.whatsapp_token = encrypt_value(company.whatsapp_token)
        new_company.webhook_secret = encrypt_value(company.webhook_secret)
        new_company.verify_token = encrypt_value(company.verify_token)

    elif company.provider == "zapi":
        if not company.zapi_instance_id or not company.zapi_token:
            raise HTTPException(status_code=400, detail="Missing Z-API credentials")
        new_company.zapi_instance_id = company.zapi_instance_id
        new_company.zapi_token = company.zapi_token

    db.add(new_company)
    try:
        await db.commit()
        return {"message": "Company created successfully", "company_id": new_company.id}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error creating company")
