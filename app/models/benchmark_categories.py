from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BenchmarkCategory(Base):
    __tablename__ = "benchmark_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)  # e.g. sand, cement, gravel
    description = Column(Text)

