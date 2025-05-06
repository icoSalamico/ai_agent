from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.core import Base
from utils.crypto import decrypt_value, encrypt_value


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    display_number = Column(String, nullable=True)
    phone_number_id = Column(String, nullable=True)
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

    @property
    def decrypted_zapi_token(self):
        return decrypt_value(self.zapi_token)

    @property
    def decrypted_zapi_instance_id(self):
        return decrypt_value(self.zapi_instance_id)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True)
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", backref="conversations")


class ClientSession(Base):
    __tablename__ = "client_sessions"

    id = Column(Integer, primary_key=True)
    phone_number = Column(String, nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", backref="client_sessions")
    ai_enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ZApiInstance(Base):
    __tablename__ = "zapi_instances"

    id = Column(Integer, primary_key=True)
    instance_id = Column(String, nullable=False)
    token = Column(String, nullable=False)
    assigned = Column(Boolean, default=False)

    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    company = relationship("Company", backref="zapi_instance")

    @property
    def decrypted_instance_id(self):
        return decrypt_value(self.instance_id)

    @property
    def decrypted_token(self):
        return decrypt_value(self.token)
