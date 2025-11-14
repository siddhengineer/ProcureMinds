import os
import logging
from typing import Literal
from dotenv import load_dotenv
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

load_dotenv()
# Initialize OpenAI client with OpenRouter
client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

def classify_email_intent(message: str) -> Literal["Quotation", "Casual"]:
    """
    Classify email message intent using OpenAI.
    
    Args:
        message: The email body text to classify
        
    Returns:
        Either "Quotation" or "Casual"
    """
    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an email classifier. Classify emails into two categories:
                    
1. "Quotation" - Emails related to:
   - Price quotes or quotations
   - Purchase requests
   - Vendor proposals
   - RFQ (Request for Quotation)
   - Pricing inquiries
   - Product/service cost discussions
   - Procurement-related communications

2. "Casual" - All other emails including:
   - General inquiries
   - Casual conversations
   - Non-business emails
   - Newsletters
   - Notifications
   
Respond with ONLY one word: either "Quotation" or "Casual"."""
                },
                {
                    "role": "user",
                    "content": f"Classify this email:\n\n{message}"
                }
            ],
            temperature=0,
            max_tokens=10
        )
        
        intent = response.choices[0].message.content.strip()
        
        # Validate response
        if intent not in ["Quotation", "Casual"]:
            logger.warning(f"Unexpected intent classification: {intent}, defaulting to Casual")
            return "Casual"
        
        logger.info(f"Email classified as: {intent}")
        return intent
        
    except Exception as e:
        logger.error(f"Error classifying email intent: {e}")
        # Default to Casual on error
        return "Casual"
