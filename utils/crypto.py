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
    if not isinstance(value, str) or not value.strip():
        raise ValueError("❌ Cannot encrypt an empty, None, or non-string value.")
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(value: str | None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("❌ Cannot decrypt an empty, None, or non-string value.")
    try:
        return fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        raise ValueError("❌ Invalid token: decryption failed due to tampering or wrong key.")
    except Exception as e:
        raise ValueError(f"❌ Unexpected error during decryption: {e}")
