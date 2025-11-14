from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class MasterRuleItem(Base):
    __tablename__ = "master_rule_items"

    master_rule_item_id = Column(Integer, primary_key=True, index=True)
    master_rule_set_id = Column(
        Integer,
        ForeignKey("master_rule_sets.master_rule_set_id", ondelete="CASCADE"),
        nullable=False,
    )

    key = Column(String(200), nullable=False)
    unit = Column(String(100), nullable=False)
    description = Column(Text)
    default_value = Column(Numeric, nullable=True)
    formula = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    master_rule_set = relationship("MasterRuleSet", back_populates="items")

    __table_args__ = (
        UniqueConstraint("master_rule_set_id", "key", name="uq_master_rule_item_key_per_set"),
    )
