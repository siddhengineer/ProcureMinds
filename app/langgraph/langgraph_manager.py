import asyncio
import logging
import json
from typing import TypedDict, Literal
from datetime import datetime
from langgraph.graph import StateGraph, END
from app.summary.intent_service import classify_email_intent
from app.summary.extraction_service import BenchmarkExtractionService
from app.models.emails import Email
from app.utils.storage_service import storage_service
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EmailState(TypedDict):
    """State for email processing workflow."""
    email_id: str
    subject: str
    sender: str
    body: str
    attachments: list
    intent: str
    user_id: int
    project_id: int
    mail_id: int | None
    saved_files: list
    s3_urls: list
    attachment_data: dict | None
    benchmark_analysis: dict | None
    db: Session


def intent_node(state: EmailState) -> EmailState:
    """
    Classify email intent with enhanced context including attachments.
    
    Args:
        state: Current email state
        
    Returns:
        Updated state with intent classification
    """
    logger.info(f"[INTENT NODE] Processing email: {state['subject']}")
    
    # Classify the email with full context
    intent = classify_email_intent(
        message=state['body'],
        subject=state['subject'],
        attachments=state.get('attachments', []),
        sender=state['sender']
    )
    
    logger.info(f"[INTENT NODE] Classified as: {intent}")
    
    return {
        **state,
        "intent": intent
    }


def attachment_processing_node(state: EmailState) -> EmailState:
    """
    Process attachments: upload to S3 and extract data from Excel files.
    
    Args:
        state: Current email state
        
    Returns:
        Updated state with S3 URLs and extracted attachment data
    """
    logger.info(f"[ATTACHMENT NODE] Processing {len(state.get('attachments', []))} attachments")
    
    s3_urls = []
    attachment_data = {}
    
    # Generate a temporary mail_id for S3 storage (will be updated after DB save)
    temp_mail_id = int(datetime.now().timestamp())
    
    try:
        for idx, attachment in enumerate(state.get('attachments', [])):
            filename = attachment.get('filename', f'attachment_{idx}')
            logger.info(f"[ATTACHMENT NODE] Processing: {filename}")
            
            # Upload to S3
            if storage_service.is_enabled():
                s3_url = storage_service.upload_attachment(
                    attachment=attachment,
                    mail_id=temp_mail_id,
                    user_id=state['user_id']
                )
                
                if s3_url:
                    s3_urls.append(s3_url)
                    logger.info(f"[ATTACHMENT NODE] Uploaded to S3: {s3_url}")
                    
                    # Extract data from Excel files
                    if filename.lower().endswith(('.xlsx', '.xls')):
                        logger.info(f"[ATTACHMENT NODE] Extracting Excel data from: {filename}")
                        excel_data = storage_service.extract_excel_data(
                            file_data=attachment.get('data'),
                            filename=filename
                        )
                        
                        if excel_data:
                            attachment_data[filename] = {
                                "type": "excel",
                                "s3_url": s3_url,
                                "extracted_data": excel_data
                            }
                            logger.info(
                                f"[ATTACHMENT NODE] Extracted {excel_data['row_count']} rows "
                                f"from {len(excel_data['sheets'])} sheets"
                            )
                    else:
                        # Store metadata for non-Excel files
                        attachment_data[filename] = {
                            "type": attachment.get('content_type', 'unknown'),
                            "s3_url": s3_url,
                            "size": attachment.get('size', 0)
                        }
            else:
                logger.warning("[ATTACHMENT NODE] S3 storage not enabled, skipping upload")
        
        logger.info(f"[ATTACHMENT NODE] Processed {len(s3_urls)} attachments successfully")
        
        return {
            **state,
            "s3_urls": s3_urls,
            "attachment_data": attachment_data
        }
        
    except Exception as e:
        logger.error(f"[ATTACHMENT NODE] Error processing attachments: {e}")
        return {
            **state,
            "s3_urls": s3_urls,
            "attachment_data": attachment_data
        }


