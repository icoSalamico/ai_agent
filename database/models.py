from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.core import Base
from utils.crypto import decrypt_value

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    display_number = Column(String, nullable=True)
    phone_number_id = Column(String, nullable=False)
    verify_token = Column(String, default="gAAAAABoD7Tfnjh_shD9FgJp2E5ks3dEhYPGTJpLSx4IT6l0rbNuslXsN2n9ktQGanG1JGasEgFVkomfZpGLy9qkneH8YpUOS8YSTiWL67ax5bG0DnlzJ20=")
    business_hours = Column(String)
    
    # AI configuration
    ai_prompt = Column(Text, nullable=True)
    tone = Column(String, default="Formal")
    language = Column(String, default="Portuguese")

    # WhatsApp provider info
    provider = Column(String, default="meta")  # meta or zapi
    whatsapp_token = Column(Text, nullable=True)  # used for Meta
    webhook_secret = Column(Text, nullable=True)  # used for Meta

    # Z-API fields
    zapi_instance_id = Column(String, nullable=True)
    zapi_token = Column(String, nullable=True)

    # Optional flags or tracking
    active = Column(Boolean, default=True)

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
