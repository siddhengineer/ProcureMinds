from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Text,
    TIMESTAMP,
    ForeignKey,
    Enum,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class BenchmarkMaterial(Base):
    __tablename__ = "benchmark_materials"

    benchmark_material_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    category_id = Column(
        Integer,
        ForeignKey("item_categories.item_category_id", ondelete="SET NULL"),
        nullable=True,
    )
    name = Column(String(100), nullable=False)  # e.g., OPC 53, Fine Sand
    material_state = Column(
        Enum("solid", "liquid", name="material_state_enum"),
        nullable=False,
    )
    quality_standard = Column(String(100))  # e.g., IS 12269
    default_quantity_per_m3 = Column(
        Numeric,
        comment="For solid materials: default usage per m3",
    )
    unit = Column(String(50))  # e.g., bags, m3, m2
    default_wastage_multiplier = Column(Numeric, server_default="1.0")
    dimensions = Column(Numeric, nullable=True)
    quantity = Column(
        Numeric,
        nullable=True,
        comment="For liquid materials: numeric amount (with unit like L/kg)",
    )
    notes = Column(Text)
    required_by = Column(TIMESTAMP)  # when the user needs the material
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    project = relationship("Project")
    category = relationship("BenchmarkCategory")

    __table_args__ = (
        CheckConstraint(
            "(material_state = 'liquid' AND quantity IS NOT NULL AND default_quantity_per_m3 IS NULL) OR "
            "(material_state = 'solid' AND default_quantity_per_m3 IS NOT NULL AND quantity IS NULL)",
            name="ck_benchmark_materials_state_quantity_rules",
        ),
    )
 