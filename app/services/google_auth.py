# """
# Google Gmail API Service
# Handles OAuth2 authentication and Gmail operations
# """
# import os
# import base64
# import json
# from typing import List, Dict, Optional
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
# import pickle


# # Gmail API scopes - full access to Gmail
# SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
#           'https://www.googleapis.com/auth/gmail.modify',
#           'https://www.googleapis.com/auth/gmail.compose',
#           'https://mail.google.com/']


# class GmailService:
#     """Service class for Gmail API operations"""
    
#     def __init__(self):
#         self.creds = None
#         self.service = None
#         self.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
#         self.token_file = os.getenv('GOOGLE_TOKEN_FILE', 'token.pickle')
    
#     def authenticate(self) -> bool:
#         """
#         Authenticate with Google Gmail API using OAuth2
#         Returns True if authentication successful
#         """
#         # Load existing credentials from token file
#         if os.path.exists(self.token_file):
#             with open(self.token_file, 'rb') as token:
#                 self.creds = pickle.load(token)
        
#         # If no valid credentials, let user log in
#         if not self.creds or not self.creds.valid:
#             if self.creds and self.creds.expired and self.creds.refresh_token:
#                 try:
#                     self.creds.refresh(Request())
#                 except Exception as e:
#                     print(f"Error refreshing token: {e}")
#                     return self._new_authentication()
#             else:
#                 return self._new_authentication()
            
#             # Save credentials for next run
#             with open(self.token_file, 'wb') as token:
#                 pickle.dump(self.creds, token)
        
#         # Build Gmail service
#         try:
#             self.service = build('gmail', 'v1', credentials=self.creds)
#             return True
#         except Exception as e:
#             print(f"Error building Gmail service: {e}")
#             return False
    
#     def _new_authentication(self) -> bool:
#         """Handle new OAuth2 authentication flow"""
#         try:
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 self.credentials_file, SCOPES)
#             self.creds = flow.run_local_server(port=0)
            
#             # Save credentials
#             with open(self.token_file, 'wb') as token:
#                 pickle.dump(self.creds, token)
            
#             return True
#         except Exception as e:
#             print(f"Error during authentication: {e}")
#             return False

#     def get_messages(self, max_results: int = 100, query: str = '') -> List[Dict]:
#         """
#         Get messages from Gmail inbox
        
#         Args:
#             max_results: Maximum number of messages to retrieve
#             query: Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')
        
#         Returns:
#             List of message dictionaries
#         """
#         if not self.service:
#             if not self.authenticate():
#                 return []
        
#         try:
#             results = self.service.users().messages().list(
#                 userId='me',
#                 maxResults=max_results,
#                 q=query
#             ).execute()
            
#             messages = results.get('messages', [])
            
#             if not messages:
#                 print('No messages found.')
#                 return []
            
#             # Get full message details
#             detailed_messages = []
#             for message in messages:
#                 msg = self.get_message_detail(message['id'])
#                 if msg:
#                     detailed_messages.append(msg)
            
#             return detailed_messages
            
#         except HttpError as error:
#             print(f'An error occurred: {error}')
#             return []
    
#     def get_message_detail(self, message_id: str) -> Optional[Dict]:
#         """
#         Get detailed information about a specific message
        
#         Args:
#             message_id: Gmail message ID
        
#         Returns:
#             Dictionary with message details
#         """
#         if not self.service:
#             if not self.authenticate():
#                 return None
        
#         try:
#             message = self.service.users().messages().get(
#                 userId='me',
#                 id=message_id,
#                 format='full'
#             ).execute()
            
#             # Parse message details
#             headers = message['payload']['headers']
#             subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
#             sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
#             date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
            
#             # Get message body
#             body = self._get_message_body(message['payload'])
            
#             return {
#                 'id': message['id'],
#                 'threadId': message['threadId'],
#                 'subject': subject,
#                 'from': sender,
#                 'date': date,
#                 'snippet': message.get('snippet', ''),
#                 'body': body,
#                 'labels': message.get('labelIds', [])
#             }
            
#         except HttpError as error:
#             print(f'An error occurred: {error}')
#             return None
    
#     def _get_message_body(self, payload: Dict) -> str:
#         """Extract message body from payload"""
#         body = ''
        
#         if 'parts' in payload:
#             for part in payload['parts']:
#                 if part['mimeType'] == 'text/plain':
#                     if 'data' in part['body']:
#                         body = base64.urlsafe_b64decode(
#                             part['body']['data']
#                         ).decode('utf-8')
#                         break
#                 elif part['mimeType'] == 'text/html' and not body:
#                     if 'data' in part['body']:
#                         body = base64.urlsafe_b64decode(
#                             part['body']['data']
#                         ).decode('utf-8')
#         else:
#             if 'body' in payload and 'data' in payload['body']:
#                 body = base64.urlsafe_b64decode(
#                     payload['body']['data']
#                 ).decode('utf-8')
        
