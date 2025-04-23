from database import Company

def get_debug_company():
    return Company(
        id=999,
        name="Debug Company",
        phone_number_id="test-id",
        ai_prompt="You are a test assistant.",
        language="Portuguese",
        tone="Informal",
        whatsapp_token="test",
        verify_token="test",
        webhook_secret="test"
    )