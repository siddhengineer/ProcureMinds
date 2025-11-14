import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize Gemini client
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    logger.info(f"Gemini API key loaded: {gemini_key[:10]}...")
    genai.configure(api_key=gemini_key)
else:
    logger.error("GEMINI_API_KEY not found in environment variables")


def generate_rfq_content(rfq_data: dict) -> str:
    """
    Generate RFQ email content using Gemini.
    
    Args:
        rfq_data: Dictionary containing RFQ details
        
    Returns:
        Generated RFQ email content
    """
    try:
        prompt = f"""Generate a professional RFQ (Request for Quotation) email based on the following details:

{rfq_data}

The email should be formal, clear, and include all necessary details for the vendor to provide an accurate quote."""

        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        full_prompt = f"""You are a professional procurement specialist writing RFQ emails. Write clear, formal, and detailed RFQ emails.

{prompt}"""
        
        response = model.generate_content(full_prompt)
        content = response.text.strip()
        logger.info("RFQ content generated successfully using Gemini")
        return content
        
    except Exception as e:
        logger.error(f"Error generating RFQ content: {e}")
        raise


def send_email(
    to_email: str,
    subject: str,
    body: str,
    attachments: Optional[List[str]] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None
) -> bool:
    """
    Send email via SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body content
        attachments: List of file paths to attach
        cc: List of CC email addresses
        bcc: List of BCC email addresses
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Get SMTP credentials from environment
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_email = os.getenv("SMTP_EMAIL")
        smtp_password = os.getenv("SMTP_PASSWORD")
        
        if not all([smtp_server, smtp_email, smtp_password]):
            logger.error("Missing SMTP credentials in environment variables")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if cc:
            msg['Cc'] = ', '.join(cc)
        if bcc:
            msg['Bcc'] = ', '.join(bcc)
        
        # Attach body
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach files
        if attachments:
            for file_path in attachments:
                try:
                    with open(file_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename={os.path.basename(file_path)}'
                        )
                        msg.attach(part)
                except Exception as e:
                    logger.error(f"Error attaching file {file_path}: {e}")
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            
            # Prepare recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            server.sendmail(smtp_email, recipients, msg.as_string())
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False


def send_rfq_email(
    to_email: str,
    rfq_data: dict,
    attachments: Optional[List[str]] = None,
    cc: Optional[List[str]] = None
) -> dict:
    """
    Generate and send RFQ email.
    
    Args:
        to_email: Vendor email address
        rfq_data: Dictionary containing RFQ details
        attachments: List of file paths to attach
        cc: List of CC email addresses
        
    Returns:
        Dictionary with status and details
    """
    try:
        # Generate RFQ content
        logger.info(f"Generating RFQ for {to_email}")
        rfq_content = generate_rfq_content(rfq_data)
        
        # Extract subject from rfq_data or use default
        subject = rfq_data.get('subject', 'Request for Quotation')
        
        # Send email
        success = send_email(
            to_email=to_email,
            subject=subject,
            body=rfq_content,
            attachments=attachments,
            cc=cc
        )
        
        return {
            "success": success,
            "to_email": to_email,
            "subject": subject,
            "rfq_content": rfq_content,
            "message": "RFQ sent successfully" if success else "Failed to send RFQ"
        }
        
    except Exception as e:
        logger.error(f"Error in send_rfq_email: {e}")
        return {
            "success": False,
            "to_email": to_email,
            "error": str(e),
            "message": "Failed to generate or send RFQ"
        }
