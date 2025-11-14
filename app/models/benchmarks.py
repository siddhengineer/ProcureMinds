from sqlalchemy import Column, Integer, String, Numeric, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BenchmarkCement(Base):
    __tablename__ = "benchmark_cement"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    quality_standard = Column(String(100))
    default_quantity_per_m3 = Column(Numeric)
    unit = Column(String(50), default="bags")
    notes = Column(Text)


class BenchmarkSand(Base):
    __tablename__ = "benchmark_sand"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    quality_standard = Column(String(100))
    default_quantity_per_m3 = Column(Numeric)
    unit = Column(String(50), default="m3")
    notes = Column(Text)


class BenchmarkGravel(Base):
    __tablename__ = "benchmark_gravel"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    quality_standard = Column(String(100))
    default_quantity_per_m3 = Column(Numeric)
    unit = Column(String(50), default="m3")
    size_mm = Column(Integer)
    notes = Column(Text)


class BenchmarkTile(Base):
    __tablename__ = "benchmark_tile"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    quality_standard = Column(String(100))
    length_mm = Column(Integer)
    width_mm = Column(Integer)
    default_wastage_multiplier = Column(Numeric)
    unit = Column(String(50), default="m2")
    notes = Column(Text)
