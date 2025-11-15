from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class RFQ(Base):
    __tablename__ = "rfqs"

    rfq_id = Column(Integer, primary_key=True, index=True)
    incoming_mail = Column(Text, nullable=True)  # Store the incoming email content
    outgoing_mail = Column(Text, nullable=True)  # Store the outgoing RFQ email content
    reply_received = Column(Boolean, default=False, nullable=False)  # Flag for reply status
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.vendor_id", ondelete="SET NULL"), nullable=True)
    boq_id = Column(Integer, ForeignKey("boq.boq_id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="pending", nullable=False)  # e.g., pending, sent, replied, closed
    subject = Column(String(500), nullable=True)  # Email subject
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="rfqs")
    vendor = relationship("Vendor", back_populates="rfqs")
    project = relationship("Project", back_populates="rfqs")
    boq = relationship("BOQ", back_populates="rfqs")