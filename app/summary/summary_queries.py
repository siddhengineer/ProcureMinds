import json
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.emails import Email


def get_top_vendors_for_analysis(
    db: Session,
    project_id: int,
    top_percentage: float = 0.20
) -> List[dict]:
    """
    Query top vendors by project_id sorted by overall_score.
    Returns formatted data ready for LLM analysis.
    
    Args:
        db: Database session
        project_id: The project ID to filter emails
        top_percentage: Percentage of top scores to fetch (default 20%)
    
    Returns:
        List of vendor dictionaries with email, score, and summary
    """
    # Query emails sorted by overall_score descending
    emails = db.query(Email).filter(
        Email.project_id == project_id,
        Email.overall_score.isnot(None)
    ).order_by(desc(Email.overall_score)).all()
    
    if not emails:
        return []
    
    # Calculate top count
    total_count = len(emails)
    top_count = max(1, int(total_count * top_percentage))
    top_emails = emails[:top_count]
    
    # Format data for LLM
    vendors_data = []
    for email in top_emails:
        summary_data = None
        if email.summary_json:
            try:
                summary_data = json.loads(email.summary_json)
            except json.JSONDecodeError:
                summary_data = email.summary_json
        
        vendors_data.append({
            "mail_id": email.mail_id,
            "vendor_email": email.email,
            "overall_score": email.overall_score,
            "summary": summary_data,
            "created_at": email.created_at.isoformat() if email.created_at else None
        })
    
    return vendors_data


def get_emails_by_project_and_user(
    db: Session,
    project_id: int,
    user_id: Optional[int] = None
) -> List[dict]:
    """
    Query all emails by project_id and optionally filter by user_id.
    Returns formatted email details ordered by date (newest first).
    
    Args:
        db: Database session
        project_id: The project ID to filter emails
        user_id: Optional user ID to filter emails (if None, returns all users)
    
    Returns:
        List of email dictionaries with relevant details
    """
    # Build query
    query = db.query(Email).filter(Email.project_id == project_id)
    
    # Add user filter if provided
    if user_id is not None:
        query = query.filter(Email.user_id == user_id)
    
    # Order by created_at descending (newest first)
    emails = query.order_by(desc(Email.created_at)).all()
    
    # Format data
    emails_data = []
    for email in emails:
        summary_data = None
        if email.summary_json:
            try:
                summary_data = json.loads(email.summary_json)
            except json.JSONDecodeError:
                summary_data = email.summary_json
        
        emails_data.append({
            "mail_id": email.mail_id,
            "user_id": email.user_id,
            "project_id": email.project_id,
            "vendor_email": email.email,
            "message": email.message,
            "attachments_url": email.attachments_url,
            "summary": summary_data,
            "overall_score": email.overall_score,
            "created_at": email.created_at.isoformat() if email.created_at else None,
            "updated_at": email.updated_at.isoformat() if email.updated_at else None
        })
    
    return emails_data
