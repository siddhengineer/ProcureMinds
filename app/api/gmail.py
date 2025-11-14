from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
import logging

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.project_gmail_tokens import ProjectGmailToken

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gmail", tags=["Gmail"])

def create_oauth_flow():
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials not configured"
        )
    
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uris": [settings.google_redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=settings.google_scopes_list
    )

@router.get("/auth/google")
def start_gmail_auth(
    project_id: int,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Verify project belongs to user
        project = db.query(Project).filter(
            Project.project_id == project_id,
            Project.user_id == current_user.user_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Starting Gmail OAuth for project {project_id}")
        flow = create_oauth_flow()
        flow.redirect_uri = settings.google_redirect_uri
        
        auth_url, state = flow.authorization_url(
            prompt='consent',
            access_type='offline',
            include_granted_scopes='true'
        )
        
        response.set_cookie(
            "gmail_project_id",
            str(project_id),
            max_age=600,
            httponly=True,
            samesite='lax'
        )
        response.set_cookie(
            "gmail_user_id",
            str(current_user.user_id),
            max_age=600,
            httponly=True,
            samesite='lax'
        )
        
        return RedirectResponse(url=auth_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting Gmail auth: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/google/callback")
def gmail_auth_callback(
    request: Request,
    code: str = None,
    error: str = None,
    db: Session = Depends(get_db)
):
    try:
        if error:
            logger.error(f"OAuth error: {error}")
            return RedirectResponse(
                f"{settings.frontend_url}/dashboard?gmail_error={error}"
            )
        
        project_id = request.cookies.get("gmail_project_id")
        user_id = request.cookies.get("gmail_user_id")
        
        if not project_id or not user_id or not code:
            logger.error("Missing required data in callback")
            return RedirectResponse(
                f"{settings.frontend_url}/dashboard?gmail_error=missing_data"
            )
        
        # Verify project belongs to user
        project = db.query(Project).filter(
            Project.project_id == int(project_id),
            Project.user_id == int(user_id)
        ).first()
        
        if not project:
            return RedirectResponse(
                f"{settings.frontend_url}/dashboard?gmail_error=invalid_project"
            )
        
        # Exchange code for tokens
        flow = create_oauth_flow()
        flow.redirect_uri = settings.google_redirect_uri
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Get user email from Gmail
        temp_service = build('gmail', 'v1', credentials=creds)
        profile = temp_service.users().getProfile(userId='me').execute()
        user_email = profile.get('emailAddress')
        
        # Save or update tokens in database
        existing_token = db.query(ProjectGmailToken).filter(
            ProjectGmailToken.project_id == int(project_id)
        ).first()
        
        if existing_token:
            existing_token.email = user_email
            existing_token.access_token = creds.token
            existing_token.refresh_token = creds.refresh_token
            existing_token.token_expiry = creds.expiry
        else:
            new_token = ProjectGmailToken(
                project_id=int(project_id),
                email=user_email,
                access_token=creds.token,
                refresh_token=creds.refresh_token,
                token_expiry=creds.expiry
            )
            db.add(new_token)
        
        db.commit()
        logger.info(f"Gmail connected successfully for project {project_id}")
        
        return RedirectResponse(
            f"{settings.frontend_url}/dashboard?gmail_connected=true&email={user_email}"
        )
    except Exception as e:
        logger.error(f"Error in Gmail callback: {e}", exc_info=True)
        return RedirectResponse(
            f"{settings.frontend_url}/dashboard?gmail_error={str(e)}"
        )

@router.get("/test")
def test_endpoint():
    return {
        "status": "ok",
        "message": "Gmail API is working",
        "client_id_set": bool(settings.google_client_id),
        "client_secret_set": bool(settings.google_client_secret),
        "redirect_uri": settings.google_redirect_uri
    }


@router.get("/status/{project_id}")
def get_gmail_status(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify project belongs to user
    project = db.query(Project).filter(
        Project.project_id == project_id,
        Project.user_id == current_user.user_id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if Gmail is connected
    gmail_token = db.query(ProjectGmailToken).filter(
        ProjectGmailToken.project_id == project_id
    ).first()
    
    if not gmail_token:
        return {
            "connected": False,
            "email": None
        }
    
    return {
        "connected": True,
        "email": gmail_token.email
    }


@router.delete("/disconnect/{project_id}")
def disconnect_gmail(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify project belongs to user
    project = db.query(Project).filter(
        Project.project_id == project_id,
        Project.user_id == current_user.user_id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Delete Gmail token
    gmail_token = db.query(ProjectGmailToken).filter(
        ProjectGmailToken.project_id == project_id
    ).first()
    
    if gmail_token:
        db.delete(gmail_token)
        db.commit()
    
    return {"message": "Gmail disconnected successfully"}
