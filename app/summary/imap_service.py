import imaplib
import email
from email.header import decode_header
import os
from pathlib import Path
from typing import List, Dict, Optional, Callable
import logging
import time

logger = logging.getLogger(__name__)


class IMAPEmailService:
    """Service to connect to email via IMAP and retrieve unread messages with attachments."""
    
    def __init__(self, imap_server: str, email_address: str, password: str, port: int = 993):
        """
        Initialize IMAP service.
        
        Args:
            imap_server: IMAP server address (e.g., 'imap.gmail.com')
            email_address: Your email address
            password: Your email password or app-specific password
            port: IMAP port (default 993 for SSL)
        """
        self.imap_server = imap_server
        self.email_address = email_address
        self.password = password
        self.port = port
        self.mail = None
        
    def connect(self) -> bool:
        """Connect to the IMAP server."""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.port)
            self.mail.login(self.email_address, self.password)
            logger.info(f"Successfully connected to {self.imap_server}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the IMAP server."""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
                logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")

    def get_unread_emails(self, folder: str = "INBOX", limit: Optional[int] = None) -> List[Dict]:
        """
        Retrieve all unread emails from specified folder.
        
        Args:
            folder: Email folder to check (default: INBOX)
            limit: Maximum number of emails to fetch (None for all, fetches most recent first)
            
        Returns:
            List of email dictionaries with metadata and content
        """
        if not self.mail:
            logger.error("Not connected to IMAP server")
            return []
        
        try:
            self.mail.select(folder)
            status, messages = self.mail.search(None, 'UNSEEN')
            
            if status != "OK":
                logger.error("Failed to search for unread emails")
                return []
            
            email_ids = messages[0].split()
            total_unread = len(email_ids)
            logger.info(f"Found {total_unread} unread emails")
            
            # If limit is set, only fetch the most recent emails
            if limit and limit < total_unread:
                email_ids = email_ids[-limit:]  # Get the last N (most recent)
                logger.info(f"Limiting to {limit} most recent emails")
            
            emails = []
            for idx, email_id in enumerate(email_ids, 1):
                logger.info(f"Fetching email {idx}/{len(email_ids)}...")
                email_data = self._fetch_email(email_id)
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error retrieving unread emails: {e}")
            return []
    
    def _fetch_email(self, email_id: bytes, mark_as_read: bool = True) -> Optional[Dict]:
        """Fetch and parse a single email."""
        try:
            status, msg_data = self.mail.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                return None
            
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Decode email subject
            subject, encoding = decode_header(email_message["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
            
            # Get sender
            from_header = email_message.get("From")
            
            # Get date
            date = email_message.get("Date")
            
            # Extract body and attachments
            body = self._get_email_body(email_message)
            attachments = self._get_attachments(email_message)
            
            # Mark email as read
            if mark_as_read:
                self._mark_as_read(email_id)
            
            return {
                "id": email_id.decode(),
                "subject": subject,
                "from": from_header,
                "date": date,
                "body": body,
                "attachments": attachments
            }
            
        except Exception as e:
            logger.error(f"Error fetching email {email_id}: {e}")
            return None
    
    def _mark_as_read(self, email_id: bytes):
        """Mark an email as read."""
        try:
            self.mail.store(email_id, '+FLAGS', '\\Seen')
            logger.debug(f"Marked email {email_id.decode()} as read")
        except Exception as e:
            logger.error(f"Error marking email {email_id} as read: {e}")

    def _get_email_body(self, email_message) -> str:
        """Extract email body text."""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        pass
        else:
            try:
                body = email_message.get_payload(decode=True).decode()
            except:
                pass
        
        return body
    
    def _get_attachments(self, email_message) -> List[Dict]:
        """Extract attachment metadata from email."""
        attachments = []
        
        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            
            filename = part.get_filename()
            if filename:
                # Decode filename if needed
                decoded_filename = decode_header(filename)[0]
                if isinstance(decoded_filename[0], bytes):
                    filename = decoded_filename[0].decode(decoded_filename[1] if decoded_filename[1] else "utf-8")
                else:
                    filename = decoded_filename[0]
                
                attachments.append({
                    "filename": filename,
                    "content_type": part.get_content_type(),
                    "size": len(part.get_payload(decode=True)),
                    "data": part.get_payload(decode=True)
                })
        
        return attachments
    
    def save_attachments(self, email_data: Dict, output_dir: str = "downloads/attachments") -> List[str]:
        """
        Save email attachments to local directory.
        
        Args:
            email_data: Email dictionary containing attachments
            output_dir: Directory to save attachments
            
        Returns:
            List of saved file paths
        """
        saved_files = []
        
        if not email_data.get("attachments"):
            return saved_files
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        for attachment in email_data["attachments"]:
            try:
                filename = attachment["filename"]
                filepath = os.path.join(output_dir, filename)
                
                # Handle duplicate filenames
                counter = 1
                base_name, extension = os.path.splitext(filename)
                while os.path.exists(filepath):
                    filename = f"{base_name}_{counter}{extension}"
                    filepath = os.path.join(output_dir, filename)
                    counter += 1
                
                with open(filepath, "wb") as f:
                    f.write(attachment["data"])
                
                saved_files.append(filepath)
                logger.info(f"Saved attachment: {filepath}")
                
            except Exception as e:
                logger.error(f"Error saving attachment {attachment.get('filename')}: {e}")
        
        return saved_files

    def process_unread_emails(self, output_dir: str = "downloads/attachments", mark_as_read: bool = True) -> Dict:
        """
        Main method to retrieve all unread emails and save attachments.
        
        Args:
            output_dir: Directory to save attachments
            mark_as_read: Whether to mark emails as read after processing
            
        Returns:
            Dictionary with processing results
        """
        results = {
            "total_emails": 0,
            "processed_emails": [],
            "total_attachments": 0,
            "saved_files": []
        }
        
        unread_emails = self.get_unread_emails()
        results["total_emails"] = len(unread_emails)
        
        for email_data in unread_emails:
            saved_files = self.save_attachments(email_data, output_dir)
            
            results["processed_emails"].append({
                "subject": email_data["subject"],
                "from": email_data["from"],
                "date": email_data["date"],
                "attachments_count": len(email_data["attachments"]),
                "saved_files": saved_files
            })
            
            results["total_attachments"] += len(email_data["attachments"])
            results["saved_files"].extend(saved_files)
        
        logger.info(f"Processed {results['total_emails']} emails with {results['total_attachments']} attachments")
        return results
    
    def start_polling(self, 
                     interval_seconds: int = 30, 
                     output_dir: str = "downloads/attachments",
                     callback: Optional[Callable[[Dict], None]] = None,
                     max_iterations: Optional[int] = None):
        """
        Start polling for new unread emails at regular intervals.
        
        Args:
            interval_seconds: Time between checks in seconds (default: 30)
            output_dir: Directory to save attachments
            callback: Optional callback function to call with results after each poll
            max_iterations: Maximum number of polling iterations (None for infinite)
        """
        iteration = 0
        logger.info(f"Starting email polling every {interval_seconds} seconds")
        
        try:
            while True:
                if max_iterations is not None and iteration >= max_iterations:
                    logger.info(f"Reached maximum iterations ({max_iterations}), stopping polling")
                    break
                
                logger.info(f"Polling iteration {iteration + 1}")
                
                try:
                    # Process unread emails
                    results = self.process_unread_emails(output_dir)
                    
                    if results["total_emails"] > 0:
                        logger.info(f"Found and processed {results['total_emails']} new emails")
                    else:
                        logger.debug("No new unread emails")
                    
                    # Call callback if provided
                    if callback:
                        callback(results)
                    
                except Exception as e:
                    logger.error(f"Error during polling iteration: {e}")
                    # Try to reconnect
                    logger.info("Attempting to reconnect...")
                    if not self.connect():
                        logger.error("Reconnection failed, will retry next iteration")
                
                iteration += 1
                
                # Wait before next poll
                if max_iterations is None or iteration < max_iterations:
                    time.sleep(interval_seconds)
                    
        except KeyboardInterrupt:
            logger.info("Polling stopped by user")
        except Exception as e:
            logger.error(f"Polling stopped due to error: {e}")
        finally:
            self.disconnect()


