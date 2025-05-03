import httpx
from whatsapp.base import WhatsAppProvider
import os
from fastapi import HTTPException


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
