from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class MasterRuleSet(Base):
    __tablename__ = "master_rule_sets"

    master_rule_set_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category_id = Column(
        Integer,
        ForeignKey("boq_categories.boq_category_id", ondelete="CASCADE"),
        nullable=False,
    )
    description = Column(Text)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Integer, nullable=False, default=1)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    category = relationship("BOQCategory")
    items = relationship(
        "MasterRuleItem",
        back_populates="master_rule_set",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("name", "category_id", "version", name="uq_master_rule_set_name_cat_ver"),
    )
