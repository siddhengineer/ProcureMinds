from sqlalchemy import Column, Integer, String, Numeric, Text, ForeignKey
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
    quantity = Column(Numeric, nullable=False)
    unit = Column(String(50), nullable=False)
    standard = Column(String(100))  # IS code
    notes = Column(Text)

    boq = relationship("BOQ", back_populates="items")
    category = relationship("BOQCategory")
