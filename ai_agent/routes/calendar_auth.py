from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_calendar.auth import get_flow, save_credentials

router = APIRouter()

@router.get("/google-auth/{company_id}")
def auth_start(company_id: str):
    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", state=company_id)
    return RedirectResponse(auth_url)

@router.get("/google-auth/callback")
def auth_callback(request: Request):
    flow = get_flow()
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials
    company_id = request.query_params.get("state")  # Recupera o state
    save_credentials(company_id, credentials)
    return {"message": f"Google Calendar connected for company {company_id}."}
