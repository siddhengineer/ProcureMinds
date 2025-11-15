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

def classify_email_intent(
    message: str,
    subject: str = "",
    attachments: list = None,
    sender: str = ""
) -> Literal["Quotation", "Casual"]:
    """
    Classify email message intent using OpenAI with enhanced context.
    
    Args:
        message: The email body text to classify
        subject: Email subject line
        attachments: List of attachment filenames
        sender: Sender email address
        
    Returns:
        Either "Quotation" or "Casual"
    """
    try:
        # Prepare attachment info
        attachment_info = ""
        if attachments:
            attachment_names = [att.get("filename", "") if isinstance(att, dict) else str(att) for att in attachments]
            attachment_info = f"\n\nAttachments: {', '.join(attachment_names)}"
        
        # Prepare full context
        email_context = f"""Subject: {subject}
From: {sender}
{attachment_info}

Body:
{message}"""
        
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert email classifier for construction procurement systems. 
Classify emails into two categories based on their intent and content:

1. "Quotation" - Emails that are vendor responses to procurement requests, including:
   - Price quotes or quotations for materials/services
   - Vendor proposals with pricing information
   - RFQ (Request for Quotation) responses
   - Pricing inquiries with cost details
   - Product/service specifications with pricing
   - Procurement-related communications with commercial terms
   - Emails with attachments like Excel price lists, PDF quotations, or specification sheets
   - Vendor responses discussing availability, delivery, and pricing
   - Construction material quotes (cement, steel, aggregates, etc.)
   - Equipment rental or purchase quotations
   - Subcontractor bids and proposals

Key indicators of Quotation emails:
- Contains pricing information or cost discussions
- Includes material specifications with quantities
- Has attachments like .xlsx, .pdf with pricing/specs
- Discusses delivery terms, payment terms, or commercial conditions
- References project requirements or RFQ numbers
- Vendor responding to a procurement inquiry

2. "Casual" - All other emails including:
   - General inquiries without pricing
   - Casual conversations
   - Non-business emails
   - Newsletters and marketing emails
   - Notifications and alerts
   - Meeting invitations
   - Status updates without commercial terms
   - Internal communications
   
Respond with ONLY one word: either "Quotation" or "Casual"."""
                },
                {
                    "role": "user",
                    "content": f"Classify this email:\n\n{email_context}"
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
        
        logger.info(f"Email classified as: {intent} (subject: {subject[:50]}...)")
        return intent
        
    except Exception as e:
        logger.error(f"Error classifying email intent: {e}")
        # Default to Casual on error
        return "Casual"
