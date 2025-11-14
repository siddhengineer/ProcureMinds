from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import Optional

load_dotenv()




class Settings(BaseSettings):
    # Database
    DATABASE_URL: str 

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

    OPENAI_API_KEY: Optional[str] = None

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    
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
        return self.GOOGLE_SCOPES.split(",")

    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # ignore unknown keys in .env
    )


settings = Settings()

# Export individual settings for backward compatibility
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI
GOOGLE_SCOPES = settings.google_scopes_list
FRONTEND_URL = settings.frontend_url
