from cryptography.fernet import Fernet, InvalidToken
import os

FERNET_KEY = os.getenv("FERNET_SECRET_KEY")
fernet = Fernet(FERNET_KEY.encode())

def encrypt_value(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(value: str | None) -> str | None:
    if not value:
        return None

    try:
        return fernet.decrypt(value.encode()).decode()
    except (InvalidToken, AttributeError, TypeError):
        return None
