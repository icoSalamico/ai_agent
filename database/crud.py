from sqlalchemy.future import select
from database.core import SessionLocal
from database.models import Company
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_company_by_phone(phone_id: str):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.phone_number_id == phone_id)
        )
        return result.scalar_one_or_none()
