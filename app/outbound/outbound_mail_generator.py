from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from openai import OpenAI
import os
import logging

from app.models.vendors import Vendor
from app.models.rfqs import RFQ
from app.summary.benchmark_queries import get_project_benchmarks_json
from app.outbound.smtp_mail import send_email

logger = logging.getLogger(__name__)

# Material ID to category name mapping
MATERIAL_ID_TO_CATEGORY = {
    1: "sand",
    2: "tile",
    3: "steel",
    4: "cement",
    5: "granular"
}


def get_vendor_relevant_benchmarks(
    vendor: Vendor,
    all_benchmarks: List[Dict]
) -> List[Dict]:
    """
    Filter benchmarks based on vendor's material categories.
    
    Args:
        vendor: Vendor object with material IDs
        all_benchmarks: List of all benchmark dictionaries
        
    Returns:
        List of benchmarks matching vendor's materials
    """
    if not vendor.material:
        return []
    
    # Convert vendor material IDs to category names
    vendor_categories = {
        MATERIAL_ID_TO_CATEGORY[mat_id] 
        for mat_id in vendor.material 
        if mat_id in MATERIAL_ID_TO_CATEGORY
    }
    
    # Filter benchmarks by matching categories
    relevant_benchmarks = [
        benchmark for benchmark in all_benchmarks
        if benchmark.get("category") in vendor_categories
    ]
    
    return relevant_benchmarks


def generate_rfq_email_with_openrouter(
    vendor: Vendor,
    benchmarks: List[Dict],
    project_name: str,
    additional_context: Optional[str] = None
) -> str:
    """
    Generate a professional RFQ email using OpenRouter API.
    
    Args:
        vendor: Vendor object with contact details
        benchmarks: List of relevant benchmark dictionaries
        project_name: Name of the project
        additional_context: Optional additional context for the email
        
    Returns:
        Generated email content as string
    """
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Prepare benchmark details for the prompt
    benchmark_details = []
    for bm in benchmarks:
        benchmark_details.append(
            f"- {bm['description']}"
            + (f" (Required by: {bm['required_by']})" if bm['required_by'] else "")
        )
    
    benchmark_text = "\n".join(benchmark_details)
    
    # Create the prompt
    prompt = f"""Generate a professional Request for Quotation (RFQ) email for the following:

Vendor Details:
- Name: {vendor.name}
- Email: {vendor.email}
- Location: {vendor.location}

Project: {project_name}

Materials Required:
{benchmark_text}

{f"Additional Context: {additional_context}" if additional_context else ""}

Please generate a professional, concise RFQ email that:
1. Addresses the vendor professionally
2. Introduces the project briefly
3. Lists the materials required with specifications
4. Requests pricing and delivery timelines
5. Includes a polite closing with contact information
6. Maintains a formal business tone

Format the email with proper structure including subject line, greeting, body, and signature."""

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a professional procurement specialist writing RFQ emails for construction projects."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content


