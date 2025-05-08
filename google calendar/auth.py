import os, json
from fastapi import HTTPException
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

CLIENT_SECRETS_FILE = "google_calendar/credentials.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

def get_flow():
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

def save_credentials(company_id: str, credentials: Credentials):
    os.makedirs("google_calendar/tokens", exist_ok=True)
    with open(f"google_calendar/tokens/{company_id}.json", "w") as f:
        f.write(credentials.to_json())

def load_credentials(company_id: str) -> Credentials:
    path = f"google_calendar/tokens/{company_id}.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Google credentials not found.")
    with open(path) as f:
        return Credentials.from_authorized_user_info(json.load(f), SCOPES)
