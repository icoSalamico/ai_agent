import os
import hmac
from fastapi import Request, Header, HTTPException, Depends
from dotenv import load_dotenv

load_dotenv()

# Verify admin access using a static key (used for protected endpoints like /ping-db)
def verify_admin_key(x_api_key: str = Header(...)):
    expected_key = os.getenv("ADMIN_API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="Server misconfiguration: ADMIN_API_KEY not set.")
    
    if x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key.")

# Verify signature for incoming WhatsApp webhook requests
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
