import asyncio
import logging
import json
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from app.summary.intent_service import classify_email_intent
from app.summary.extraction_service import BenchmarkExtractionService
from app.models.emails import Email
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
    benchmark_analysis: dict | None
    db: Session


def intent_node(state: EmailState) -> EmailState:
    """
    Classify email intent.
    
    Args:
        state: Current email state
        
    Returns:
        Updated state with intent classification
    """
    logger.info(f"[INTENT NODE] Processing email: {state['subject']}")
    
    # Classify the email
    intent = classify_email_intent(state['body'])
    
    logger.info(f"[INTENT NODE] Classified as: {intent}")
    
    return {
        **state,
        "intent": intent
    }


def benchmark_analysis_node(state: EmailState) -> EmailState:
    """
    Analyze vendor email against project benchmarks.
    
    Args:
        state: Current email state
        
    Returns:
        Updated state with benchmark analysis
    """
    logger.info(f"[BENCHMARK NODE] Analyzing email: {state['subject']}")
    
    try:
        # Initialize extraction service
        extraction_service = BenchmarkExtractionService(state['db'])
        
        # Prepare attachments info
        attachments_info = [
            {"filename": att, "content_type": "application/octet-stream"}
            for att in state.get('attachments', [])
        ]
        
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
        self.workflow.add_node("benchmark_analysis", benchmark_analysis_node)
        
        # Set entry point
        self.workflow.set_entry_point("intent")
        
        # Add conditional edges
        self.workflow.add_conditional_edges(
            "intent",
            should_analyze_benchmarks,
            {
                "analyze": "benchmark_analysis",
                "skip": END
            }
        )
        
        # Add edge from benchmark analysis to end
        self.workflow.add_edge("benchmark_analysis", END)
        
        # Compile the graph
        self.app = self.workflow.compile()
        
        logger.info("Email workflow initialized with benchmark analysis")
    
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
            "benchmark_analysis": None,
            "db": db
        }
        
        # Run workflow
        result = await self.app.ainvoke(initial_state)
        
        # If quotation, save to database with benchmark analysis
        if result['intent'] == "Quotation":
            try:
                # Save attachments (handled by IMAP service)
                attachments_url = None
                if result.get('saved_files'):
                    attachments_url = ",".join(result['saved_files'])
                
                # Prepare summary JSON
                summary_json = None
                overall_score = None
                if result.get('benchmark_analysis'):
                    summary_json = json.dumps(result['benchmark_analysis'])
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
                    f"Score: {overall_score})"
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
