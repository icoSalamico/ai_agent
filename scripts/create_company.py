import argparse
import asyncio
from database.models import Company
from database.core import SessionLocal, init_db
from utils.crypto import encrypt_value
from dotenv import load_dotenv

load_dotenv()


def get_args():
    parser = argparse.ArgumentParser(description="Create a new company")
    parser.add_argument("--name", required=True, help="Company name")
    parser.add_argument("--display-number", help="Display phone number")
    parser.add_argument("--phone", required=True, help="Phone number ID from WhatsApp Business")
    parser.add_argument("--token", required=True, help="WhatsApp token")
    parser.add_argument("--verify-token", required=True, help="Webhook Verify Token")
    parser.add_argument("--prompt", required=True, help="AI Prompt")
    parser.add_argument("--language", default="Portuguese", help="Language (default: Portuguese)")
    parser.add_argument("--tone", default="Formal", help="Tone (default: Formal)")
    parser.add_argument("--hours", required=True, help="Business hours (e.g., 09:00-18:00)")
    parser.add_argument("--secret", required=True, help="Webhook Secret")
    parser.add_argument("--provider", default="meta", choices=["meta", "zapi"], help="WhatsApp provider (default: meta)")
    parser.add_argument("--zapi-token", help="Z-API token (optional)")
    parser.add_argument("--zapi-instance-id", help="Z-API instance ID (optional)")
    return parser.parse_args()


async def create_company(args):
    await init_db()
    async with SessionLocal() as session:
        company = Company(
            name=args.name,
            display_number=args.display_number,
            phone_number_id=args.phone,
            whatsapp_token=encrypt_value(args.token),
            verify_token=encrypt_value(args.verify_token),
            ai_prompt=args.prompt,
            language=args.language,
            tone=args.tone,
            business_hours=args.hours,
            webhook_secret=encrypt_value(args.secret),
            provider=args.provider,
            zapi_token=encrypt_value(args.zapi_token) if args.zapi_token else None,
            zapi_instance_id=encrypt_value(args.zapi_instance_id) if args.zapi_instance_id else None
        )
        session.add(company)
        await session.commit()
        print(f"✅ Company '{args.name}' created successfully!")


if __name__ == "__main__":
    args = get_args()
    asyncio.run(create_company(args))