#         return body

#     def poll_new_messages(self, last_history_id: Optional[str] = None) -> Dict:
#         """
#         Poll for new messages using Gmail history API
#         More efficient than fetching all messages repeatedly
        
#         Args:
#             last_history_id: Last known history ID to check for changes
        
#         Returns:
#             Dictionary with new messages and updated history ID
#         """
#         if not self.service:
#             if not self.authenticate():
#                 return {'messages': [], 'historyId': None}
        
#         try:
#             if last_history_id:
#                 # Get changes since last history ID
#                 history = self.service.users().history().list(
#                     userId='me',
#                     startHistoryId=last_history_id,
#                     historyTypes=['messageAdded']
#                 ).execute()
                
#                 changes = history.get('history', [])
#                 new_messages = []
                
#                 for change in changes:
#                     if 'messagesAdded' in change:
#                         for msg_added in change['messagesAdded']:
#                             msg_detail = self.get_message_detail(msg_added['message']['id'])
#                             if msg_detail:
#                                 new_messages.append(msg_detail)
                
#                 return {
#                     'messages': new_messages,
#                     'historyId': history.get('historyId')
#                 }
#             else:
#                 # First time - get current messages and history ID
#                 profile = self.service.users().getProfile(userId='me').execute()
#                 messages = self.get_messages(max_results=10)
                
#                 return {
#                     'messages': messages,
#                     'historyId': profile.get('historyId')
#                 }
                
#         except HttpError as error:
#             print(f'An error occurred: {error}')
#             return {'messages': [], 'historyId': last_history_id}
    
#     def get_unread_messages(self, max_results: int = 100) -> List[Dict]:
#         """
#         Get only unread messages from inbox
        
#         Args:
#             max_results: Maximum number of messages to retrieve
        
#         Returns:
#             List of unread message dictionaries
#         """
#         return self.get_messages(max_results=max_results, query='is:unread')
    
#     def mark_as_read(self, message_id: str) -> bool:
#         """
#         Mark a message as read
        
#         Args:
#             message_id: Gmail message ID
        
#         Returns:
#             True if successful
#         """
#         if not self.service:
#             if not self.authenticate():
#                 return False
        
#         try:
#             self.service.users().messages().modify(
#                 userId='me',
#                 id=message_id,
#                 body={'removeLabelIds': ['UNREAD']}
#             ).execute()
#             return True
#         except HttpError as error:
#             print(f'An error occurred: {error}')
#             return False
    
#     def get_attachments(self, message_id: str) -> List[Dict]:
#         """
#         Get attachments from a message
        
#         Args:
#             message_id: Gmail message ID
        
#         Returns:
#             List of attachment dictionaries with filename and data
#         """
#         if not self.service:
#             if not self.authenticate():
#                 return []
        
#         try:
#             message = self.service.users().messages().get(
#                 userId='me',
#                 id=message_id
#             ).execute()
            
#             attachments = []
            
#             for part in message['payload'].get('parts', []):
#                 if part.get('filename'):
#                     if 'data' in part['body']:
#                         data = part['body']['data']
#                     else:
#                         att_id = part['body']['attachmentId']
#                         att = self.service.users().messages().attachments().get(
#                             userId='me',
#                             messageId=message_id,
#                             id=att_id
#                         ).execute()
#                         data = att['data']
                    
#                     attachments.append({
#                         'filename': part['filename'],
#                         'mimeType': part['mimeType'],
#                         'size': part['body'].get('size', 0),
#                         'data': base64.urlsafe_b64decode(data)
#                     })
            
#             return attachments
            
#         except HttpError as error:
#             print(f'An error occurred: {error}')
#             return []


# # Example usage function
# def example_usage():
#     """Example of how to use the GmailService"""
#     gmail = GmailService()
    
#     # Authenticate
#     if gmail.authenticate():
#         print("Authentication successful!")
        
#         # Get latest 10 messages
#         messages = gmail.get_messages(max_results=10)
#         print(f"Retrieved {len(messages)} messages")
        
#         for msg in messages:
#             print(f"\nSubject: {msg['subject']}")
#             print(f"From: {msg['from']}")
#             print(f"Date: {msg['date']}")
#             print(f"Snippet: {msg['snippet']}")
        
#         # Get unread messages
#         unread = gmail.get_unread_messages()
#         print(f"\n{len(unread)} unread messages")
        
#         # Poll for new messages (use history ID for efficient polling)
#         result = gmail.poll_new_messages()
#         history_id = result['historyId']
#         print(f"Current history ID: {history_id}")
        
#         # Later, poll again with the history ID
#         # new_result = gmail.poll_new_messages(last_history_id=history_id)
#         # new_messages = new_result['messages']
#     else:
#         print("Authentication failed!")


# if __name__ == "__main__":
#     example_usage()
