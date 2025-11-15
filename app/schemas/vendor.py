from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime


# Material mapping
MATERIAL_MAPPING = {
    "sand": 1,
    "tile": 2,
    "steel": 3,
    "cement": 4,
    "granular": 5
}

VALID_MATERIALS = set(MATERIAL_MAPPING.keys())


class VendorBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    materials: Optional[str] = None  # Comma-separated material names
    
    @field_validator('materials')
    @classmethod
    def validate_materials(cls, v):
        if v is None:
            return v
        materials = [m.strip().lower() for m in v.split(',')]
        invalid = [m for m in materials if m and m not in VALID_MATERIALS]
        if invalid:
            raise ValueError(f"Invalid materials: {', '.join(invalid)}. Valid options: {', '.join(VALID_MATERIALS)}")
        return v


class VendorCreate(VendorBase):
    pass


class VendorCSVRow(BaseModel):
    Name: str
    Email: EmailStr
    Phone: Optional[str] = None
    Location: Optional[str] = None
    Materials: Optional[str] = None
    
    @field_validator('Materials')
    @classmethod
    def validate_materials(cls, v):
        if v is None:
            return v
        materials = [m.strip().lower() for m in v.split(',')]
        invalid = [m for m in materials if m and m not in VALID_MATERIALS]
        if invalid:
            raise ValueError(f"Invalid materials: {', '.join(invalid)}. Valid options: {', '.join(VALID_MATERIALS)}")
        return v


class VendorResponse(BaseModel):
    vendor_id: int
    name: Optional[str]
    email: str
    phone_number: Optional[str]
    location: Optional[str]
    material: Optional[List[int]]
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
