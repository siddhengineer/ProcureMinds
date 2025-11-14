from fastapi import APIRouter, HTTPException
from app.summary.imap_service import IMAPEmailService
import os
import asyncio
import logging
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)

# Global polling task
polling_task: Optional[asyncio.Task] = None
is_polling = False

def get_imap_credentials():
    """Get IMAP credentials from environment variables."""
    return {
        "imap_server": os.getenv("IMAP_SERVER"),
        "email_address": os.getenv("IMAP_EMAIL"),
        "password": os.getenv("IMAP_PASSWORD"),
        "port": int(os.getenv("IMAP_PORT", 993))
    }

async def poll_emails():
    """Background task that polls for new emails every 30 seconds."""
    global is_polling
    
    credentials = get_imap_credentials()
    service = IMAPEmailService(**credentials)
    
    if not service.connect():
        error_msg = "Failed to connect to IMAP server for polling"
        logger.error(error_msg)
        print(f"ERROR: {error_msg}")
        is_polling = False
        return
    
    start_msg = "Email polling started - checking every 30 seconds (limit: 10 most recent emails)"
    logger.info(start_msg)
    print(f"\n{'='*80}")
    print(f"INFO: {start_msg}")
    print(f"{'='*80}\n")
    
    try:
        while is_polling:
            try:
                print(f"\n[POLLING] Checking for new emails at {asyncio.get_event_loop().time():.0f}s...")
                
                # Get only the 10 most recent unread emails
                emails = service.get_unread_emails(limit=10)
                
                if emails:
                    msg = f"Processing {len(emails)} most recent unread email(s)"
                    logger.info(msg)
                    print(f"INFO: {msg}\n")
                    
                    for idx, email_data in enumerate(emails, 1):
                        # Print and log full email details
                        separator = "=" * 80
                        print(f"\n{separator}")
                        print(f"NEW EMAIL #{idx}")
                        print(f"Subject: {email_data['subject']}")
                        print(f"From: {email_data['from']}")
                        print(f"Date: {email_data['date']}")
                        print(f"Body:\n{email_data['body']}")
                        
                        logger.info(separator)
                        logger.info(f"NEW EMAIL #{idx}")
                        logger.info(f"Subject: {email_data['subject']}")
                        logger.info(f"From: {email_data['from']}")
                        logger.info(f"Date: {email_data['date']}")
                        logger.info(f"Body:\n{email_data['body']}")
                        
                        # Log and save attachments
                        if email_data['attachments']:
                            att_msg = f"Attachments ({len(email_data['attachments'])}):"
                            print(att_msg)
                            logger.info(att_msg)
                            
                            saved_files = service.save_attachments(email_data)
                            for i, attachment in enumerate(email_data['attachments']):
                                att_detail = f"  {i+1}. {attachment['filename']} ({attachment['content_type']}, {attachment['size']} bytes)"
                                print(att_detail)
                                logger.info(att_detail)
                                if i < len(saved_files):
                                    saved_msg = f"     Saved to: {saved_files[i]}"
                                    print(saved_msg)
                                    logger.info(saved_msg)
                        else:
                            no_att_msg = "No attachments"
                            print(no_att_msg)
                            logger.info(no_att_msg)
                        
                        print(separator)
                        logger.info(separator)
                else:
                    print("[POLLING] No new unread emails")
                    logger.debug("No new unread emails")
                
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
async def start_polling():
    """Start polling for new emails every 30 seconds."""
    global polling_task, is_polling
    
    if is_polling:
        return {"status": "already_running", "message": "Email polling is already active"}
    
    is_polling = True
    polling_task = asyncio.create_task(poll_emails())
    
    return {
        "status": "started",
        "message": "Email polling started - checking every 30 seconds",
        "interval": "30 seconds"
    }

@router.post("/emails/stop-polling")
async def stop_polling():
    """Stop the email polling task."""
    global polling_task, is_polling
    
    if not is_polling:
        return {"status": "not_running", "message": "Email polling is not active"}
    
    is_polling = False
    
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    
    return {"status": "stopped", "message": "Email polling stopped"}

@router.get("/emails/polling-status")
async def get_polling_status():
    """Get the current status of email polling."""
    return {
        "is_polling": is_polling,
        "status": "running" if is_polling else "stopped"
    }