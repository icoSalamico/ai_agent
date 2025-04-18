from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True, poolclass=NullPool)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone_number_id = Column(String, unique=True)
    whatsapp_token = Column(String)
    verify_token = Column(String)
    ai_prompt = Column(String)
    language = Column(String, default="Portuguese")
    tone = Column(String, default="Formal")
    business_hours = Column(String) # e.g. "09:00-18:00"
    webhook_secret = Column(String, nullable=True)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True)
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", backref="conversations")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_company_by_phone(phone_id: str):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.phone_number_id == phone_id)
        )
        return result.scalar_one_or_none()