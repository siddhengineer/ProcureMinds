from sqlalchemy import Column, Integer, String, Numeric, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.core.database import Base


class RuleItem(Base):
    __tablename__ = "rule_items"

    rule_item_id = Column(Integer, primary_key=True, index=True)
    rule_set_id = Column(Integer, ForeignKey("rule_sets.rule_set_id", ondelete="CASCADE"))
    category_id = Column(
        Integer,
        ForeignKey("boq_categories.boq_category_id", ondelete="SET NULL"),
        nullable=True,
    )
    key = Column(String(100), nullable=False)  # e.g., cement_bags_per_m3
    value = Column(Numeric, nullable=True)  # numerical rate if constant
    unit = Column(String(50))  # e.g., bags_per_m3
    rate_basis = Column(
        Enum("per_m3", "per_m2", "per_m", "per_unit", "absolute", name="ruleitem_basis_enum"),
        nullable=True,
    )
    description = Column(Text)
    formula = Column(Text, nullable=True)  # optional expression for derived values
    resolved_rate = Column(Numeric, nullable=True)  # post-evaluated numeric rate

    rule_set = relationship("RuleSet", back_populates="rule_items")
    category = relationship("BOQCategory")
