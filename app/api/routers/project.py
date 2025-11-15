from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if project with same name already exists for this user
    existing_project = db.query(Project).filter(
        Project.user_id == current_user.user_id,
        Project.name == project_data.name
    ).first()
    
    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project with this name already exists"
        )
    
    new_project = Project(
        user_id=current_user.user_id,
        name=project_data.name,
        description=project_data.description
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return new_project


@router.get("", response_model=List[ProjectResponse])
def get_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all projects for the current user"""
    projects = db.query(Project).filter(
        Project.user_id == current_user.user_id
    ).order_by(Project.created_at.desc()).all()
    return projects


@router.get("/list/simple")
def get_projects_simple(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get simplified project list for dropdowns (id and name only)"""
    projects = db.query(
        Project.project_id,
        Project.name
    ).filter(
        Project.user_id == current_user.user_id
    ).order_by(Project.created_at.desc()).all()
    
    return [
        {"project_id": p.project_id, "name": p.name}
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.project_id == project_id,
        Project.user_id == current_user.user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.project_id == project_id,
        Project.user_id == current_user.user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if updating name to a name that already exists
    if project_data.name is not None and project_data.name != project.name:
        existing_project = db.query(Project).filter(
            Project.user_id == current_user.user_id,
            Project.name == project_data.name,
            Project.project_id != project_id
        ).first()
        
        if existing_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project with this name already exists"
            )
        
        project.name = project_data.name
    
    if project_data.description is not None:
        project.description = project_data.description
    
    db.commit()
    db.refresh(project)
    
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.project_id == project_id,
        Project.user_id == current_user.user_id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    db.delete(project)
    db.commit()
    
    return None
