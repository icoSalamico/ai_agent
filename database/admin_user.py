from sqlalchemy import Column, Integer, String
from database.core import Base  # use your declarative base
from passlib.hash import bcrypt

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    def verify_password(self, password: str) -> bool:
        return bcrypt.verify(password, self.hashed_password)
