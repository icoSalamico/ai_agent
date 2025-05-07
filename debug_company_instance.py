import asyncio
from sqlalchemy import select
from database.core import async_session
from database.models import Company
from utils.crypto import decrypt_value

async def check_encrypted_company():
    async with async_session() as session:
        result = await session.execute(
            select(Company).where(Company.zapi_instance_id.isnot(None))
        )
        companies = result.scalars().all()
        for company in companies:
            print("Empresa:", company.name)
            print("ID criptografado:", company.zapi_instance_id)
            try:
                print("ID descriptografado:", decrypt_value(company.zapi_instance_id))
            except Exception as e:
                print("❌ Erro ao descriptografar:", str(e))
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(check_encrypted_company())
