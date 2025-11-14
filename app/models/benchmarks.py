from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Text,
    TIMESTAMP,
    ForeignKey,
    Enum,
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
    quality_standard = Column(String(100))  # e.g., IS 12269
    # Unified quantity representation
    amount = Column(Numeric, nullable=True)  # numeric value
    unit = Column(String(50))  # e.g., bags, m3, m2
    basis = Column(
        Enum("per_m3", "per_m2", "per_m", "per_unit", "absolute", name="benchmark_basis_enum"),
        nullable=True,
    )
    default_wastage_multiplier = Column(Numeric, server_default="1.0")
    dimensions = Column(Numeric, nullable=True)
    notes = Column(Text)
    required_by = Column(TIMESTAMP)  # when the user needs the material
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    project = relationship("Project")
    category = relationship("BenchmarkCategory")

    __table_args__ = ()
 