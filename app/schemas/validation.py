from typing import List, Optional, Literal
from decimal import Decimal
from pydantic import BaseModel, Field


class DimValueIn(BaseModel):
    value: Decimal
    unit: str


class RoomRelationIn(BaseModel):
    source: str
    relation: Literal["adjacent", "attached_to", "outer", "above", "below", "near", "opposite"]
    target: str


class RoomIn(BaseModel):
    name: str
    length: Optional[DimValueIn] = None
    width: Optional[DimValueIn] = None
    height: Optional[DimValueIn] = None
    wall_thickness: Optional[DimValueIn] = None
    relations: List[RoomRelationIn] = Field(default_factory=list)


class ValidationRequest(BaseModel):
    user_id: int
    project_id: Optional[int] = None
    raw_input_text: str


class ValidationResponse(BaseModel):
    validation_attempt_id: int
    status: Literal["valid", "invalid", "needs_more_info"]
    missing_fields: List[str] = Field(default_factory=list)
    invalid_fields: List[str] = Field(default_factory=list)
    unit_warnings: List[str] = Field(default_factory=list)
