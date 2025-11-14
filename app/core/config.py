from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = ""

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    GOOGLE_SCOPES: Optional[str] = None

    # IMAP Email
    IMAP_SERVER: Optional[str] = None
    IMAP_EMAIL: Optional[str] = None
    IMAP_PASSWORD: Optional[str] = None
    IMAP_PORT: int = 993

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Remove extra='forbid' if it exists, or change to 'allow'
        extra = "allow"  # or remove this line entirely


settings = Settings()
