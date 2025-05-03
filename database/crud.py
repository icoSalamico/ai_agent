from sqlalchemy import select
from database.core import SessionLocal
from database.models import Company, ClientSession
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from utils.crypto import encrypt_value


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_company_by_phone(phone_id: str) -> Company | None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.phone_number_id == phone_id)
        )
        return result.scalar_one_or_none()


async def get_company_by_verify_token(verify_token: str) -> Company | None:
    encrypted_token = encrypt_value(verify_token)
    async with SessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.verify_token == encrypted_token)
        )
        return result.scalar_one_or_none()


async def get_client_session(company_id: int, phone_number: str) -> ClientSession | None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(ClientSession).where(
                ClientSession.company_id == company_id,
                ClientSession.phone_number == phone_number
            )
        )
        return result.scalar_one_or_none()
