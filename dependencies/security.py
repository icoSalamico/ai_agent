from fastapi import Header, HTTPException
import os

async def verify_admin_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Unauthorized")
