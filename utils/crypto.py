from cryptography.fernet import Fernet, InvalidToken
import os

FERNET_KEY = os.getenv("FERNET_SECRET_KEY")

if not FERNET_KEY:
    raise RuntimeError("❌ FERNET_SECRET_KEY is not set in environment variables")

try:
    fernet = Fernet(FERNET_KEY.encode())
except Exception as e:
    raise RuntimeError(f"❌ Invalid FERNET_SECRET_KEY: {e}")


def encrypt_value(value: str) -> str:
    if not value:
        raise ValueError("❌ Cannot encrypt an empty or None value")
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return fernet.decrypt(value.encode()).decode()
    except (InvalidToken, AttributeError, TypeError):
        return None
