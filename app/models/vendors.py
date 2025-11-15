from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, func, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    vendor_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    phone_number = Column(String(20), nullable=True)
    material = Column(ARRAY(Integer), nullable=True)
    location = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="vendors")
 
