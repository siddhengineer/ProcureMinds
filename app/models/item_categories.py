from sqlalchemy import Column, Integer, String, Text
from app.core.database import Base


class BenchmarkCategory(Base):
    __tablename__ = "item_categories"

    item_category_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)  # e.g. sand, cement, gravel
    description = Column(Text)

