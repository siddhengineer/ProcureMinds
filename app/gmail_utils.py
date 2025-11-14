from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from app.core.database import get_db
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_SCOPES

def get_gmail_service(project_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT access_token, refresh_token, token_expiry FROM project_gmail_tokens WHERE project_id = %s",
        (project_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise Exception("No Gmail token found for project")

    creds = Credentials(
        token=row[0],
        refresh_token=row[1],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=GOOGLE_SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE project_gmail_tokens SET access_token=%s, token_expiry=%s WHERE project_id=%s",
            (creds.token, creds.expiry, project_id),
        )
        conn.commit()
        cur.close()
        conn.close()

    return build("gmail", "v1", credentials=creds)
