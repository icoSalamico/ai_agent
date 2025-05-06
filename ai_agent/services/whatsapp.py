# services/whatsapp.py

import os
import traceback
from sqlalchemy.future import select
from ai_agent.services.ai import generate_response
from database.core import SessionLocal
from database.models import Conversation, Company
from utils.persistence import save_conversation
from whatsapp.provider_factory import get_provider

DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"


async def get_recent_messages(session, phone_number: str, company_id: int, limit: int = 5):
    result = await session.execute(
        select(Conversation)
        .where(Conversation.phone_number == phone_number)
        .where(Conversation.company_id == company_id)
        .order_by(Conversation.timestamp.desc())
        .limit(limit)
    )
    conversations = result.scalars().all()
    messages = []
    for conv in reversed(conversations):  # reverse to preserve order
        messages.append({"role": "user", "content": conv.user_message})
        messages.append({"role": "assistant", "content": conv.ai_response})
    return messages


async def handle_message(data):
    try:
        changes = data["entry"][0]["changes"][0]["value"]
        phone_id = changes["metadata"]["phone_number_id"]
        msg = changes["messages"][0]
        user_text = msg["text"]["body"]
        sender = msg["from"]

        async with SessionLocal() as session:
            # Get company
            result = await session.execute(select(Company).where(Company.phone_number_id == phone_id))
            company = result.scalar_one_or_none()

            if not company:
                print("⚠️ Company not found for phone_number_id:", phone_id)
                return

            # Get conversation history
            history = await get_recent_messages(session, sender, company.id)

            # Generate AI response
            reply = await generate_response(
                user_input=user_text,
                prompt=company.ai_prompt,
                language=company.language,
                tone=company.tone,
                history=history
            )

            # Save to database
            await save_conversation(
                session,
                phone_number=sender,
                user_message=user_text,
                ai_response=reply,
                company_id=company.id
            )

        # Send response
        if DEBUG_MODE:
            print(f"⚠️ DEBUG_MODE: Simulação de envio para {sender}: {reply}")
        else:
            provider = get_provider(company.provider, {
                "token": company.decrypted_whatsapp_token,
                "phone_number_id": company.phone_number_id,
                "instance_id": company.decrypted_zapi_instance_id,
                "api_token": company.decrypted_zapi_token
            })
            await provider.send_message(phone_number=sender, message=reply)

    except Exception as e:
        print(f"❌ Error handling message: {e}")
        traceback.print_exc()
