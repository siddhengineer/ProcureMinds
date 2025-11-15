from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    refresh_token = Column(Text, nullable=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    emails = relationship("Email", back_populates="user", cascade="all, delete-orphan")
    vendors = relationship("Vendor", back_populates="user", cascade="all, delete-orphan")
    rfqs = relationship("RFQ", back_populates="user", cascade="all, delete-orphan")
