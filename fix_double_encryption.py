import asyncio
from database.core import async_session
from database.models import Company
from utils.crypto import decrypt_value, encrypt_value
from sqlalchemy import select

async def fix_zapi_instance_ids():
    async with async_session() as session:
        result = await session.execute(
            select(Company).where(Company.zapi_instance_id.isnot(None))
        )
        companies = result.scalars().all()

        for company in companies:
            try:
                first_decrypt = decrypt_value(company.zapi_instance_id)
                if first_decrypt.startswith("gAAAAA"):  # ainda criptografado
                    print(f"🔧 Corrigindo empresa: {company.name}")
                    second_decrypt = decrypt_value(first_decrypt)
                    corrected = encrypt_value(second_decrypt)
                    company.zapi_instance_id = corrected
                    print(f"✅ Corrigido para: {second_decrypt}")
                else:
                    print(f"✅ {company.name} já está correto.")
            except Exception as e:
                print(f"❌ Erro com empresa {company.name}: {e}")

        await session.commit()

if __name__ == "__main__":
    asyncio.run(fix_zapi_instance_ids())
