from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

# Get your key from env
SECRET_KEY = os.getenv("FERNET_SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("FERNET_SECRET_KEY is not set in .env")

fernet = Fernet(SECRET_KEY)

def encrypt_value(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()

def decrypt_value(value: str) -> str:
    return fernet.decrypt(value.encode()).decode()
