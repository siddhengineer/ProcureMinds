from sqlalchemy import (
    Column,
    Integer,
    Text,
    TIMESTAMP,
    ForeignKey,
    Enum,
    JSON,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ValidationAttempt(Base):
    __tablename__ = "validation_attempts"

    validation_attempt_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True)
    parent_attempt_id = Column(
        Integer,
        ForeignKey("validation_attempts.validation_attempt_id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(
        Enum("valid", "invalid", "needs_more_info", name="validation_status_enum"),
        nullable=False,
    )
    raw_input_text = Column(Text, nullable=False)
    extracted_payload = Column(JSON, nullable=True)
    missing_fields = Column(JSON, nullable=True)
    invalid_fields = Column(JSON, nullable=True)
    unit_warnings = Column(JSON, nullable=True)
    derived_metrics = Column(JSON, nullable=True)  # computed geometry like floor_area_m2, volumes

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User")
    project = relationship("Project")
    parent_attempt = relationship("ValidationAttempt", remote_side=[validation_attempt_id])
