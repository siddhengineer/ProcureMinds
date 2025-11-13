from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowUpdate
from app.services.workflow_service import WorkflowService
from app.workflows.langgraph_workflow import WorkflowGraph

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/", response_model=WorkflowResponse, status_code=201)
def create_workflow(
    workflow: WorkflowCreate,
    db: Session = Depends(get_db)
):
    return WorkflowService.create_workflow(db=db, workflow=workflow)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    db_workflow = WorkflowService.get_workflow(db=db, workflow_id=workflow_id)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return db_workflow


@router.get("/", response_model=list[WorkflowResponse])
def list_workflows(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return WorkflowService.get_workflows(db=db, skip=skip, limit=limit)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: int,
    workflow_update: WorkflowUpdate,
    db: Session = Depends(get_db)
):
    db_workflow = WorkflowService.update_workflow(
        db=db,
        workflow_id=workflow_id,
        workflow_update=workflow_update
    )
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return db_workflow


@router.delete("/{workflow_id}", status_code=204)
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    success = WorkflowService.delete_workflow(db=db, workflow_id=workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")


@router.post("/{workflow_id}/execute", response_model=dict[str, Any])
async def execute_workflow(
    workflow_id: int,
    db: Session = Depends(get_db)
):
    db_workflow = WorkflowService.get_workflow(db=db, workflow_id=workflow_id)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow_graph = WorkflowGraph()
    result = await workflow_graph.execute(db_workflow.input_data or {})

    WorkflowService.update_workflow(
        db=db,
        workflow_id=workflow_id,
        workflow_update=WorkflowUpdate(status="completed", output_data=result)
    )

    return result
