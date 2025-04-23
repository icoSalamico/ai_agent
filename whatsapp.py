import httpx
from ai_agent import generate_response
from database import get_company_by_phone
from database import SessionLocal
from database import Conversation, Company
from utils.persistence import save_conversation
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
import os

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
        company = await get_company_by_phone(phone_id)
        if not company:
            print(f"Company not found for phone_number_id: {phone_id}")
            return
        
        msg = changes["messages"][0]
        user_text = msg["text"]["body"]
        sender = msg["from"]

        async with SessionLocal() as session:
            # Get company again (ensures latest DB context)
            result = await session.execute(select(Company).where(Company.phone_number_id == phone_id))
            company = result.scalar_one_or_none()
            if not company:
                print("⚠️ Company not found for phone_number_id:", phone_id)
                return

            # Get recent messages for conversational context
            history = await get_recent_messages(session, sender, company.id)

            # Generate AI reply using conversation history
            reply = await generate_response(
                user_input=user_text,
                prompt=company.ai_prompt,
                language=company.language,
                tone=company.tone,
                history=history
            )

            # Save the new conversation
            await save_conversation(
                session,
                phone_number=sender,
                user_message=user_text,
                ai_response=reply,
                company_id=company.id
            )

        # Send the reply back to the user
        await send_reply(sender, reply, company)

    except Exception as e:
        print(f"❌ Error handling message: {e}")


async def send_reply(to: str, message: str, company):
    if DEBUG_MODE:
        print(f"⚠️ DEBUG_MODE: Simulação de envio para {to}: {message}")
        return
    
    url = f"https://graph.facebook.com/v17.0/{company.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {company.decrypted_whatsapp_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": message
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"❌ Failed to send message: {response.status_code} - {response.text}")
