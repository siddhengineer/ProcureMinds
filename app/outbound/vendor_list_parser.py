from sqlalchemy.orm import Session
from typing import List, Optional
import io
import openpyxl
from openpyxl.workbook.workbook import Workbook

from app.models.vendors import Vendor
from app.schemas.vendor import VendorCreate, VendorCSVRow, MATERIAL_MAPPING


def parse_materials_to_ids(materials_str: Optional[str]) -> Optional[List[int]]:
    """Convert comma-separated material names to list of IDs"""
    if not materials_str:
        return None
    
    materials = [m.strip().lower() for m in materials_str.split(',')]
    material_ids = [MATERIAL_MAPPING[m] for m in materials if m in MATERIAL_MAPPING]
    
    return material_ids if material_ids else None


def create_vendor(db: Session, vendor_data: VendorCreate, user_id: int) -> Vendor:
    """Create a single vendor or update if email exists"""
    material_ids = parse_materials_to_ids(vendor_data.materials)
    
    # Check if vendor with this email already exists for this user
    existing_vendor = db.query(Vendor).filter(
        Vendor.email == vendor_data.email,
        Vendor.user_id == user_id
    ).first()
    
    if existing_vendor:
        # Update existing vendor
        existing_vendor.name = vendor_data.name
        existing_vendor.phone_number = vendor_data.phone
        existing_vendor.location = vendor_data.location
        existing_vendor.material = material_ids
        db.commit()
        db.refresh(existing_vendor)
        return existing_vendor
    else:
        # Create new vendor
        vendor = Vendor(
            name=vendor_data.name,
            email=vendor_data.email,
            phone_number=vendor_data.phone,
            location=vendor_data.location,
            material=material_ids,
            user_id=user_id
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
        return vendor


def create_vendors_bulk(db: Session, vendors_data: List[VendorCreate], user_id: int) -> List[Vendor]:
    """Create multiple vendors at once or update if email exists"""
    vendors = []
    
    # Get all existing vendors for this user to check for duplicates
    existing_vendors_dict = {
        v.email: v for v in db.query(Vendor).filter(Vendor.user_id == user_id).all()
    }
    
    for vendor_data in vendors_data:
        material_ids = parse_materials_to_ids(vendor_data.materials)
        
        if vendor_data.email in existing_vendors_dict:
            # Update existing vendor
            existing_vendor = existing_vendors_dict[vendor_data.email]
            existing_vendor.name = vendor_data.name
            existing_vendor.phone_number = vendor_data.phone
            existing_vendor.location = vendor_data.location
            existing_vendor.material = material_ids
            vendors.append(existing_vendor)
        else:
            # Create new vendor
            vendor = Vendor(
                name=vendor_data.name,
                email=vendor_data.email,
                phone_number=vendor_data.phone,
                location=vendor_data.location,
                material=material_ids,
                user_id=user_id
            )
            db.add(vendor)
            vendors.append(vendor)
            # Add to dict to prevent duplicates within the same batch
            existing_vendors_dict[vendor_data.email] = vendor
    
    db.commit()
    
    for vendor in vendors:
        db.refresh(vendor)
    
    return vendors


def create_vendors_from_excel(db: Session, excel_content: bytes, user_id: int) -> List[Vendor]:
    """Create multiple vendors from Excel file content"""
    vendors = []
    
    # Load workbook from bytes
    excel_file = io.BytesIO(excel_content)
    workbook = openpyxl.load_workbook(excel_file)
    sheet = workbook.active
    
    # Expected headers (case-insensitive)
    expected_headers = {'name', 'email', 'phone', 'location', 'materials'}
    
    # Read headers from first row
    headers = []
    header_row = sheet[1]
    for cell in header_row:
        if cell.value:
            headers.append(str(cell.value).strip().lower())
    
    # Validate headers
    if not expected_headers.issubset(set(headers)):
        missing = expected_headers - set(headers)
        raise ValueError(f"Excel missing required columns: {', '.join(missing)}")
    
    # Create header index mapping
    header_map = {header: idx for idx, header in enumerate(headers)}
    
    # Get all existing vendors for this user to check for duplicates
    existing_vendors_dict = {
        v.email: v for v in db.query(Vendor).filter(Vendor.user_id == user_id).all()
    }
    
    # Process data rows (starting from row 2)
    for row_idx in range(2, sheet.max_row + 1):
        row = sheet[row_idx]
        
        # Extract values based on header positions
        name = str(row[header_map['name']].value).strip() if row[header_map['name']].value else None
        email = str(row[header_map['email']].value).strip() if row[header_map['email']].value else None
        phone = str(row[header_map['phone']].value).strip() if row[header_map['phone']].value else None
        location = str(row[header_map['location']].value).strip() if row[header_map['location']].value else None
        materials = str(row[header_map['materials']].value).strip() if row[header_map['materials']].value else None
        
        # Skip empty rows
        if not name and not email:
            continue
        
        # Validate required fields
        if not email:
            raise ValueError(f"Row {row_idx}: Email is required")
        
        # Validate and create vendor
        vendor_data = VendorCSVRow(
            Name=name or "",
            Email=email,
            Phone=phone,
            Location=location,
            Materials=materials
        )
        
        material_ids = parse_materials_to_ids(vendor_data.Materials)
        
        if email in existing_vendors_dict:
            # Update existing vendor
            existing_vendor = existing_vendors_dict[email]
            existing_vendor.name = vendor_data.Name
            existing_vendor.phone_number = vendor_data.Phone
            existing_vendor.location = vendor_data.Location
            existing_vendor.material = material_ids
            vendors.append(existing_vendor)
        else:
            # Create new vendor
            vendor = Vendor(
                name=vendor_data.Name,
                email=vendor_data.Email,
                phone_number=vendor_data.Phone,
                location=vendor_data.Location,
                material=material_ids,
                user_id=user_id
            )
            db.add(vendor)
            vendors.append(vendor)
            # Add to dict to prevent duplicates within the same Excel file
            existing_vendors_dict[email] = vendor
    
    db.commit()
    
    for vendor in vendors:
        db.refresh(vendor)
    
    return vendors


def get_vendor_by_id(db: Session, vendor_id: int, user_id: int) -> Optional[Vendor]:
    """Get a vendor by ID for a specific user"""
    return db.query(Vendor).filter(
        Vendor.vendor_id == vendor_id,
        Vendor.user_id == user_id
    ).first()


def get_vendors_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Vendor]:
    """Get all vendors for a user"""
    return db.query(Vendor).filter(
        Vendor.user_id == user_id
    ).offset(skip).limit(limit).all()


def delete_vendor(db: Session, vendor_id: int, user_id: int) -> bool:
    """Delete a vendor"""
    vendor = get_vendor_by_id(db, vendor_id, user_id)
    if not vendor:
        return False
    
    db.delete(vendor)
    db.commit()
    return True
