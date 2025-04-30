import httpx
from whatsapp.base import WhatsAppProvider

class MetaCloudProvider(WhatsAppProvider):
    def __init__(self, token: str, phone_number_id: str):
        self.token = token
        self.phone_number_id = phone_number_id

    async def send_message(self, phone_number: str, message: str) -> dict:
        url = f"https://graph.facebook.com/v19.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            return response.json()
