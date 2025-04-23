from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.core import Base
from utils.crypto import decrypt_value

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone_number_id = Column(String, unique=True)
    whatsapp_token = Column(String)
    verify_token = Column(String)
    ai_prompt = Column(String)
    language = Column(String, default="Portuguese")
    tone = Column(String, default="Formal")
    business_hours = Column(String)
    webhook_secret = Column(String, nullable=True)

    @property
    def decrypted_whatsapp_token(self):
        return decrypt_value(self.whatsapp_token)

    @property
    def decrypted_verify_token(self):
        return decrypt_value(self.verify_token)

    @property
    def decrypted_webhook_secret(self):
        return decrypt_value(self.webhook_secret)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True)
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", backref="conversations")