def benchmark_analysis_node(state: EmailState) -> EmailState:
    """
    Analyze vendor email against project benchmarks with extracted attachment data.
    
    Args:
        state: Current email state
        
    Returns:
        Updated state with benchmark analysis
    """
    logger.info(f"[BENCHMARK NODE] Analyzing email: {state['subject']}")
    
    try:
        # Initialize extraction service
        extraction_service = BenchmarkExtractionService(state['db'])
        
        # Prepare enhanced attachments info with extracted data
        attachments_info = []
        attachment_data = state.get('attachment_data', {})
        
        for att in state.get('attachments', []):
            filename = att.get('filename', 'unknown') if isinstance(att, dict) else str(att)
            
            att_info = {
                "filename": filename,
                "content_type": att.get('content_type', 'application/octet-stream') if isinstance(att, dict) else 'unknown'
            }
            
            # Add extracted data if available
            if filename in attachment_data:
                att_data = attachment_data[filename]
                att_info["s3_url"] = att_data.get("s3_url")
                
                # Add Excel data summary if available
                if att_data.get("type") == "excel" and att_data.get("extracted_data"):
                    excel_data = att_data["extracted_data"]
                    att_info["excel_summary"] = {
                        "sheets": excel_data.get("sheets", []),
                        "total_rows": excel_data.get("row_count", 0),
                        "columns": excel_data.get("column_info", {}),
                        "data_preview": excel_data.get("data", {})
                    }
            
            attachments_info.append(att_info)
        
        # Analyze email against benchmarks
        analysis = extraction_service.analyze_vendor_email(
            project_id=state['project_id'],
            email_subject=state['subject'],
            email_body=state['body'],
            sender_email=state['sender'],
            attachments_info=attachments_info
        )
        
        logger.info(
            f"[BENCHMARK NODE] Analysis complete. "
            f"Overall score: {analysis.get('overall_score', 0)}, "
            f"Coverage: {analysis.get('vendor_coverage', 0)}%"
        )
        
        return {
            **state,
            "benchmark_analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"[BENCHMARK NODE] Error analyzing email: {e}")
        return {
            **state,
            "benchmark_analysis": {
                "error": str(e),
                "overall_score": 0
            }
        }


def should_analyze_benchmarks(state: EmailState) -> Literal["analyze", "skip"]:
    """
    Determine if email should be analyzed against benchmarks.
    
    Args:
        state: Current email state
        
    Returns:
        "analyze" if email is a quotation, "skip" otherwise
    """
    if state.get('intent') == "Quotation":
        return "analyze"
    return "skip"


class EmailWorkflow:
    """LangGraph workflow for processing emails."""
    
    def __init__(self):
        """Initialize the email processing workflow."""
        self.workflow = StateGraph(EmailState)
        
        # Add nodes
        self.workflow.add_node("intent", intent_node)
        self.workflow.add_node("attachment_processing", attachment_processing_node)
        self.workflow.add_node("benchmark_analysis", benchmark_analysis_node)
        
        # Set entry point
        self.workflow.set_entry_point("intent")
        
        # Add conditional edges from intent
        self.workflow.add_conditional_edges(
            "intent",
            should_analyze_benchmarks,
            {
                "analyze": "attachment_processing",
                "skip": END
            }
        )
        
        # Add edge from attachment processing to benchmark analysis
        self.workflow.add_edge("attachment_processing", "benchmark_analysis")
        
        # Add edge from benchmark analysis to end
        self.workflow.add_edge("benchmark_analysis", END)
        
        # Compile the graph
        self.app = self.workflow.compile()
        
        logger.info("Email workflow initialized with attachment processing and benchmark analysis")
    
    async def process_email(
        self,
        email_data: dict,
        user_id: int,
        project_id: int,
        db: Session
    ) -> dict:
        """
        Process a single email through the workflow.
        
        Args:
            email_data: Email data from IMAP service
            user_id: User ID
            project_id: Project ID
            db: Database session
            
        Returns:
            Processing result with intent, benchmark analysis, and database info
        """
        # Initialize state
        initial_state: EmailState = {
            "email_id": email_data['id'],
            "subject": email_data['subject'],
            "sender": email_data['from'],
            "body": email_data['body'],
            "attachments": email_data['attachments'],
            "intent": "",
            "user_id": user_id,
            "project_id": project_id,
            "mail_id": None,
            "saved_files": [],
            "s3_urls": [],
            "attachment_data": None,
            "benchmark_analysis": None,
            "db": db
        }
        
        # Run workflow
        result = await self.app.ainvoke(initial_state)
        
        # If quotation, save to database with benchmark analysis
        if result['intent'] == "Quotation":
            try:
                # Use S3 URLs if available, otherwise fall back to local saved files
                attachments_url = None
                if result.get('s3_urls'):
                    attachments_url = ",".join(result['s3_urls'])
                    logger.info(f"[WORKFLOW] Using S3 URLs for attachments: {len(result['s3_urls'])} files")
                elif result.get('saved_files'):
                    attachments_url = ",".join(result['saved_files'])
                    logger.info(f"[WORKFLOW] Using local file paths for attachments: {len(result['saved_files'])} files")
                
                # Prepare summary JSON with attachment data
                summary_json = None
                overall_score = None
                if result.get('benchmark_analysis'):
                    # Include attachment data in summary
                    summary_data = result['benchmark_analysis'].copy()
                    if result.get('attachment_data'):
                        summary_data['attachment_details'] = result['attachment_data']
                    
                    summary_json = json.dumps(summary_data)
                    overall_score = result['benchmark_analysis'].get('overall_score')
                
                # Create email record
                email_record = Email(
                    user_id=user_id,
                    project_id=project_id,
                    email=result['sender'],
                    message=result['body'],
                    attachments_url=attachments_url,
                    summary_json=summary_json,
                    overall_score=overall_score
                )
                db.add(email_record)
                db.commit()
                db.refresh(email_record)
                
                result['mail_id'] = email_record.mail_id
                
                logger.info(
                    f"[WORKFLOW] Saved quotation to database (ID: {email_record.mail_id}, "
                    f"Score: {overall_score}, Attachments: {len(result.get('s3_urls', []))} in S3)"
                )
                
            except Exception as e:
                db.rollback()
                logger.error(f"[WORKFLOW] Database error: {e}")
                raise
        
        return result


# Global workflow instance
email_workflow = EmailWorkflow()


async def process_email_queue(
    emails: list,
    user_id: int,
    project_id: int,
    db: Session
) -> list:
    """
    Process multiple emails through the workflow queue.
    
    Args:
        emails: List of email data from IMAP service
        user_id: User ID
        project_id: Project ID
        db: Database session
        
    Returns:
        List of processing results
    """
    results = []
    
    logger.info(f"[QUEUE] Processing {len(emails)} emails")
    
    for idx, email_data in enumerate(emails, 1):
        logger.info(f"[QUEUE] Processing email {idx}/{len(emails)}")
        
        try:
            result = await email_workflow.process_email(
                email_data=email_data,
                user_id=user_id,
                project_id=project_id,
                db=db
            )
            results.append(result)
            
        except Exception as e:
            logger.error(f"[QUEUE] Error processing email {idx}: {e}")
            results.append({
                "email_id": email_data.get('id'),
                "error": str(e),
                "intent": "Error"
            })
    
    logger.info(f"[QUEUE] Completed processing {len(results)} emails")
    
    return results
