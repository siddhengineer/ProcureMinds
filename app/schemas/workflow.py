from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class WorkflowBase(BaseModel):
    name: str
    input_data: Optional[dict[str, Any]] = None


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    output_data: Optional[dict[str, Any]] = None


class WorkflowResponse(WorkflowBase):
    id: int
    status: str
    output_data: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
