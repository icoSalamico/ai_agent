from cryptography.fernet import Fernet
import os

SECRET_KEY = os.getenv("SECRET_KEY")
fernet = Fernet(SECRET_KEY.encode())

def encrypt_value(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()

def decrypt_value(value: str) -> str:
    return fernet.decrypt(value.encode()).decode()
