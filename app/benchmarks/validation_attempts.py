from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from app.models.validation_attempts import ValidationAttempt


def save_validation_attempt(
    db: Session,
    *,
    user_id: int,
    raw_input_text: str,
    status: str,
    project_id: Optional[int] = None,
    parent_attempt_id: Optional[int] = None,
    extracted_payload: Optional[Dict[str, Any]] = None,
    missing_fields: Optional[List[str]] = None,
    invalid_fields: Optional[List[str]] = None,
    unit_warnings: Optional[List[str]] = None,
) -> ValidationAttempt:
    attempt = ValidationAttempt(
        user_id=user_id,
        project_id=project_id,
        parent_attempt_id=parent_attempt_id,
        status=status,
        raw_input_text=raw_input_text,
        extracted_payload=extracted_payload or None,
        missing_fields=missing_fields or None,
        invalid_fields=invalid_fields or None,
        unit_warnings=unit_warnings or None,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt
