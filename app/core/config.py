from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
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

    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # ignore unknown keys in .env
    )


settings = Settings()
