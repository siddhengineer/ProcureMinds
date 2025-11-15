from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.vendor import VendorCreate, VendorResponse
from app.outbound.vendor_list_parser import (
    create_vendor,
    create_vendors_bulk,
    create_vendors_from_excel,
    get_vendor_by_id,
    get_vendors_by_user,
    delete_vendor
)

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.post("/", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def add_vendor(
    vendor_data: VendorCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Add a single vendor manually"""
    try:
        vendor = create_vendor(db, vendor_data, user_id)
        return vendor
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/bulk", response_model=List[VendorResponse], status_code=status.HTTP_201_CREATED)
def add_vendors_bulk(
    vendors_data: List[VendorCreate],
    user_id: int,
    db: Session = Depends(get_db)
):
    """Add multiple vendors at once"""
    try:
        vendors = create_vendors_bulk(db, vendors_data, user_id)
        return vendors
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/upload-excel", response_model=List[VendorResponse], status_code=status.HTTP_201_CREATED)
async def upload_vendors_excel(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload vendors from Excel file"""
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        content = await file.read()
        vendors = create_vendors_from_excel(db, content, user_id)
        return vendors
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing Excel file: {str(e)}"
        )


@router.get("/", response_model=List[VendorResponse])
def list_vendors(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all vendors for a user"""
    vendors = get_vendors_by_user(db, user_id, skip, limit)
    return vendors


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific vendor by ID"""
    vendor = get_vendor_by_id(db, vendor_id, user_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    return vendor


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_vendor(
    vendor_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Delete a vendor"""
    success = delete_vendor(db, vendor_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    return None
