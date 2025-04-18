import httpx
from ai_agent import generate_response
from database import get_company_by_phone
from database import SessionLocal
from database import Conversation, Company
from utils.persistence import save_conversation

from sqlalchemy.future import select


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

        reply = await generate_response(
            user_text, 
            company.ai_prompt,
            language=company.language,
            tone=company.tone
            )
        
        async with SessionLocal() as session:
            result = await session.execute(select(Company).where(Company.phone_number_id == phone_id))
            company = result.scalar_one_or_none()

            if not company:
                print("⚠️ Company not found for phone_number_id:", phone_id)
                return

            # Save the conversation
            await save_conversation(
                session,
                phone_number=msg.get("from"),
                user_message=user_text,
                ai_response=reply,
                company_id=company.id
            )
        
        await send_reply(sender, reply, company)

        async with SessionLocal() as session:
            conversation = Conversation(
                phone_number=sender,
                user_message=user_text,
                ai_response=reply,
                company_id=company.id
            )
            session.add(conversation)
            await session.commit()

    except Exception as e:
        print(f"Error handling message: {e}")


async def send_reply(to: str, message: str, company):
    url = f"https://graph.facebook.com/v17.0/{company.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {company.whatsapp_token}",
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
            print(f"Failed to send message: {response.status_code} - {response.text}")