from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.outbound.outbound_mail_generator import generate_and_send_rfq_for_vendors

router = APIRouter(prefix="/rfq-emails", tags=["RFQ Emails"])


class SendRFQRequest(BaseModel):
    vendor_ids: List[int]
    project_id: int
    project_name: str
    user_id: int
    boq_id: Optional[int] = None
    additional_context: Optional[str] = None
    send_emails: bool = True  # Set to False to only generate without sending


class RFQResponse(BaseModel):
    rfq_id: Optional[int] = None
    vendor_id: int
    vendor_name: Optional[str] = None
    vendor_email: Optional[str] = None
    relevant_materials: Optional[List[str]] = None
    benchmark_count: Optional[int] = None
    email_content: Optional[str] = None
    subject: Optional[str] = None
    status: Optional[str] = None
    email_sent: Optional[bool] = None
    success: bool
    message: str
    error: Optional[str] = None


@router.post("/send", response_model=List[RFQResponse])
def send_rfq_emails(
    request: SendRFQRequest,
    db: Session = Depends(get_db)
):
    """
    Generate and send RFQ emails to selected vendors.
    
    This endpoint:
    1. Generates RFQ emails for each vendor based on their materials
    2. Stores RFQ records in the database
    3. Sends emails via SMTP (if send_emails=True)
    4. Updates status to 'sent' or keeps as 'pending'
    
    Args:
        request: Contains vendor_ids, project_id, boq_id, user_id, etc.
        
    Returns:
        List of RFQ responses with status for each vendor
    """
    try:
        results = generate_and_send_rfq_for_vendors(
            db=db,
            vendor_ids=request.vendor_ids,
            project_id=request.project_id,
            project_name=request.project_name,
            user_id=request.user_id,
            boq_id=request.boq_id,
            additional_context=request.additional_context,
            send_emails=request.send_emails
        )
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing RFQ emails: {str(e)}"
        )
