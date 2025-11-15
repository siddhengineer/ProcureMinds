from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.rfqs import RFQ
from app.models.vendors import Vendor
from app.models.project import Project
from app.models.boq import BOQ


def get_rfqs_for_project(
    db: Session, 
    user_id: int, 
    project_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get all RFQs for a specific project (or all RFQs if project_id is None).
    
    Args:
        db: Database session
        user_id: User ID to filter RFQs
        project_id: Optional project ID to filter RFQs. If None, returns all RFQs for the user.
        
    Returns:
        List of RFQs with complete details including:
        - rfq_id
        - rfq_name (formatted as RFQ#<id>)
        - project_id
        - project_name
        - vendor_id
        - vendor_name
        - vendor_email
        - boq_id
        - boq_name (formatted as BOQ#<id>)
        - status
        - subject
        - incoming_mail
        - outgoing_mail
        - reply_received
        - created_at
        - updated_at
    """
    query = db.query(
        RFQ.rfq_id,
        RFQ.project_id,
        RFQ.vendor_id,
        RFQ.boq_id,
        RFQ.status,
        RFQ.subject,
        RFQ.incoming_mail,
        RFQ.outgoing_mail,
        RFQ.reply_received,
        RFQ.created_at,
        RFQ.updated_at,
        Project.name.label('project_name'),
        Vendor.name.label('vendor_name'),
        Vendor.email.label('vendor_email')
    ).outerjoin(
        Project, RFQ.project_id == Project.project_id
    ).outerjoin(
        Vendor, RFQ.vendor_id == Vendor.vendor_id
    ).filter(
        RFQ.user_id == user_id
    )
    
    # Filter by project_id if provided
    if project_id is not None:
        query = query.filter(RFQ.project_id == project_id)
    
    rfqs = query.order_by(RFQ.created_at.desc()).all()
    
    return [
        {
            "rfq_id": rfq.rfq_id,
            "rfq_name": f"RFQ#{rfq.rfq_id}",
            "project_id": rfq.project_id,
            "project_name": rfq.project_name or "Unassigned",
            "vendor_id": rfq.vendor_id,
            "vendor_name": rfq.vendor_name,
            "vendor_email": rfq.vendor_email,
            "boq_id": rfq.boq_id,
            "boq_name": f"BOQ#{rfq.boq_id}" if rfq.boq_id else None,
            "status": rfq.status,
            "subject": rfq.subject,
            "incoming_mail": rfq.incoming_mail,
            "outgoing_mail": rfq.outgoing_mail,
            "reply_received": rfq.reply_received,
            "created_at": rfq.created_at,
            "updated_at": rfq.updated_at
        }
        for rfq in rfqs
    ]


def get_rfqs_grouped_by_project(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Get all RFQs grouped by project for a specific user.
    
    Args:
        db: Database session
        user_id: User ID to filter RFQs
        
    Returns:
        List of projects with their associated RFQs, each RFQ includes all details
    """
    rfqs = db.query(
        RFQ.rfq_id,
        RFQ.project_id,
        RFQ.vendor_id,
        RFQ.boq_id,
        RFQ.status,
        RFQ.subject,
        RFQ.incoming_mail,
        RFQ.outgoing_mail,
        RFQ.reply_received,
        RFQ.created_at,
        RFQ.updated_at,
        Project.name.label('project_name'),
        Vendor.name.label('vendor_name'),
        Vendor.email.label('vendor_email')
    ).outerjoin(
        Project, RFQ.project_id == Project.project_id
    ).outerjoin(
        Vendor, RFQ.vendor_id == Vendor.vendor_id
    ).filter(
        RFQ.user_id == user_id
    ).order_by(
        Project.name.asc().nullsfirst(),
        RFQ.created_at.desc()
    ).all()
    
    # Group RFQs by project
    projects_dict = {}
    
    for rfq in rfqs:
        project_id = rfq.project_id or 0  # Use 0 for RFQs without project
        project_name = rfq.project_name or "Unassigned"
        
        if project_id not in projects_dict:
            projects_dict[project_id] = {
                "project_id": project_id if project_id != 0 else None,
                "project_name": project_name,
                "rfqs": []
            }
        
        projects_dict[project_id]["rfqs"].append({
            "rfq_id": rfq.rfq_id,
            "rfq_name": f"RFQ#{rfq.rfq_id}",
            "vendor_id": rfq.vendor_id,
            "vendor_name": rfq.vendor_name,
            "vendor_email": rfq.vendor_email,
            "boq_id": rfq.boq_id,
            "boq_name": f"BOQ#{rfq.boq_id}" if rfq.boq_id else None,
            "status": rfq.status,
            "subject": rfq.subject,
            "incoming_mail": rfq.incoming_mail,
            "outgoing_mail": rfq.outgoing_mail,
            "reply_received": rfq.reply_received,
            "created_at": rfq.created_at,
            "updated_at": rfq.updated_at
        })
    
    # Convert dict to list
    return list(projects_dict.values())


def get_rfq_by_id(db: Session, user_id: int, rfq_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a single RFQ by ID with all details.
    
    Args:
        db: Database session
        user_id: User ID to verify ownership
        rfq_id: RFQ ID to retrieve
        
    Returns:
        RFQ details or None if not found
    """
    rfq = db.query(
        RFQ.rfq_id,
        RFQ.project_id,
        RFQ.vendor_id,
        RFQ.boq_id,
        RFQ.status,
        RFQ.subject,
        RFQ.incoming_mail,
        RFQ.outgoing_mail,
        RFQ.reply_received,
        RFQ.created_at,
        RFQ.updated_at,
        Project.name.label('project_name'),
        Vendor.name.label('vendor_name'),
        Vendor.email.label('vendor_email'),
        Vendor.phone_number.label('vendor_phone'),
        Vendor.location.label('vendor_location')
    ).outerjoin(
        Project, RFQ.project_id == Project.project_id
    ).outerjoin(
        Vendor, RFQ.vendor_id == Vendor.vendor_id
    ).filter(
        RFQ.user_id == user_id,
        RFQ.rfq_id == rfq_id
    ).first()
    
    if not rfq:
        return None
    
    return {
        "rfq_id": rfq.rfq_id,
        "rfq_name": f"RFQ#{rfq.rfq_id}",
        "project_id": rfq.project_id,
        "project_name": rfq.project_name or "Unassigned",
        "vendor_id": rfq.vendor_id,
        "vendor_name": rfq.vendor_name,
        "vendor_email": rfq.vendor_email,
        "vendor_phone": rfq.vendor_phone,
        "vendor_location": rfq.vendor_location,
        "boq_id": rfq.boq_id,
        "boq_name": f"BOQ#{rfq.boq_id}" if rfq.boq_id else None,
        "status": rfq.status,
        "subject": rfq.subject,
        "incoming_mail": rfq.incoming_mail,
        "outgoing_mail": rfq.outgoing_mail,
        "reply_received": rfq.reply_received,
        "created_at": rfq.created_at,
        "updated_at": rfq.updated_at
    }
