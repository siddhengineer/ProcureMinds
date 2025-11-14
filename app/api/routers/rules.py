from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.benchmarks.ruleset_engine import generate_ruleset


router = APIRouter(prefix="/rules", tags=["rules"])


class RulesetGenerateRequest(BaseModel):
    user_id: int
    project_id: int
    validation_attempt_id: int
    rule_set_name: str | None = "default"
    preview: bool = False


class RuleItemPreview(BaseModel):
    category: Optional[str]
    key: str
    value: Optional[float] = None
    formula: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None


class RulesetGenerateResponse(BaseModel):
    rule_set_id: int
    items_created: int
    items: Optional[List[RuleItemPreview]] = None


@router.post("/generate", response_model=RulesetGenerateResponse)
def rules_generate(payload: RulesetGenerateRequest, db: Session = Depends(get_db)):
    try:
        rs_id, count, items_preview = generate_ruleset(
            db,
            user_id=payload.user_id,
            project_id=payload.project_id,
            validation_attempt_id=payload.validation_attempt_id,
            rule_set_name=payload.rule_set_name or "default",
            preview=payload.preview,
        )
        return RulesetGenerateResponse(
            rule_set_id=rs_id,
            items_created=count,
            items=items_preview if payload.preview else None,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
