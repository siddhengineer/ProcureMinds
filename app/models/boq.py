from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func, Text
from sqlalchemy.orm import relationship
 
from app.core.database import Base
from app.models.boq_csv import BOQCSV  # Add this import at the top
 
 
class BOQ(Base):
    __tablename__ = "boq"
 
    boq_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True)
    rule_set_id = Column(Integer, ForeignKey("rule_sets.rule_set_id"))
    status = Column(String(50), default="draft")     # draft / approved / sent
    pdf_link = Column(String(255), nullable=True)
    compute_json = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
 
    rule_set = relationship("RuleSet")
    user = relationship("User")
    items = relationship("BOQItem", back_populates="boq", cascade="all, delete-orphan")
    csv_files = relationship("BOQCSV", back_populates="boq", cascade="all, delete-orphan")