def generate_and_send_rfq_for_vendors(
    db: Session,
    vendor_ids: List[int],
    project_id: int,
    project_name: str,
    user_id: int,
    boq_id: Optional[int] = None,
    additional_context: Optional[str] = None,
    send_emails: bool = True
) -> List[Dict]:
    """
    Generate and optionally send RFQ emails for multiple vendors.
    
    Args:
        db: Database session
        vendor_ids: List of vendor IDs
        project_id: ID of the project
        project_name: Name of the project
        user_id: ID of the user
        boq_id: Optional BOQ ID
        additional_context: Optional additional context
        send_emails: Whether to actually send emails via SMTP
        
    Returns:
        List of dictionaries with vendor info, email content, and send status
    """
    # Fetch all benchmarks once
    all_benchmarks = get_project_benchmarks_json(project_id, db)
    
    results = []
    
    for vendor_id in vendor_ids:
        try:
            # Fetch vendor
            vendor = db.query(Vendor).filter(
                Vendor.vendor_id == vendor_id,
                Vendor.user_id == user_id
            ).first()
            
            if not vendor:
                results.append({
                    "vendor_id": vendor_id,
                    "success": False,
                    "message": f"Vendor {vendor_id} not found"
                })
                continue
            
            # Filter benchmarks relevant to vendor's materials
            relevant_benchmarks = get_vendor_relevant_benchmarks(vendor, all_benchmarks)
            
            if not relevant_benchmarks:
                results.append({
                    "vendor_id": vendor_id,
                    "vendor_name": vendor.name,
                    "vendor_email": vendor.email,
                    "success": False,
                    "message": "No relevant materials found for this vendor"
                })
                continue
            
            # Generate email using OpenRouter
            email_content = generate_rfq_email_with_openrouter(
                vendor=vendor,
                benchmarks=relevant_benchmarks,
                project_name=project_name,
                additional_context=additional_context
            )
            
            # Extract subject from email content (first line or default)
            subject = f"RFQ - {project_name}"
            if email_content and email_content.startswith("Subject:"):
                lines = email_content.split("\n", 1)
                subject = lines[0].replace("Subject:", "").strip()
                email_content = lines[1].strip() if len(lines) > 1 else email_content
            
            # Create RFQ record with status "pending"
            rfq = RFQ(
                user_id=user_id,
                vendor_id=vendor_id,
                project_id=project_id,
                boq_id=boq_id,
                outgoing_mail=email_content,
                subject=subject,
                status="pending"
            )
            db.add(rfq)
            db.flush()  # Get the RFQ ID
            
            email_sent = False
            send_error = None
            
            # Send email if requested
            if send_emails:
                try:
                    email_sent = send_email(
                        to_email=vendor.email,
                        subject=subject,
                        body=email_content
                    )
                    
                    if email_sent:
                        rfq.status = "sent"
                        logger.info(f"RFQ email sent to {vendor.email}")
                    else:
                        send_error = "Failed to send email"
                        logger.error(f"Failed to send RFQ email to {vendor.email}")
                        
                except Exception as e:
                    send_error = str(e)
                    logger.error(f"Error sending email to {vendor.email}: {e}")
            
            db.commit()
            db.refresh(rfq)
            
            results.append({
                "rfq_id": rfq.rfq_id,
                "vendor_id": vendor_id,
                "vendor_name": vendor.name,
                "vendor_email": vendor.email,
                "relevant_materials": [bm["category"] for bm in relevant_benchmarks],
                "benchmark_count": len(relevant_benchmarks),
                "email_content": email_content,
                "subject": subject,
                "status": rfq.status,
                "email_sent": email_sent,
                "success": True,
                "message": "RFQ sent successfully" if email_sent else "RFQ created but not sent",
                "error": send_error
            })
            
        except Exception as e:
            logger.error(f"Error processing vendor {vendor_id}: {e}")
            results.append({
                "vendor_id": vendor_id,
                "success": False,
                "message": f"Error: {str(e)}"
            })
    
    return results


def generate_rfq_for_all_vendors(
    db: Session,
    project_id: int,
    project_name: str,
    user_id: int,
    additional_context: Optional[str] = None
) -> List[Dict]:
    """
    Generate RFQ emails for all vendors of a user based on project benchmarks.
    
    Args:
        db: Database session
        project_id: ID of the project
        project_name: Name of the project
        user_id: ID of the user
        additional_context: Optional additional context
        
    Returns:
        List of dictionaries with vendor info and generated emails
    """
    # Fetch all vendors for the user
    vendors = db.query(Vendor).filter(Vendor.user_id == user_id).all()
    
    if not vendors:
        return []
    
    # Fetch all benchmarks once
    all_benchmarks = get_project_benchmarks_json(project_id, db)
    
    results = []
    for vendor in vendors:
        # Filter benchmarks relevant to this vendor
        relevant_benchmarks = get_vendor_relevant_benchmarks(vendor, all_benchmarks)
        
        if not relevant_benchmarks:
            results.append({
                "vendor_id": vendor.vendor_id,
                "vendor_name": vendor.name,
                "vendor_email": vendor.email,
                "email_content": None,
                "message": "No relevant materials found for this vendor"
            })
            continue
        
        # Generate email
        email_content = generate_rfq_email_with_openrouter(
            vendor=vendor,
            benchmarks=relevant_benchmarks,
            project_name=project_name,
            additional_context=additional_context
        )
        
        results.append({
            "vendor_id": vendor.vendor_id,
            "vendor_name": vendor.name,
            "vendor_email": vendor.email,
            "relevant_materials": [bm["category"] for bm in relevant_benchmarks],
            "benchmark_count": len(relevant_benchmarks),
            "email_content": email_content
        })
    
    return results
