"""
Updated config.py with Google OAuth fields
Copy this to: ProcureMinds/app/core/config.py
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # JWT Configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Gemini API Configuration
    gemini_api_key: str
    gemini_model: str
    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-4o"
    # Optional Google fields present in .env; not used here but allowed
    google_credentials_file: str | None = None
    google_token_file: str | None = None

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def google_scopes_list(self) -> list:
        return self.google_scopes.split(",")

    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # ignore unknown keys in .env
    )


settings = Settings()

# Export individual settings for backward compatibility
GOOGLE_CLIENT_ID = settings.google_client_id
GOOGLE_CLIENT_SECRET = settings.google_client_secret
GOOGLE_REDIRECT_URI = settings.google_redirect_uri
GOOGLE_SCOPES = settings.google_scopes_list
FRONTEND_URL = settings.frontend_url
