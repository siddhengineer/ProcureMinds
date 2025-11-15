from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class BOQItemResponse(BaseModel):
    boq_item_id: int
    material_name: str
    quantity: Decimal
    unit: str
    category_id: Optional[int] = None
    standard: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class BOQListResponse(BaseModel):
    boq_id: int
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    status: str
    item_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BOQDetailResponse(BaseModel):
    boq_id: int
    user_id: int
    project_id: Optional[int] = None
    rule_set_id: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime
    items: List[BOQItemResponse]

    class Config:
        from_attributes = True


class BOQCreate(BaseModel):
    project_id: Optional[int] = None
    rule_set_id: Optional[int] = None
    status: str = "draft"


class BOQItemCreate(BaseModel):
    material_name: str
    quantity: Decimal
    unit: str
    category_id: Optional[int] = None
    standard: Optional[str] = None
    notes: Optional[str] = None
