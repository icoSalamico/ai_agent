import httpx
from whatsapp.base import WhatsAppProvider
import os
from fastapi import HTTPException

from utils.crypto import decrypt_value

class ZApiProvider(WhatsAppProvider):
    def __init__(self, instance_id: str, api_token: str):
        if not instance_id:
            raise ValueError("ZApiProvider: instance_id is None")
        if not api_token:
            raise ValueError("ZApiProvider: api_token is None")

        self.instance_id = instance_id
        self.api_token = decrypt_value(api_token)  # ✅ ALREADY DECRYPTED before being passed in

        self.base_url = f"https://api.z-api.io/instances/{self.instance_id}/token/{self.api_token}"

    async def send_message(self, phone_number: str, message: str) -> dict:
        url = f"{self.base_url}/send-messages"
        payload = {
            "phone": phone_number,
            "message": message
        }
        headers = {
            "Content-Type": "application/json",
            "Client-Token": decrypt_value(self.api_token)  # ✅ No extra str() or decode needed
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                print(f"❌ Failed to send message to {phone_number}")
                print("URL:", url)
                print("Payload:", payload)
                print("Response:", response.status_code, response.text)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to send message via Z-API: {response.text}"
                )
            return response.json()


# Criação de instância on-demand
ZAPI_API_BASE = "https://api.z-api.io"

async def create_zapi_instance(company_name: str, session_name: str, callback_base_url: str) -> dict:
    master_token = os.getenv("ZAPI_MASTER_TOKEN")

    if not master_token:
        raise RuntimeError("❌ ZAPI_MASTER_TOKEN not found in environment variables")

    url = f"{ZAPI_API_BASE}/instances/integrator/on-demand"
    headers = {
        "Content-Type": "application/json",
        "Client-Token": master_token
    }
    payload = {
        "name": company_name,
        "sessionName": session_name,
        "deliveryCallbackUrl": f"{callback_base_url}/webhook/delivery",
        "receivedCallbackUrl": f"{callback_base_url}/webhook",
        "disconnectedCallbackUrl": f"{callback_base_url}/webhook/disconnected",
        "connectedCallbackUrl": f"{callback_base_url}/webhook/connected",
        "messageStatusCallbackUrl": f"{callback_base_url}/webhook/status",
        "isDevice": False,
        "businessDevice": True
    }

    async with httpx.AsyncClient() as client:
        try:
            print("📡 Sending Z-API instance creation request...")
            print("🔐 Token being used:", master_token[:6] + "..." if master_token else "None")
            res = await client.post(url, json=payload, headers=headers)
            res.raise_for_status()
            data = res.json()
            print("✅ Z-API instance created:", data)
            return {
                "instance_id": data["id"],
                "token": data["token"]
            }
        except httpx.HTTPStatusError as e:
            print("❌ Z-API responded with an error:")
            print("Response status:", e.response.status_code)
            print("Response body:", e.response.text)
            raise HTTPException(status_code=500, detail=f"Failed to create Z-API instance: {e.response.text}")
