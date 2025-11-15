from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.boq import BOQ
from app.models.project import Project
from app.models.boq_item import BOQItem


def get_boqs_by_project(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Get all BOQs grouped by project for a specific user.
    
    Args:
        db: Database session
        user_id: User ID to filter BOQs
        
    Returns:
        List of projects with their associated BOQs, each BOQ includes:
        - boq_id
        - boq_name (formatted as BOQ#<id>)
        - status
        - item_count
        - created_at
        - updated_at
    """
    # Query BOQs with project info and item count
    boqs = db.query(
        BOQ.boq_id,
        BOQ.project_id,
        BOQ.status,
        BOQ.created_at,
        BOQ.updated_at,
        Project.name.label('project_name'),
        func.count(BOQItem.boq_item_id).label('item_count')
    ).outerjoin(
        BOQItem, BOQ.boq_id == BOQItem.boq_id
    ).outerjoin(
        Project, BOQ.project_id == Project.project_id
    ).filter(
        BOQ.user_id == user_id
    ).group_by(
        BOQ.boq_id,
        BOQ.project_id,
        BOQ.status,
        BOQ.created_at,
        BOQ.updated_at,
        Project.name
    ).order_by(
        Project.name.asc().nullsfirst(),
        BOQ.created_at.desc()
    ).all()
    
    # Group BOQs by project
    projects_dict = {}
    
    for boq in boqs:
        project_id = boq.project_id or 0  # Use 0 for BOQs without project
        project_name = boq.project_name or "Unassigned"
        
        if project_id not in projects_dict:
            projects_dict[project_id] = {
                "project_id": project_id if project_id != 0 else None,
                "project_name": project_name,
                "boqs": []
            }
        
        projects_dict[project_id]["boqs"].append({
            "boq_id": boq.boq_id,
            "boq_name": f"BOQ#{boq.boq_id}",
            "status": boq.status,
            "item_count": boq.item_count,
            "created_at": boq.created_at,
            "updated_at": boq.updated_at
        })
    
    # Convert dict to list
    return list(projects_dict.values())


def get_boqs_for_project(db: Session, user_id: int, project_id: int) -> List[Dict[str, Any]]:
    """
    Get all BOQs for a specific project and user.
    
    Args:
        db: Database session
        user_id: User ID to filter BOQs
        project_id: Project ID to filter BOQs
        
    Returns:
        List of BOQs with:
        - boq_id
        - boq_name (formatted as BOQ#<id>)
        - status
        - item_count
        - created_at
        - updated_at
    """
    boqs = db.query(
        BOQ.boq_id,
        BOQ.status,
        BOQ.created_at,
        BOQ.updated_at,
        func.count(BOQItem.boq_item_id).label('item_count')
    ).outerjoin(
        BOQItem, BOQ.boq_id == BOQItem.boq_id
    ).filter(
        BOQ.user_id == user_id,
        BOQ.project_id == project_id
    ).group_by(
        BOQ.boq_id,
        BOQ.status,
        BOQ.created_at,
        BOQ.updated_at
    ).order_by(
        BOQ.created_at.desc()
    ).all()
    
    return [
        {
            "boq_id": boq.boq_id,
            "boq_name": f"BOQ#{boq.boq_id}",
            "status": boq.status,
            "item_count": boq.item_count,
            "created_at": boq.created_at,
            "updated_at": boq.updated_at
        }
        for boq in boqs
    ]
