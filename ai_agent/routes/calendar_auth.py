from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from google_calendar.auth import get_flow
from google.oauth2.credentials import Credentials
from database.models import Company
from database.crud import get_db
from utils.crypto import encrypt_value

router = APIRouter()

@router.get("/google-auth/{company_id}")
def auth_start(company_id: str):
    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", state=company_id)
    return RedirectResponse(auth_url)


@router.get("/google-auth/callback")
async def auth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    flow = get_flow()
    flow.fetch_token(authorization_response=str(request.url))
    credentials: Credentials = flow.credentials
    company_id = request.query_params.get("state")

    result = await db.execute(select(Company).where(Company.id == int(company_id)))
    company = result.scalar_one_or_none()

    if not company:
        return {"error": "Company not found."}

    company.google_refresh_token = encrypt_value(credentials.refresh_token)
    company.google_access_token = encrypt_value(credentials.token)
    company.google_token_expiry = credentials.expiry
    company.google_calendar_id = credentials.id_token.get("email", "primary")

    await db.commit()

    return RedirectResponse(f"/dashboard?token={company.decrypted_verify_token}&success=true")
