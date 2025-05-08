# google_calendar/session_state.py
from datetime import datetime, timedelta
import pytz

class MeetingSessionState:
    def __init__(self, company_id: str, phone_number: str):
        self.company_id = company_id
        self.phone_number = phone_number
        self.current_window_start = datetime.now(pytz.UTC)
        self.window_duration = timedelta(hours=8)
        self.slot_duration = timedelta(minutes=30)
        self.retry_interval = timedelta(days=1)
        self.max_retries = 5
        self.retry_count = 0
        self.last_suggested_slots = []
        self.confirmed_slot = None
        self.state = "suggesting"  # or "awaiting_confirmation" / "scheduled" / "aborted"

    def advance_window(self):
        self.current_window_start += self.retry_interval
        self.retry_count += 1

    def is_exceeded_retries(self) -> bool:
        return self.retry_count >= self.max_retries

    def get_current_window_end(self):
        return self.current_window_start + self.window_duration
