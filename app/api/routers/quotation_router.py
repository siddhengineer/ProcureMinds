from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.langgraph.langgraph_manager import email_workflow
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class EmailAnalysisRequest(BaseModel):
    """Request model for email analysis."""
    subject: str
    sender: str
    body: str
    user_id: int
    project_id: int


class EmailAnalysisResponse(BaseModel):
    """Response model for email analysis."""
    intent: str
    subject: str
    sender: str
    user_id: int
    project_id: int
    mail_id: int | None


@router.post("/analyze", response_model=EmailAnalysisResponse)
async def analyze_quotation(
    request: EmailAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze an email and classify its intent.
    If classified as Quotation, saves to database.
    
    Args:
        request: Email data to analyze
        db: Database session
        
    Returns:
        Analysis result with intent and database info
    """
    try:
        # Prepare email data
        email_data = {
            "id": "manual",
            "subject": request.subject,
            "from": request.sender,
            "body": request.body,
            "attachments": []
        }
        
        # Process through workflow
        result = await email_workflow.process_email(
            email_data=email_data,
            user_id=request.user_id,
            project_id=request.project_id,
            db=db
        )
        
        logger.info(f"Email analyzed - Intent: {result['intent']}")
        
        return EmailAnalysisResponse(
            intent=result['intent'],
            subject=result['subject'],
            sender=result['sender'],
            user_id=result['user_id'],
            project_id=result['project_id'],
            mail_id=result.get('mail_id')
        )
        
    except Exception as e:
        logger.error(f"Error analyzing email: {e}")
        raise HTTPException(status_code=500, detail=str(e))
