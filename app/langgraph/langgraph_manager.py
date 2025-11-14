import asyncio
import logging
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from app.summary.intent_service import classify_email_intent
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


class EmailWorkflow:
    """LangGraph workflow for processing emails."""
    
    def __init__(self):
        """Initialize the email processing workflow."""
        self.workflow = StateGraph(EmailState)
        
        # Add nodes
        self.workflow.add_node("intent", intent_node)
        
        # Set entry point
        self.workflow.set_entry_point("intent")
        
        # Add edges
        self.workflow.add_edge("intent", END)
        
        # Compile the graph
        self.app = self.workflow.compile()
        
        logger.info("Email workflow initialized")
    
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
            Processing result with intent and database info
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
            "saved_files": []
        }
        
        # Run workflow
        result = await self.app.ainvoke(initial_state)
        
        # If quotation, save to database
        if result['intent'] == "Quotation":
            try:
                # Save attachments (handled by IMAP service)
                attachments_url = None
                if result.get('saved_files'):
                    attachments_url = ",".join(result['saved_files'])
                
                # Create email record
                email_record = Email(
                    user_id=user_id,
                    project_id=project_id,
                    email=result['sender'],
                    message=result['body'],
                    attachments_url=attachments_url
                )
                db.add(email_record)
                db.commit()
                db.refresh(email_record)
                
                result['mail_id'] = email_record.mail_id
                
                logger.info(f"[WORKFLOW] Saved quotation to database (ID: {email_record.mail_id})")
                
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
