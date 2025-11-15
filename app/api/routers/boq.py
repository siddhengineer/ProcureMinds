from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.boq import BOQ
from app.models.boq_item import BOQItem
from app.models.project import Project
from app.schemas.boq import (
    BOQListResponse,
    BOQDetailResponse,
    BOQCreate,
    BOQItemCreate,
    BOQItemResponse
)

router = APIRouter(prefix="/boq", tags=["BOQ"])


@router.get("", response_model=List[BOQListResponse])
def list_boqs(
    project_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all BOQs for the current user, optionally filtered by project"""
    query = db.query(
        BOQ.boq_id,
        BOQ.project_id,
        BOQ.status,
        BOQ.created_at,
        BOQ.updated_at,
        Project.name.label('project_name'),
        func.count(BOQItem.boq_item_id).label('item_count')
    ).outerjoin(BOQItem, BOQ.boq_id == BOQItem.boq_id
    ).outerjoin(Project, BOQ.project_id == Project.project_id
    ).filter(
        BOQ.user_id == current_user.user_id
    ).group_by(
        BOQ.boq_id,
        BOQ.project_id,
        BOQ.status,
        BOQ.created_at,
        BOQ.updated_at,
        Project.name
    )
    
    if project_id:
        query = query.filter(BOQ.project_id == project_id)
    
    boqs = query.order_by(BOQ.created_at.desc()).all()
    
    return [
        {
            "boq_id": boq.boq_id,
            "project_id": boq.project_id,
            "project_name": boq.project_name,
            "status": boq.status,
            "item_count": boq.item_count,
            "created_at": boq.created_at,
            "updated_at": boq.updated_at
        }
        for boq in boqs
    ]


@router.get("/{boq_id}", response_model=BOQDetailResponse)
def get_boq(
    boq_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed BOQ with all items"""
    boq = db.query(BOQ).filter(
        BOQ.boq_id == boq_id,
        BOQ.user_id == current_user.user_id
    ).first()
    
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOQ not found"
        )
    
    return boq


@router.post("", response_model=BOQDetailResponse, status_code=status.HTTP_201_CREATED)
def create_boq(
    boq_data: BOQCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new BOQ"""
    # Verify project belongs to user if project_id is provided
    if boq_data.project_id:
        project = db.query(Project).filter(
            Project.project_id == boq_data.project_id,
            Project.user_id == current_user.user_id
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
    
    new_boq = BOQ(
        user_id=current_user.user_id,
        project_id=boq_data.project_id,
        rule_set_id=boq_data.rule_set_id,
        status=boq_data.status
    )
    
    db.add(new_boq)
    db.commit()
    db.refresh(new_boq)
    
    return new_boq


@router.post("/{boq_id}/items", response_model=BOQItemResponse, status_code=status.HTTP_201_CREATED)
def add_boq_item(
    boq_id: int,
    item_data: BOQItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an item to a BOQ"""
    # Verify BOQ belongs to user
    boq = db.query(BOQ).filter(
        BOQ.boq_id == boq_id,
        BOQ.user_id == current_user.user_id
    ).first()
    
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOQ not found"
        )
    
    new_item = BOQItem(
        boq_id=boq_id,
        material_name=item_data.material_name,
        quantity=item_data.quantity,
        unit=item_data.unit,
        category_id=item_data.category_id,
        standard=item_data.standard,
        notes=item_data.notes
    )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    return new_item


@router.delete("/{boq_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_boq(
    boq_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a BOQ"""
    boq = db.query(BOQ).filter(
        BOQ.boq_id == boq_id,
        BOQ.user_id == current_user.user_id
    ).first()
    
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOQ not found"
        )
    
    db.delete(boq)
    db.commit()
    
    return None


@router.put("/{boq_id}/status")
def update_boq_status(
    boq_id: int,
    status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update BOQ status (draft/approved/sent)"""
    boq = db.query(BOQ).filter(
        BOQ.boq_id == boq_id,
        BOQ.user_id == current_user.user_id
    ).first()
    
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOQ not found"
        )
    
    if status not in ["draft", "approved", "sent"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be: draft, approved, or sent"
        )
    
    boq.status = status
    db.commit()
    db.refresh(boq)
    
    return {"message": "Status updated successfully", "status": boq.status}
