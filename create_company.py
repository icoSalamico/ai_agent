import asyncio
from database import SessionLocal, Company
from dotenv import load_dotenv

load_dotenv()


async def create_company():
    name = input("Company name: ")
    phone_number_id = input("Phone number ID (from WhatsApp Business): ")
    whatsapp_token = input("WhatsApp token: ")
    verify_token = input("Webhook Verify Token: ")
    ai_prompt = input("AI Prompt: ")
    language = input("Language (default: Portuguese): ") or "Portuguese"
    tone = input("Tone (default: Formal): ") or "Formal"
    business_hours = input("Business hours (e.g., 09:00-18:00): ")

    async with SessionLocal() as session:
        company = Company(
            name=name,
            phone_number_id=phone_number_id,
            whatsapp_token=whatsapp_token,
            verify_token=verify_token,
            ai_prompt=ai_prompt,
            language=language,
            tone=tone,
            business_hours=business_hours
        )
        session.add(company)
        await session.commit()
        print(f"Company {name} created successfully!")

if __name__ == "__main__":
    asyncio.run(create_company())