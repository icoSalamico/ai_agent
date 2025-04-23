from fastapi import HTTPException
import hmac
import hashlib

def verify_signature(app_secret: str, request_body: bytes, signature: str):
    if not signature or "=" not in signature:
        raise HTTPException(status_code=403, detail="Missing or invalid signature format")

    signature_hash = signature.split("=")[1]
    expected_hash = hmac.new(app_secret.encode("utf-8"), msg=request_body, digestmod=hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, signature_hash):
        raise HTTPException(status_code=403, detail="Invalid signature")