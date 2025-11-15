from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowUpdate
from app.schemas.validation import ValidationRequest, ValidationResponse
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

    workflow_graph = WorkflowGraph(db)
    result = await workflow_graph.execute(db_workflow.input_data or {})

    WorkflowService.update_workflow(
        db=db,
        workflow_id=workflow_id,
        workflow_update=WorkflowUpdate(status="completed", output_data=result)
    )

    return result


# Note: validation-only route removed to prefer a single endpoint for the chatbot flow


class RuleItemPreview(BaseModel):
    category: str | None = None
    key: str
    value: float | None = None
    formula: str | None = None
    unit: str | None = None
    description: str | None = None


class RulesResult(BaseModel):
    rule_set_id: int | None = None
    items_created: int | None = None
    items: list[RuleItemPreview] | None = None
    skipped: bool | None = None
    reason: str | None = None
    error: str | None = None


class ValidateAndGenerateRequest(BaseModel):
    user_id: int
    project_id: int | None = None
    raw_input_text: str


class ValidateAndGenerateResponse(BaseModel):
    validation: ValidationResponse
    rules: RulesResult
    compute: dict[str, Any] | None = None


@router.post("/generate", response_model=ValidateAndGenerateResponse)
async def validate_and_generate(payload: ValidateAndGenerateRequest, db: Session = Depends(get_db)):
    graph = WorkflowGraph(db)
    try:
        res = await graph.execute_validate_and_generate(
            user_id=payload.user_id,
            project_id=payload.project_id,
            raw_input_text=payload.raw_input_text,
        )
        validation_dict = res.get("validation_result") or {}
        # If validation failed, return a structured response indicating the error so
        # the client can show a helpful message without a hard exception.
        if validation_dict.get("status") != "valid":
            # Return a short, standardized 400 response for invalid/insufficient descriptions
            return JSONResponse(
                status_code=400,
                content={
                    "error": "API request failed",
                    "message": "Incomplete or Invalid description.",
                },
            )

        validation = ValidationResponse(**validation_dict)
        rules_dict = res.get("rules_result") or {}
        rules = RulesResult(**rules_dict)
        compute_dict = res.get("compute_result") or {}
        response = ValidateAndGenerateResponse(validation=validation, rules=rules, compute=compute_dict)
        return response
    except HTTPException:
        # Re-raise HTTP exceptions (so their intended status codes are preserved)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
