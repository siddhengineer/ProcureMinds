"""Email Processing Router for Intent Classification and Quotation Extraction."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.intent import EmailInput, IntentClassificationResult
from app.schemas.quotation import (
    AttachmentData,
    BenchmarkItem,
    QuotationExtractionInput,
    QuotationSummary,
)
from app.services.email_extraction import extract_quotation
from app.services.intent import classify_email_intent
from app.workflows.complete_email_workflow import CompleteEmailWorkflow

router = APIRouter(prefix="/email", tags=["email-processing"])


@router.post("/classify-intent", response_model=IntentClassificationResult)
async def classify_intent_endpoint(email_input: EmailInput):
    """
    Classify email intent.

    Determines if email is QUOTATION, QUOTATION_QUERIES, or CASUAL.
    Only QUOTATION emails should be processed further.
    """
    try:
        result = classify_email_intent(
            email_content=email_input.email_content,
            subject=email_input.subject,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Intent classification failed: {str(e)}"
        )


@router.post("/extract-quotation", response_model=QuotationSummary)
async def extract_quotation_endpoint(
    extraction_input: QuotationExtractionInput,
):
    """
    Extract quotation data from vendor email.

    Processes email content and attachments (Excel/PDF) to extract:
    - Vendor information
    - Quoted items with prices
    - Benchmark matching
    - Delivery terms
    """
    try:
        result = extract_quotation(
            email_content=extraction_input.email_content,
            subject=extraction_input.subject,
            sender=extraction_input.sender,
            attachments=extraction_input.attachments,
            benchmarks=extraction_input.benchmarks,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Quotation extraction failed: {str(e)}",
        )


@router.post("/process-complete", response_model=dict[str, Any])
async def process_complete_email(
    email_content: str,
    subject: str = "",
    sender: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
    db: Session = Depends(get_db),
):
    """
    Complete email processing workflow.

    Steps:
    1. Classify intent (QUOTATION, QUOTATION_QUERIES, CASUAL)
    2. If QUOTATION: Extract quotation data with benchmark matching
    3. Return complete results

    This endpoint integrates both intent classification and
    quotation extraction in a single LangGraph workflow.
    """
    try:
        # Fetch benchmarks from database
        benchmarks = await _fetch_benchmarks(db)

        # Execute complete workflow
        workflow = CompleteEmailWorkflow()
        result = await workflow.execute(
            email_content=email_content,
            subject=subject,
            sender=sender,
            attachments=attachments,
            benchmarks=benchmarks,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Email processing failed: {str(e)}",
        )


async def _fetch_benchmarks(db: Session) -> list[dict[str, Any]]:
    """
    Fetch benchmark items from database.

    Args:
        db: Database session

    Returns:
        List of benchmark items as dictionaries
    """
    from app.models.benchmarks import (
        BenchmarkCement,
        BenchmarkGravel,
        BenchmarkSand,
        BenchmarkTile,
    )

    benchmarks = []

    # Fetch cement benchmarks
    cement_items = db.query(BenchmarkCement).all()
    for item in cement_items:
        benchmarks.append(
            {
                "id": item.id,
                "name": item.name,
                "category": "cement",
                "quality_standard": item.quality_standard,
                "unit": item.unit,
                "notes": item.notes,
            }
        )

    # Fetch sand benchmarks
    sand_items = db.query(BenchmarkSand).all()
    for item in sand_items:
        benchmarks.append(
            {
                "id": item.id,
                "name": item.name,
                "category": "sand",
                "quality_standard": item.quality_standard,
                "unit": item.unit,
                "notes": item.notes,
            }
        )

    # Fetch gravel benchmarks
    gravel_items = db.query(BenchmarkGravel).all()
    for item in gravel_items:
        benchmarks.append(
            {
                "id": item.id,
                "name": item.name,
                "category": "gravel",
                "quality_standard": item.quality_standard,
                "unit": item.unit,
                "notes": item.notes,
            }
        )

    # Fetch tile benchmarks
    tile_items = db.query(BenchmarkTile).all()
    for item in tile_items:
        benchmarks.append(
            {
                "id": item.id,
                "name": item.name,
                "category": "tile",
                "quality_standard": item.quality_standard,
                "unit": item.unit,
                "notes": item.notes,
            }
        )

    return benchmarks
