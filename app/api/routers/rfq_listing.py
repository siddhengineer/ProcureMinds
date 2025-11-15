"""
RFQ Listing Router

This router provides endpoints to list RFQs with complete details including vendor, project, and BOQ information.

Example cURL commands:

1. Get all RFQs grouped by project:
curl -X GET "http://localhost:8000/api/rfq-listings/by-project?user_id=1"

2. Get RFQs for a specific project:
curl -X GET "http://localhost:8000/api/rfq-listings/project/1?user_id=1"

3. Get all RFQs (not grouped):
curl -X GET "http://localhost:8000/api/rfq-listings/all?user_id=1"

4. Get a specific RFQ by ID:
curl -X GET "http://localhost:8000/api/rfq-listings/5?user_id=1"
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.listings.rfqs_listing import (
    get_rfqs_for_project,
    get_rfqs_grouped_by_project,
    get_rfq_by_id
)

router = APIRouter(prefix="/rfq-listings", tags=["RFQ Listings"])


@router.get("/by-project")
def list_rfqs_by_project(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all RFQs grouped by project for a specific user.
    
    Returns a list of projects, each containing their associated RFQs.
    Each RFQ includes complete details:
    - rfq_id: RFQ identifier
    - rfq_name: Formatted as "RFQ#<id>" (e.g., "RFQ#5")
    - vendor_id, vendor_name, vendor_email: Vendor information
    - boq_id, boq_name: Associated BOQ (formatted as "BOQ#<id>")
    - status: Current status (pending/sent/replied/closed)
    - subject: Email subject
    - incoming_mail: Incoming email content
    - outgoing_mail: Outgoing RFQ email content
    - reply_received: Boolean flag indicating if reply was received
    - created_at, updated_at: Timestamps
    
    Example Response:
    [
        {
            "project_id": 1,
            "project_name": "Construction Project A",
            "rfqs": [
                {
                    "rfq_id": 5,
                    "rfq_name": "RFQ#5",
                    "vendor_id": 2,
                    "vendor_name": "ABC Suppliers",
                    "vendor_email": "contact@abcsuppliers.com",
                    "boq_id": 4,
                    "boq_name": "BOQ#4",
                    "status": "sent",
                    "subject": "Request for Quotation - Construction Materials",
                    "incoming_mail": null,
                    "outgoing_mail": "Dear Vendor...",
                    "reply_received": false,
                    "created_at": "2024-01-15T10:30:00",
                    "updated_at": "2024-01-15T10:30:00"
                }
            ]
        }
    ]
    """
    try:
        result = get_rfqs_grouped_by_project(db, user_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching RFQs: {str(e)}"
        )


@router.get("/project/{project_id}")
def list_rfqs_for_specific_project(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all RFQs for a specific project.
    
    Args:
        project_id: The ID of the project to fetch RFQs for
        user_id: The ID of the user
    
    Returns a list of RFQs for the specified project with complete details.
    
    Example Response:
    [
        {
            "rfq_id": 5,
            "rfq_name": "RFQ#5",
            "project_id": 1,
            "project_name": "Construction Project A",
            "vendor_id": 2,
            "vendor_name": "ABC Suppliers",
            "vendor_email": "contact@abcsuppliers.com",
            "boq_id": 4,
            "boq_name": "BOQ#4",
            "status": "sent",
            "subject": "Request for Quotation - Construction Materials",
            "incoming_mail": null,
            "outgoing_mail": "Dear Vendor...",
            "reply_received": false,
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T10:30:00"
        }
    ]
    """
    try:
        result = get_rfqs_for_project(db, user_id, project_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching RFQs for project: {str(e)}"
        )


@router.get("/all")
def list_all_rfqs(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all RFQs for a specific user (not grouped by project).
    
    Returns a flat list of all RFQs with complete details.
    
    Example Response:
    [
        {
            "rfq_id": 5,
            "rfq_name": "RFQ#5",
            "project_id": 1,
            "project_name": "Construction Project A",
            "vendor_id": 2,
            "vendor_name": "ABC Suppliers",
            "vendor_email": "contact@abcsuppliers.com",
            "boq_id": 4,
            "boq_name": "BOQ#4",
            "status": "sent",
            "subject": "Request for Quotation",
            "incoming_mail": null,
            "outgoing_mail": "Dear Vendor...",
            "reply_received": false,
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T10:30:00"
        }
    ]
    """
    try:
        result = get_rfqs_for_project(db, user_id, project_id=None)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching all RFQs: {str(e)}"
        )


@router.get("/{rfq_id}")
def get_rfq_details(
    rfq_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific RFQ.
    
    Args:
        rfq_id: The ID of the RFQ to fetch
        user_id: The ID of the user
    
    Returns complete RFQ details including additional vendor information (phone, location).
    
    Example Response:
    {
        "rfq_id": 5,
        "rfq_name": "RFQ#5",
        "project_id": 1,
        "project_name": "Construction Project A",
        "vendor_id": 2,
        "vendor_name": "ABC Suppliers",
        "vendor_email": "contact@abcsuppliers.com",
        "vendor_phone": "+1234567890",
        "vendor_location": "New York",
        "boq_id": 4,
        "boq_name": "BOQ#4",
        "status": "sent",
        "subject": "Request for Quotation - Construction Materials",
        "incoming_mail": null,
        "outgoing_mail": "Dear Vendor...",
        "reply_received": false,
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:30:00"
    }
    """
    try:
        result = get_rfq_by_id(db, user_id, rfq_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"RFQ with ID {rfq_id} not found"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching RFQ details: {str(e)}"
        )
