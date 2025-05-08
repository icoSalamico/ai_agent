from datetime import datetime, timedelta
import pytz
from .calendar import suggest_available_slots, create_event

class MeetingScheduler:
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.current_window_start = datetime.now(pytz.UTC)
        self.slot_duration = timedelta(minutes=30)
        self.window_step = timedelta(days=1)
        self.max_attempts = 5
        self.attempts = 0

    async def suggest_slots(self) -> list:
        window_end = self.current_window_start + timedelta(hours=8)
        return suggest_available_slots(
            company_id=self.company_id,
            start_time=self.current_window_start,
            end_time=window_end,
            slot_duration_minutes=int(self.slot_duration.total_seconds() / 60),
            working_hours=(9, 18)
        )

    async def handle_user_response(self, user_message: str, suggested_slots: list) -> tuple:
        user_message = user_message.lower()

        for slot in suggested_slots:
            start_str = slot["start"][:16]
            end_str = slot["end"][:16]
            if start_str in user_message or end_str in user_message:
                return "confirm", slot

        negative_keywords = ["nenhum", "não posso", "não consigo", "nenhuma hora", "sem disponibilidade"]
        if any(k in user_message for k in negative_keywords):
            self.attempts += 1
            if self.attempts >= self.max_attempts:
                return "abort", None

            self.current_window_start += self.window_step
            new_slots = await self.suggest_slots()
            return "retry", new_slots

        return "clarify", None

    async def schedule_event(self, slot: dict, summary: str = "Reunião com Assistente IA", description: str = "Agendamento automático pelo assistente") -> dict:
        return create_event(
            self.company_id,
            {
                "summary": summary,
                "description": description,
                "start": {"dateTime": slot["start"], "timeZone": "America/Sao_Paulo"},
                "end": {"dateTime": slot["end"], "timeZone": "America/Sao_Paulo"},
            }
        )
