import httpx
from whatsapp.base import WhatsAppProvider

class ZApiProvider(WhatsAppProvider):
    def __init__(self, instance_id: str, api_token: str):
        self.base_url = f"https://api.z-api.io/instances/{instance_id}/token/{api_token}"

    async def send_message(self, phone_number: str, message: str) -> dict:
        url = f"{self.base_url}/send-messages"
        payload = {
            "phone": phone_number,
            "message": message
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            return response.json()
