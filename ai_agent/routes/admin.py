from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import Conversation, Company
from database.crud import get_db
from dependencies.security import verify_admin_key

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
