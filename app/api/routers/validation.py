from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.validation import ValidationRequest, ValidationResponse
from app.services.validation_engine import run_validation


router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/attempts", response_model=ValidationResponse)
def create_validation_attempt(payload: ValidationRequest, db: Session = Depends(get_db)):
    try:
        result = run_validation(
            db,
            user_id=payload.user_id,
            project_id=payload.project_id,
            raw_input_text=payload.raw_input_text,
        )
        return ValidationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
