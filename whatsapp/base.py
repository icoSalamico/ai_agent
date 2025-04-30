from abc import ABC, abstractmethod

class WhatsAppProvider(ABC):
    @abstractmethod
    async def send_message(self, phone_number: str, message: str) -> dict:
        pass
