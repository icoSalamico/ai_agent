from tenacity import retry, stop_after_attempt, wait_exponential # type: ignore
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from database import Conversation
from datetime import datetime, timezone

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry_error_callback=lambda retry_state: print("❌ Failed to persist conversation after retries.")
)
async def save_conversation(
    session: AsyncSession,
    phone_number: str,
    user_message: str,
    ai_response: str,
    company_id: int
):
    conversation = Conversation(
        phone_number=phone_number,
        user_message=user_message,
        ai_response=ai_response,
        timestamp=datetime.now(timezone.utc),
        company_id=company_id,
    )
    session.add(conversation)
    await session.commit()