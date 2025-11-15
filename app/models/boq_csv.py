from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime

class BOQCSV(Base):
    __tablename__ = "boq_csvs"

    boq_csv_id = Column(Integer, primary_key=True)
    boq_id = Column(Integer, ForeignKey("boq.boq_id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(255), nullable=False)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)
    generated_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    boq = relationship("BOQ", back_populates="csv_files")
