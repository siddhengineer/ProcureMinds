"""
BOQ Listing Router

This router provides endpoints to list BOQs grouped by projects.

Example cURL commands:

1. Get all BOQs grouped by project:
curl -X GET "http://localhost:8000/api/boq-listings/by-project?user_id=1"

2. Get BOQs for a specific project:
curl -X GET "http://localhost:8000/api/boq-listings/project/1?user_id=1"
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.listings.project_boq import get_boqs_by_project, get_boqs_for_project

router = APIRouter(prefix="/boq-listings", tags=["BOQ Listings"])


@router.get("/by-project")
def list_boqs_by_project(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all BOQs grouped by project for a specific user.
    
    Returns a list of projects, each containing their associated BOQs.
    Each BOQ includes:
    - boq_id: BOQ identifier
    - boq_name: Formatted as "BOQ#<id>" (e.g., "BOQ#4")
    - status: Current status (draft/approved/sent)
    - item_count: Number of items in the BOQ
    - created_at: Creation timestamp
    - updated_at: Last update timestamp
    
    Example Response:
    [
        {
            "project_id": 1,
            "project_name": "Construction Project A",
            "boqs": [
                {
                    "boq_id": 4,
                    "boq_name": "BOQ#4",
                    "status": "draft",
                    "item_count": 15,
                    "created_at": "2024-01-15T10:30:00",
                    "updated_at": "2024-01-15T10:30:00"
                }
            ]
        }
    ]
    """
    try:
        result = get_boqs_by_project(db, user_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching BOQs: {str(e)}"
        )


@router.get("/project/{project_id}")
def list_boqs_for_specific_project(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all BOQs for a specific project.
    
    Args:
        project_id: The ID of the project to fetch BOQs for
        user_id: The ID of the user
    
    Returns a list of BOQs for the specified project.
    Each BOQ includes:
    - boq_id: BOQ identifier
    - boq_name: Formatted as "BOQ#<id>" (e.g., "BOQ#4")
    - status: Current status (draft/approved/sent)
    - item_count: Number of items in the BOQ
    - created_at: Creation timestamp
    - updated_at: Last update timestamp
    
    Example Response:
    [
        {
            "boq_id": 4,
            "boq_name": "BOQ#4",
            "status": "draft",
            "item_count": 15,
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T10:30:00"
        }
    ]
    """
    try:
        result = get_boqs_for_project(db, user_id, project_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching BOQs for project: {str(e)}"
        )
