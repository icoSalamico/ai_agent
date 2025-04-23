import hmac
from fastapi import Header, HTTPException
import os

async def verify_admin_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    

def verify_signature(app_secret: str, request_body: bytes, signature: str):
    if not signature or "=" not in signature:
        raise HTTPException(status_code=403, detail="Missing or invalid signature format")

    signature_hash = signature.split("=")[1]
    expected_hash = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=request_body,
        digestmod="sha256"
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, signature_hash):
        raise HTTPException(status_code=403, detail="Invalid signature")
