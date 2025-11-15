from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from sqlalchemy.orm import Session
from app.outbound.smtp_mail import send_rfq_email
from app.core.database import get_db
from app.models.rfqs import RFQ
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class RFQRequest(BaseModel):
    """Request model for sending RFQ."""
    to_email: EmailStr
    rfq_data: dict
    user_id: int
    project_id: Optional[int] = None
    vendor_id: Optional[int] = None
    boq_id: Optional[int] = None
    attachments: Optional[List[str]] = None
    cc: Optional[List[str]] = None


class RFQResponse(BaseModel):
    """Response model for RFQ sending."""
    success: bool
    rfq_id: Optional[int] = None
    to_email: str
    subject: str
    message: str
    status: str
    rfq_content: Optional[str] = None


@router.post("/send", response_model=RFQResponse)
async def send_rfq(request: RFQRequest, db: Session = Depends(get_db)):
    """
    Generate and send RFQ email to vendor and store in database.
    
    Args:
        request: RFQ request with vendor email and RFQ details
        db: Database session
        
    Returns:
        Status of RFQ sending with database record ID
    """
    try:
        # Generate and send email
        result = send_rfq_email(
            to_email=request.to_email,
            rfq_data=request.rfq_data,
            attachments=request.attachments,
            cc=request.cc
        )
        
        # Determine status based on email send result
        status = "sent" if result['success'] else "pending"
        
        # Create RFQ record in database
        rfq = RFQ(
            user_id=request.user_id,
            project_id=request.project_id,
            vendor_id=request.vendor_id,
            boq_id=request.boq_id,
            outgoing_mail=result.get('rfq_content'),
            subject=result.get('subject'),
            status=status,
            reply_received=False
        )
        
        db.add(rfq)
        db.commit()
        db.refresh(rfq)
        
        logger.info(f"RFQ record created with ID: {rfq.rfq_id}, status: {status}")
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('message', 'Failed to send RFQ'))
        
        return RFQResponse(
            success=result['success'],
            rfq_id=rfq.rfq_id,
            to_email=result['to_email'],
            subject=result['subject'],
            message=result['message'],
            status=status,
            rfq_content=result.get('rfq_content')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in send_rfq endpoint: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
