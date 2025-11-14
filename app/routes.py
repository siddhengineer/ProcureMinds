from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.core.database import get_db
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_SCOPES
from app.gmail_utils import get_gmail_service

router = APIRouter(prefix="/gmail")

def get_flow(redirect_uri: str):
    return Flow.from_client_config(
        {"web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }},
        scopes=GOOGLE_SCOPES,
    )

# Start OAuth flow
@router.get("/auth")
def gmail_auth(project_id: str, redirect_url: str):
    flow = get_flow(redirect_uri=f"http://localhost:8000/gmail/callback?redirect_url={redirect_url}")
    flow.redirect_uri = f"http://localhost:8000/gmail/callback?redirect_url={redirect_url}"

    auth_url, _ = flow.authorization_url(
        prompt="consent", access_type="offline", include_granted_scopes="true"
    )
    resp = RedirectResponse(auth_url)
    resp.set_cookie("project_id", project_id)
    return resp

# OAuth callback
@router.get("/callback")
def gmail_callback(request: Request, redirect_url: str):
    project_id = request.cookies.get("project_id")
    flow = get_flow(redirect_uri=f"http://localhost:8000/gmail/callback?redirect_url={redirect_url}")
    flow.redirect_uri = f"http://localhost:8000/gmail/callback?redirect_url={redirect_url}"

    code = request.query_params["code"]
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Fetch Gmail email
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    email = profile["emailAddress"]

    # Save tokens
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO project_gmail_tokens (project_id, email, access_token, refresh_token, token_expiry)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (project_id)
        DO UPDATE SET access_token=EXCLUDED.access_token,
                      refresh_token=EXCLUDED.refresh_token,
                      token_expiry=EXCLUDED.token_expiry;
    """, (project_id, email, creds.token, creds.refresh_token, creds.expiry))
    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(redirect_url)

# Send email
@router.post("/send")
def send_mail(payload: dict):
    project_id = payload["project_id"]
    to = payload["to"]
    subject = payload["subject"]
    body = payload["body"]

    service = get_gmail_service(project_id)

    from email.mime.text import MIMEText
    import base64

    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject

    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    service.users().messages().send(
        userId="me",
        body={"raw": encoded}
    ).execute()

    return {"status": "sent", "to": to}
