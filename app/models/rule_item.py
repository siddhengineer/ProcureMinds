from sqlalchemy import Column, Integer, String, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class RuleItem(Base):
    __tablename__ = "rule_items"

    rule_item_id = Column(Integer, primary_key=True, index=True)
    rule_set_id = Column(Integer, ForeignKey("rule_sets.rule_set_id", ondelete="CASCADE"))
    key = Column(String(100), nullable=False)  # e.g., cement_per_m3
    value = Column(Numeric, nullable=False)  # numerical constant
    unit = Column(String(50))  # e.g., bags_per_m3
    description = Column(Text)

    rule_set = relationship("RuleSet", back_populates="rule_items")
