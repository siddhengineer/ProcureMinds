from sqlalchemy import Column, Integer, String, Numeric, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class RuleItem(Base):
    __tablename__ = "rule_items"

    rule_item_id = Column(Integer, primary_key=True)
    rule_set_id = Column(Integer, ForeignKey("rule_sets.rule_set_id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("boq_categories.boq_category_id", ondelete="SET NULL"))
    key = Column(String(200), nullable=False)
    value = Column(Numeric, nullable=True)
    unit = Column(String(100), nullable=False)
    rate_basis = Column(
        Enum(
            "per_m3",
            "per_m2",
            "per_m",
            "per_tile",
            "per_unit",
            "absolute",
            name="ruleitem_basis_enum",
        ),
        nullable=True,
    )
    description = Column(Text)
    formula = Column(Text)
    resolved_rate = Column(Numeric)

    rule_set = relationship("RuleSet", back_populates="rule_items")
    category = relationship("BOQCategory")
