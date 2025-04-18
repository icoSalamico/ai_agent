import httpx
from ai_agent import generate_response
from database import get_company_by_phone
from database import SessionLocal
from database import Conversation
from utils.persistence import save_conversation
from database import async_session 


async def handle_message(data):
    # Extract relevant parts
    entry = data.get("entry", [])[0]
    changes = entry.get("changes", [])[0]
    value = changes.get("value", {})
    messages = value.get("messages", [])

    if not messages:
        return

    message = messages[0]
    phone_number_id = value.get("metadata", {}).get("phone_number_id")
    from_number = message.get("from")
    text = message.get("text", {}).get("body")

    ai_response = await generate_response(phone_number_id, text)  # hypothetical function

    # Save to DB with retry
    async with async_session() as session:
        await save_conversation(session, phone_number_id, text, ai_response)

    await send_reply(from_number, ai_response)


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