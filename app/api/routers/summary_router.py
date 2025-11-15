from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.database import get_db
from app.summary.summarizer import analyze_best_vendor

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analyze-vendors/{project_id}")
async def analyze_project_vendors(
    project_id: int,
    top_percentage: Optional[float] = 0.20,
    db: Session = Depends(get_db)
):
    """
    Analyze top vendors for a project and get LLM recommendation.
    
    Args:
        project_id: The project ID to analyze vendors for
        top_percentage: Percentage of top vendors to analyze (default 20%)
        
    Returns:
        Analysis with best vendor recommendation, reasoning, and all vendor data
    """
    try:
        logger.info(f"Starting vendor analysis for project {project_id}")
        
        # Validate percentage
        if not 0 < top_percentage <= 1:
            raise HTTPException(
                status_code=400,
                detail="top_percentage must be between 0 and 1"
            )
        
        # Analyze vendors
        result = analyze_best_vendor(
            db=db,
            project_id=project_id,
            top_percentage=top_percentage
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=404,
                detail=result["message"]
            )
        
        logger.info(
            f"Analysis complete for project {project_id}: "
            f"{result['total_analyzed']} vendors analyzed"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing vendors for project {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze vendors: {str(e)}"
        )
