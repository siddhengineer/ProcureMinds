import json
from typing import List
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
