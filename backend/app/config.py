"""
Application configuration using Pydantic BaseSettings.
Follows Dependency Inversion Principle — settings injected, not hardcoded.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./ethara_seats.db"

    # API
    APP_TITLE: str = "Ethara Seat Allocation & Project Mapping System"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Manage seat allocation for 5,000 employees at Ethara"
    DEBUG: bool = True

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:80"]

    # Security & JWT
    JWT_SECRET_KEY: str = "ethara_super_secret_signing_key_2026_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # OpenAI (optional)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Gemini (optional)
    GEMINI_API_KEY: str = ""

    # Grok (optional)
    GROK_API_KEY: str = ""
    XAI_API_KEY: str = ""

    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    import secrets
    settings = Settings()
    # Security rotate: If the secret key is empty or matches the hardcoded default,
    # generate a highly secure random token for this session.
    if (
        not settings.JWT_SECRET_KEY
        or settings.JWT_SECRET_KEY == "ethara_super_secret_signing_key_2026_prod"
    ):
        settings.JWT_SECRET_KEY = secrets.token_hex(32)
    return settings
