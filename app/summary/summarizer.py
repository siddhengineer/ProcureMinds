import json
import logging
from typing import Dict, List
from sqlalchemy.orm import Session
from openai import OpenAI

from app.core.config import settings
from app.summary.summary_queries import get_top_vendors_for_analysis

logger = logging.getLogger(__name__)

# Initialize OpenAI client with OpenRouter
client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


def analyze_best_vendor(
    db: Session,
    project_id: int,
    top_percentage: float = 0.20
) -> Dict:
    """
    Analyze top vendors using LLM to determine the best pick.
    
    Args:
        db: Database session
        project_id: The project ID
        top_percentage: Percentage of top vendors to analyze
    
    Returns:
        Dictionary with best vendor recommendation and reasoning
    """
    # Get top vendors data from database
    vendors_data = get_top_vendors_for_analysis(db, project_id, top_percentage)
    
    if not vendors_data:
        return {
            "status": "error",
            "message": "No vendors found for this project"
        }
    
    # Prepare prompt for LLM
    prompt = _build_analysis_prompt(vendors_data)
    
    # Call LLM
    llm_analysis = _call_llm(prompt)
    
    return {
        "status": "success",
        "project_id": project_id,
        "total_analyzed": len(vendors_data),
        "vendors_data": vendors_data,
        "llm_analysis": llm_analysis
    }


def _build_analysis_prompt(vendors_data: List[Dict]) -> str:
    """Build the prompt for LLM analysis."""
    
    vendors_text = ""
    for idx, vendor in enumerate(vendors_data, 1):
        vendors_text += f"\n\n--- Vendor {idx} ---\n"
        vendors_text += f"Email: {vendor['vendor_email']}\n"
        vendors_text += f"Overall Score: {vendor['overall_score']}\n"
        vendors_text += f"Summary: {json.dumps(vendor['summary'], indent=2)}\n"
    
    prompt = f"""You are analyzing vendor proposals for a procurement project. 
Below are the top {len(vendors_data)} vendors sorted by their overall scores.

{vendors_text}

Based on the scores and summaries provided, analyze and provide:

1. **Best Vendor Recommendation**: Which vendor should be selected as the primary choice and why?
2. **Backup Vendor**: Which vendor should be considered as a backup option?
3. **Key Reasons**: Provide 3-5 specific reasons for your recommendation based on:
   - Overall score and performance
   - Summary details (pricing, delivery, quality, compliance, etc.)
   - Competitive advantages over other vendors
4. **Risk Assessment**: Any potential concerns or risks with the recommended vendor?

Provide your analysis in a clear, structured format with specific details from the summaries.
"""
    
    return prompt


def _call_llm(prompt: str) -> str:
    """
    Call OpenRouter LLM with the analysis prompt.
    
    Args:
        prompt: The analysis prompt
        
    Returns:
        LLM analysis response
    """
    try:
        response = client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert procurement analyst specializing in vendor evaluation and selection for construction projects.
Your role is to analyze vendor quotations and provide clear, actionable recommendations based on:
- Overall scores and performance metrics
- Pricing competitiveness
- Delivery timelines and reliability
- Quality and compliance standards
- Risk factors and mitigation strategies

Provide structured, professional analysis with specific evidence from the vendor data."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        analysis = response.choices[0].message.content.strip()
        logger.info(f"LLM analysis completed successfully")
        return analysis
        
    except Exception as e:
        logger.error(f"Error calling LLM for vendor analysis: {e}")
        return f"Error generating analysis: {str(e)}"
