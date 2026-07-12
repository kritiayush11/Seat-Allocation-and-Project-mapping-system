"""
Application configuration using Pydantic BaseSettings.
Follows Dependency Inversion Principle — settings injected, not hardcoded.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./ethara_seats.db"

    # API
    APP_TITLE: str = "Ethara Seat Allocation & Project Mapping System"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Manage seat allocation for 5,000 employees at Ethara"
    DEBUG: bool = True

    # CORS — stored as raw string so pydantic-settings never tries to JSON-parse it.
    # Accepts comma-separated (Render-friendly) OR JSON array:
    #   ALLOWED_ORIGINS=https://myapp.onrender.com,http://localhost:3000
    #   ALLOWED_ORIGINS=["https://myapp.onrender.com","http://localhost:3000"]
    ALLOWED_ORIGINS_RAW: str = "https://ethara-frontend12.netlify.app,http://localhost:5173,http://localhost:3000,http://localhost:80"

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        v = self.ALLOWED_ORIGINS_RAW.strip()
        if v.startswith("["):
            import json
            return json.loads(v)
        return [o.strip() for o in v.split(",") if o.strip()]

    # Security & JWT
    JWT_SECRET_KEY: str = "ethara_super_secret_signing_key_2026_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # OpenAI (optional)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Gemini (optional)
    GEMINI_API_KEY: str = ""

    # Groq — free inference platform (groq.com), ultra-fast Llama 3.3 70B
    # Get free key at: https://console.groq.com/keys
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # xAI / Grok (optional fallback)
    GROK_API_KEY: str = ""
    XAI_API_KEY: str = ""
    GROK_MODEL: str = "grok-3-mini"

    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    import secrets
    settings = Settings()
    # Security rotate: only replace the key when it is the hardcoded placeholder.
    # If JWT_SECRET_KEY was explicitly set via environment variable (e.g. in Docker
    # or a real .env file), leave it unchanged so tokens remain valid across restarts.
    if settings.JWT_SECRET_KEY == "ethara_super_secret_signing_key_2026_prod":
        settings.JWT_SECRET_KEY = secrets.token_hex(32)
    return settings
