"""
Updated config.py with Google OAuth fields
Copy this to: ProcureMinds/app/core/config.py
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    
    # Google OAuth Configuration
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:8000/api/gmail/auth/google/callback"
    google_scopes: str = "https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/gmail.readonly"
    
    # Frontend URL
    frontend_url: str = "http://localhost:3000"

    # Gemini API Configuration
    gemini_api_key: str = ""
    gemini_model: str = ""

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def google_scopes_list(self) -> list:
        return self.google_scopes.split(",")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# Export individual settings for backward compatibility
GOOGLE_CLIENT_ID = settings.google_client_id
GOOGLE_CLIENT_SECRET = settings.google_client_secret
GOOGLE_REDIRECT_URI = settings.google_redirect_uri
GOOGLE_SCOPES = settings.google_scopes_list
FRONTEND_URL = settings.frontend_url
