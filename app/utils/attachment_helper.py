"""
Helper utilities for managing email attachments and S3 storage.
"""

import logging
from typing import List, Dict, Optional, Any
from app.utils.storage_service import storage_service

logger = logging.getLogger(__name__)


def is_excel_file(filename: str) -> bool:
    """Check if a file is an Excel file."""
    return filename.lower().endswith(('.xlsx', '.xls'))


def is_pdf_file(filename: str) -> bool:
    """Check if a file is a PDF file."""
    return filename.lower().endswith('.pdf')


def is_document_file(filename: str) -> bool:
    """Check if a file is a document (Excel, PDF, Word, etc.)."""
    doc_extensions = ('.xlsx', '.xls', '.pdf', '.doc', '.docx', '.csv')
    return filename.lower().endswith(doc_extensions)


def get_attachment_summary(attachments: List[Dict]) -> Dict[str, Any]:
    """
    Generate a summary of attachments.
    
    Args:
        attachments: List of attachment dictionaries
        
    Returns:
        Summary with counts and types
    """
    summary = {
        "total": len(attachments),
        "excel_files": 0,
        "pdf_files": 0,
        "other_files": 0,
        "total_size": 0,
        "filenames": []
    }
    
    for att in attachments:
        filename = att.get('filename', 'unknown')
        size = att.get('size', 0)
        
        summary['filenames'].append(filename)
        summary['total_size'] += size
        
        if is_excel_file(filename):
            summary['excel_files'] += 1
        elif is_pdf_file(filename):
            summary['pdf_files'] += 1
        else:
            summary['other_files'] += 1
    
    return summary


def process_attachments_for_quotation(
    attachments: List[Dict],
    mail_id: int,
    user_id: int
) -> Dict[str, Any]:
    """
    Process all attachments for a quotation email.
    
    Args:
        attachments: List of attachment dictionaries
        mail_id: Email ID
        user_id: User ID
        
    Returns:
        Dictionary with S3 URLs and extracted data
    """
    result = {
        "s3_urls": [],
        "attachment_data": {},
        "summary": get_attachment_summary(attachments)
    }
    
    if not storage_service.is_enabled():
        logger.warning("S3 storage not enabled, skipping attachment processing")
        return result
    
    for attachment in attachments:
        filename = attachment.get('filename', 'unknown')
        
        try:
            # Upload to S3
            s3_url = storage_service.upload_attachment(
                attachment=attachment,
                mail_id=mail_id,
                user_id=user_id
            )
            
            if s3_url:
                result['s3_urls'].append(s3_url)
                
                # Extract Excel data if applicable
                if is_excel_file(filename):
                    excel_data = storage_service.extract_excel_data(
                        file_data=attachment.get('data'),
                        filename=filename
                    )
                    
                    if excel_data:
                        result['attachment_data'][filename] = {
                            "type": "excel",
                            "s3_url": s3_url,
                            "extracted_data": excel_data
                        }
                        logger.info(f"Extracted Excel data from {filename}")
                else:
                    # Store metadata for other files
                    result['attachment_data'][filename] = {
                        "type": attachment.get('content_type', 'unknown'),
                        "s3_url": s3_url,
                        "size": attachment.get('size', 0)
                    }
        
        except Exception as e:
            logger.error(f"Error processing attachment {filename}: {e}")
    
    return result


def format_excel_data_for_analysis(excel_data: Dict[str, Any]) -> str:
    """
    Format extracted Excel data into a readable string for AI analysis.
    
    Args:
        excel_data: Extracted Excel data dictionary
        
    Returns:
        Formatted string describing the Excel content
    """
    if not excel_data:
        return "No Excel data available"
    
    lines = []
    lines.append(f"Excel file contains {excel_data.get('row_count', 0)} total rows across {len(excel_data.get('sheets', []))} sheets")
    
    for sheet_name in excel_data.get('sheets', []):
        sheet_info = excel_data.get('column_info', {}).get(sheet_name, {})
        columns = sheet_info.get('columns', [])
        row_count = sheet_info.get('row_count', 0)
        
        lines.append(f"\nSheet '{sheet_name}' ({row_count} rows):")
        lines.append(f"  Columns: {', '.join(columns)}")
        
        # Add sample data if available
        sheet_data = excel_data.get('data', {}).get(sheet_name, {})
        sample_rows = sheet_data.get('sample_rows', [])
        if sample_rows:
            lines.append(f"  Sample data (first row): {sample_rows[0]}")
        
        # Add numeric summary if available
        summary = sheet_data.get('summary', {})
        numeric_summary = summary.get('numeric_summary', {})
        if numeric_summary:
            lines.append("  Numeric columns:")
            for col, stats in list(numeric_summary.items())[:3]:  # Limit to 3 columns
                lines.append(f"    {col}: min={stats.get('min')}, max={stats.get('max')}, avg={stats.get('mean'):.2f}")
    
    return "\n".join(lines)


def get_s3_urls_from_email(email_record) -> List[str]:
    """
    Extract S3 URLs from an email record.
    
    Args:
        email_record: Email database record
        
    Returns:
        List of S3 URLs
    """
    if not email_record.attachments_url:
        return []
    
    urls = email_record.attachments_url.split(',')
    return [url.strip() for url in urls if url.strip()]


def download_attachment_from_email(email_record, filename: str) -> Optional[bytes]:
    """
    Download a specific attachment from an email record.
    
    Args:
        email_record: Email database record
        filename: Name of the file to download
        
    Returns:
        File data as bytes, or None if not found
    """
    urls = get_s3_urls_from_email(email_record)
    
    for url in urls:
        if filename in url:
            return storage_service.download_file_by_url(url)
    
    logger.warning(f"Attachment {filename} not found in email {email_record.mail_id}")
    return None


def get_attachment_metadata_from_summary(email_record) -> Dict[str, Any]:
    """
    Extract attachment metadata from email summary JSON.
    
    Args:
        email_record: Email database record
        
    Returns:
        Dictionary with attachment details
    """
    import json
    
    if not email_record.summary_json:
        return {}
    
    try:
        summary = json.loads(email_record.summary_json)
        return summary.get('attachment_details', {})
    except Exception as e:
        logger.error(f"Error parsing summary JSON: {e}")
        return {}


def format_attachment_list_for_display(attachments: List[Dict]) -> str:
    """
    Format attachment list for user-friendly display.
    
    Args:
        attachments: List of attachment dictionaries
        
    Returns:
        Formatted string
    """
    if not attachments:
        return "No attachments"
    
    lines = []
    for idx, att in enumerate(attachments, 1):
        filename = att.get('filename', 'Unknown')
        size = att.get('size', 0)
        size_kb = size / 1024
        
        file_type = "📊 Excel" if is_excel_file(filename) else \
                   "📄 PDF" if is_pdf_file(filename) else \
                   "📎 File"
        
        lines.append(f"{idx}. {file_type} {filename} ({size_kb:.1f} KB)")
    
    return "\n".join(lines)
