from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.discovery_cache.base import Cache
from google_calendar.auth import load_credentials
from datetime import datetime, timedelta
import pytz

# Desabilita warnings de cache
class NoCache(Cache):
    def get(self, url): return None
    def set(self, url, content): pass

def get_service(company_id: str):
    creds = load_credentials(company_id)
    return build("calendar", "v3", credentials=creds, cache=NoCache())

def get_availability(company_id: str, start: datetime, end: datetime):
    service = get_service(company_id)
    body = {
        "timeMin": start.isoformat(),
        "timeMax": end.isoformat(),
        "timeZone": "America/Sao_Paulo",
        "items": [{"id": "primary"}],
    }
    try:
        response = service.freebusy().query(body=body).execute()
        return response["calendars"]["primary"].get("busy", [])
    except HttpError as e:
        print("❌ Erro ao consultar disponibilidade:", e)
        return []

def suggest_available_slots(company_id: str, start: datetime, end: datetime, slot_minutes: int = 30):
    busy_ranges = get_availability(company_id, start, end)
    tz = pytz.timezone("America/Sao_Paulo")

    busy = [(
        datetime.fromisoformat(b["start"]).astimezone(tz),
        datetime.fromisoformat(b["end"]).astimezone(tz)
    ) for b in busy_ranges]

    suggestions = []
    current = start
    while current + timedelta(minutes=slot_minutes) <= end:
        slot_end = current + timedelta(minutes=slot_minutes)

        if not (9 <= current.hour < 18):
            current += timedelta(minutes=15)
            continue

        conflict = any(start <= slot_end and end >= current for start, end in busy)
        if not conflict:
            suggestions.append({
                "start": current.isoformat(),
                "end": slot_end.isoformat()
            })

        current += timedelta(minutes=15)

    return suggestions

def create_event(company_id: str, event_data: dict):
    service = get_service(company_id)
    return service.events().insert(calendarId="primary", body=event_data).execute()
