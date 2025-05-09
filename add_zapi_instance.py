import asyncio
import os
from dotenv import load_dotenv  # ✅ Adicione isso

load_dotenv()  # ✅ Carrega o .env da raiz do projeto

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.core import async_session
from database.models import ZApiInstance
from utils.crypto import encrypt_value



def is_encrypted(value: str) -> bool:
    return isinstance(value, str) and value.startswith("gAAAAA")


async def add_zapi_instance(instance_id: str, token: str):
    encrypted_instance_id = instance_id if is_encrypted(instance_id) else encrypt_value(instance_id)

    async with async_session() as session:
        async with session.begin():
            # Verifica se já existe uma instância com esse ID
            result = await session.execute(select(ZApiInstance).where(ZApiInstance.instance_id == encrypted_instance_id))
            existing = result.scalars().first()
            if existing:
                print("❌ Já existe uma instância com esse ID.")
                return

            zapi_instance = ZApiInstance(
                instance_id=encrypted_instance_id,
                token=token if is_encrypted(token) else encrypt_value(token),
                assigned=False
            )
            session.add(zapi_instance)
            await session.commit()
            print("✅ Z-API instance added successfully.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Uso: python add_zapi_instance.py <INSTANCE_ID> <TOKEN>")
    else:
        instance_id = sys.argv[1]
        token = sys.argv[2]
        asyncio.run(add_zapi_instance(instance_id, token))
