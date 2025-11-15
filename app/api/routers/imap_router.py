from fastapi import APIRouter, HTTPException, Depends
from app.summary.imap_service import IMAPEmailService
from app.langgraph.langgraph_manager import process_email_queue
from app.core.database import get_db
from sqlalchemy.orm import Session
import os
import asyncio
import logging
from typing import Optional, Set
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

# Global polling task and state
polling_task: Optional[asyncio.Task] = None
is_polling = False
processed_email_ids: Set[str] = set()  # Track processed email IDs
polling_start_time: Optional[datetime] = None
current_user_id: Optional[int] = None
current_project_id: Optional[int] = None

def get_imap_credentials():
    """Get IMAP credentials from environment variables."""
    return {
        "imap_server": os.getenv("IMAP_SERVER"),
        "email_address": os.getenv("IMAP_EMAIL"),
        "password": os.getenv("IMAP_PASSWORD"),
        "port": int(os.getenv("IMAP_PORT", 993))
    }

async def poll_emails(user_id: int, project_id: int, db: Session):
    """Background task that polls for new emails every 30 seconds."""
    global is_polling, processed_email_ids, polling_start_time
    
    credentials = get_imap_credentials()
    service = IMAPEmailService(**credentials)
    
    if not service.connect():
        error_msg = "Failed to connect to IMAP server for polling"
        logger.error(error_msg)
        print(f"ERROR: {error_msg}")
        is_polling = False
        return
    
    # Mark the start time
    polling_start_time = datetime.now()
    
    # Get initial unread emails to mark as "already processed"
    initial_emails = service.get_unread_emails(limit=10)
    for email_data in initial_emails:
        processed_email_ids.add(email_data['id'])
    
    start_msg = f"Email polling started - will only process NEW emails from {polling_start_time.strftime('%Y-%m-%d %H:%M:%S')}"
    logger.info(start_msg)
    print(f"\n{'='*80}")
    print(f"INFO: {start_msg}")
    print(f"INFO: Marked {len(processed_email_ids)} existing emails as already processed")
    print(f"{'='*80}\n")
    
    try:
        while is_polling:
            try:
                print(f"\n[POLLING] Checking for new emails...")
                
                # Get recent unread emails
                emails = service.get_unread_emails(limit=20)
                
                # Filter to only NEW emails (not processed before)
                new_emails = [e for e in emails if e['id'] not in processed_email_ids]
                
                if new_emails:
                    msg = f"Found {len(new_emails)} NEW email(s)"
                    logger.info(msg)
                    print(f"INFO: {msg}\n")
                    
                    # Mark all as processed
                    for email_data in new_emails:
                        processed_email_ids.add(email_data['id'])
                    
                    # Save attachments first
                    for email_data in new_emails:
                        if email_data['attachments']:
                            saved_files = service.save_attachments(email_data)
                            email_data['saved_files'] = saved_files
                        else:
                            email_data['saved_files'] = []
                    
                    # Process through LangGraph workflow queue
                    print(f"[WORKFLOW] Processing {len(new_emails)} emails through LangGraph workflow...")
                    results = await process_email_queue(
                        emails=new_emails,
                        user_id=user_id,
                        project_id=project_id,
                        db=db
                    )
                    
                    # Print results
                    for idx, result in enumerate(results, 1):
                        separator = "=" * 80
                        print(f"\n{separator}")
                        print(f"EMAIL #{idx} PROCESSED")
                        print(f"Subject: {result.get('subject', 'N/A')}")
                        print(f"From: {result.get('sender', 'N/A')}")
                        print(f"Intent: {result.get('intent', 'N/A')}")
                        
                        if result.get('mail_id'):
                            print(f"Database ID: {result['mail_id']}")
                            print(f"Status: Saved as Quotation")
                        elif result.get('error'):
                            print(f"Error: {result['error']}")
                        else:
                            print(f"Status: Classified as Casual (not saved)")
                        
                        print(separator)
                        
                        logger.info(f"Processed email {idx}: Intent={result.get('intent')}, mail_id={result.get('mail_id')}")
                else:
                    print("[POLLING] No new emails since last check")
                    logger.debug("No new emails")
                
            except Exception as e:
                error_msg = f"Error during polling: {e}"
                logger.error(error_msg)
                print(f"ERROR: {error_msg}")
                
                # Try to reconnect
                print("Attempting to reconnect...")
                logger.info("Attempting to reconnect...")
                service.disconnect()
                service = IMAPEmailService(**credentials)
                if not service.connect():
                    reconnect_error = "Reconnection failed"
                    logger.error(reconnect_error)
                    print(f"ERROR: {reconnect_error}")
                    break
            
            # Wait 30 seconds before next poll
            print(f"[POLLING] Waiting 30 seconds before next check...\n")
            await asyncio.sleep(30)
            
    except asyncio.CancelledError:
        cancel_msg = "Polling task cancelled"
        logger.info(cancel_msg)
        print(f"INFO: {cancel_msg}")
    finally:
        service.disconnect()
        is_polling = False
        stop_msg = "Email polling stopped"
        logger.info(stop_msg)
        print(f"INFO: {stop_msg}")

@router.post("/emails/start-polling")
async def start_polling(user_id: int, project_id: int, db: Session = Depends(get_db)):
    """
    Start polling for new emails every 30 seconds.
    Only processes emails received AFTER polling starts.
    
    Args:
        user_id: User ID for database records
        project_id: Project ID for database records
    """
    global polling_task, is_polling, processed_email_ids, current_user_id, current_project_id
    
    if is_polling:
        return {"status": "already_running", "message": "Email polling is already active"}
    
    # Reset processed emails tracking
    processed_email_ids.clear()
    
    is_polling = True
    current_user_id = user_id
    current_project_id = project_id
    polling_task = asyncio.create_task(poll_emails(user_id, project_id, db))
    
    return {
        "status": "started",
        "message": "Email polling started - will only process NEW emails from now on",
        "interval": "30 seconds",
        "user_id": user_id,
        "project_id": project_id
    }

@router.post("/emails/stop-polling")
async def stop_polling():
    """Stop the email polling task."""
    global polling_task, is_polling, current_user_id, current_project_id
    
    if not is_polling:
        return {"status": "not_running", "message": "Email polling is not active"}
    
    is_polling = False
    
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    
    # Clear the current project/user info
    current_user_id = None
    current_project_id = None
    
    return {"status": "stopped", "message": "Email polling stopped"}

@router.get("/emails/polling-status")
async def get_polling_status():
    """Get the current status of email polling."""
    return {
        "is_polling": is_polling,
        "status": "running" if is_polling else "stopped",
        "user_id": current_user_id,
        "project_id": current_project_id,
        "polling_start_time": polling_start_time.isoformat() if polling_start_time else None,
        "processed_email_count": len(processed_email_ids)
    }