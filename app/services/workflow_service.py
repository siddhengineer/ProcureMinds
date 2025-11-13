from typing import Optional

from sqlalchemy.orm import Session

from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate


class WorkflowService:
    @staticmethod
    def create_workflow(db: Session, workflow: WorkflowCreate) -> Workflow:
        db_workflow = Workflow(
            name=workflow.name,
            input_data=workflow.input_data
        )
        db.add(db_workflow)
        db.commit()
        db.refresh(db_workflow)
        return db_workflow

    @staticmethod
    def get_workflow(db: Session, workflow_id: int) -> Optional[Workflow]:
        return db.query(Workflow).filter(Workflow.id == workflow_id).first()

    @staticmethod
    def get_workflows(db: Session, skip: int = 0, limit: int = 100) -> list[Workflow]:
        return db.query(Workflow).offset(skip).limit(limit).all()

    @staticmethod
    def update_workflow(db: Session, workflow_id: int, workflow_update: WorkflowUpdate) -> Optional[Workflow]:
        db_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if db_workflow:
            update_data = workflow_update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_workflow, key, value)
            db.commit()
            db.refresh(db_workflow)
        return db_workflow

    @staticmethod
    def delete_workflow(db: Session, workflow_id: int) -> bool:
        db_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if db_workflow:
            db.delete(db_workflow)
            db.commit()
            return True
        return False
