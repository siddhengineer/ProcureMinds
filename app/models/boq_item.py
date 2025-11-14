from sqlalchemy import Column, Integer, String, Numeric, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.core.database import Base


class BOQItem(Base):
    __tablename__ = "boq_items"

    boq_item_id = Column(Integer, primary_key=True, index=True)
    boq_id = Column(Integer, ForeignKey("boq.boq_id", ondelete="CASCADE"))
    category_id = Column(
        Integer, ForeignKey("boq_categories.boq_category_id", ondelete="SET NULL"), nullable=True
    )  # earthwork, concrete, tile
    material_name = Column(String(255), nullable=False)
    rule_item_id = Column(Integer, ForeignKey("rule_items.rule_item_id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Numeric, nullable=False)
    unit = Column(String(50), nullable=False)
    quantity_basis = Column(
        Enum("per_m3", "per_m2", "per_m", "per_unit", "absolute", name="boqitem_basis_enum"),
        nullable=True,
    )
    standard = Column(String(100))  # IS code
    notes = Column(Text)
    calculation_trace = Column(Text, nullable=True)  # JSON string with inputs/steps

    boq = relationship("BOQ", back_populates="items")
    category = relationship("BOQCategory")
