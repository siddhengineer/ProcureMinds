from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Float, ForeignKey, func
from sqlalchemy.orm import relationship
 
from app.core.database import Base
 
 
class Email(Base):
    __tablename__ = "emails"
 
    mail_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    attachments_url = Column(Text)  # Store URLs as comma-separated or JSON string
    summary_json = Column(Text)  # Store LLM summary JSON response
    overall_score = Column(Float)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
 
    user = relationship("User", back_populates="emails")
    project = relationship("Project", back_populates="emails")