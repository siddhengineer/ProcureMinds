"""
Gmail Polling Service
Continuously polls Gmail for new messages
"""
import time
import json
from typing import Optional, Callable
from app.services.google_auth import GmailService


class GmailPoller:
    """Service to continuously poll Gmail for new messages"""
    
    def __init__(self, poll_interval: int = 30):
        """
        Initialize Gmail poller
        
        Args:
            poll_interval: Seconds between polls (default: 30)
        """
        self.gmail = GmailService()
        self.poll_interval = poll_interval
        self.history_id = None
        self.is_running = False
    
    def start_polling(self, callback: Optional[Callable] = None):
        """
        Start polling for new messages
        
        Args:
            callback: Function to call when new messages arrive
                     Should accept a list of message dictionaries
        """
        if not self.gmail.authenticate():
            print("Failed to authenticate with Gmail")
            return
        
        print("Starting Gmail polling...")
        self.is_running = True
        
        # Initial poll to get history ID
        result = self.gmail.poll_new_messages()
        self.history_id = result['historyId']
        print(f"Initial history ID: {self.history_id}")
        
        # Process initial messages if callback provided
        if callback and result['messages']:
            callback(result['messages'])
        
        # Start polling loop
        while self.is_running:
            try:
                time.sleep(self.poll_interval)
                
                # Poll for new messages
                result = self.gmail.poll_new_messages(
                    last_history_id=self.history_id
                )
                
                new_messages = result['messages']
                
                if new_messages:
                    print(f"Received {len(new_messages)} new message(s)")
                    
                    # Call callback function if provided
                    if callback:
                        callback(new_messages)
                    else:
                        # Default behavior - print message details
                        for msg in new_messages:
                            print(f"\n--- New Message ---")
                            print(f"Subject: {msg['subject']}")
                            print(f"From: {msg['from']}")
                            print(f"Date: {msg['date']}")
                            print(f"Snippet: {msg['snippet']}")
                
                # Update history ID
                if result['historyId']:
                    self.history_id = result['historyId']
                
            except KeyboardInterrupt:
                print("\nStopping Gmail polling...")
                self.is_running = False
                break
            except Exception as e:
                print(f"Error during polling: {e}")
                time.sleep(self.poll_interval)
    
    def stop_polling(self):
        """Stop the polling loop"""
        self.is_running = False


# Example callback function
def process_new_message(messages):
    """
    Example callback to process new messages
    
    Args:
        messages: List of new message dictionaries
    """
    for msg in messages:
        print(f"\n=== Processing New Email ===")
        print(f"ID: {msg['id']}")
        print(f"Subject: {msg['subject']}")
        print(f"From: {msg['from']}")
        print(f"Date: {msg['date']}")
        
        # Check if it's unread
        if 'UNREAD' in msg['labels']:
            print("Status: UNREAD")
        
        # Get body preview
        body_preview = msg['body'][:200] if msg['body'] else msg['snippet']
        print(f"Preview: {body_preview}...")
        
        # You can add your custom logic here:
        # - Save to database
        # - Send notification
        # - Process attachments
        # - Auto-reply
        # - Trigger workflows
        
        print("=" * 40)


# Example usage
if __name__ == "__main__":
    # Create poller with 30 second interval
    poller = GmailPoller(poll_interval=30)
    
    # Start polling with custom callback
    poller.start_polling(callback=process_new_message)
    
    # Or start with default behavior (just print)
    # poller.start_polling()
