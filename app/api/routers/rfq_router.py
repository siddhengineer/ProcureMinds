from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from app.outbound.smtp_mail import send_rfq_email
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class RFQRequest(BaseModel):
    """Request model for sending RFQ."""
    to_email: EmailStr
    rfq_data: dict
    attachments: Optional[List[str]] = None
    cc: Optional[List[str]] = None


class RFQResponse(BaseModel):
    """Response model for RFQ sending."""
    success: bool
    to_email: str
    subject: str
    message: str
    rfq_content: Optional[str] = None


@router.post("/send", response_model=RFQResponse)
async def send_rfq(request: RFQRequest):
    """
    Generate and send RFQ email to vendor.
    
    Args:
        request: RFQ request with vendor email and RFQ details
        
    Returns:
        Status of RFQ sending
    """
    try:
        result = send_rfq_email(
            to_email=request.to_email,
            rfq_data=request.rfq_data,
            attachments=request.attachments,
            cc=request.cc
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('message', 'Failed to send RFQ'))
        
        return RFQResponse(
            success=result['success'],
            to_email=result['to_email'],
            subject=result['subject'],
            message=result['message'],
            rfq_content=result.get('rfq_content')
        )
        
    except Exception as e:
        logger.error(f"Error in send_rfq endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
