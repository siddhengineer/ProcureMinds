from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Text,
    ForeignKey,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class BOQCategory(Base):
    __tablename__ = "boq_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)  
    description = Column(Text)

    # Example rows:
    # earthwork
    # concrete_work
    # tile_work_flooring

class RuleSet(Base):
    __tablename__ = "rule_sets"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=True)
    name = Column(String(100), default="default")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    rule_items = relationship("RuleItem", back_populates="rule_set", cascade="all, delete-orphan")



class RuleItem(Base):
    __tablename__ = "rule_items"

    id = Column(Integer, primary_key=True, index=True)
    rule_set_id = Column(Integer, ForeignKey("rule_sets.id", ondelete="CASCADE"))
    key = Column(String(100), nullable=False)      # e.g. cement_per_m3
    value = Column(Numeric, nullable=False)        # numerical constant
    unit = Column(String(50))                      # e.g. bags_per_m3
    description = Column(Text)

    rule_set = relationship("RuleSet", back_populates="rule_items")



class BOQ(Base):
    __tablename__ = "boq"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=True)
    rule_set_id = Column(Integer, ForeignKey("rule_sets.id"))
    status = Column(String(50), default="draft")     # draft / approved / sent
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    rule_set = relationship("RuleSet")
    items = relationship("BOQItem", back_populates="boq", cascade="all, delete-orphan")



class BOQItem(Base):
    __tablename__ = "boq_items"

    id = Column(Integer, primary_key=True, index=True)
    boq_id = Column(Integer, ForeignKey("boq.id", ondelete="CASCADE"))
    category_id = Column(Integer, ForeignKey("boq_categories.id"))   # earthwork, concrete, tile
    material_name = Column(String(255), nullable=False)
    quantity = Column(Numeric, nullable=False)
    unit = Column(String(50), nullable=False)
    standard = Column(String(100))      # IS code
    notes = Column(Text)

    boq = relationship("BOQ", back_populates="items")
    category = relationship("BOQCategory")
