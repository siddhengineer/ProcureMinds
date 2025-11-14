from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base


class BOQCategory(Base):
    __tablename__ = "boq_categories"

    boq_category_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
