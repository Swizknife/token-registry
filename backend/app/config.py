"""Application configuration, loaded from environment variables / .env."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://queue:queue@localhost:5432/queue"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12

    # Token generation
    token_prefix: str = "A"

    # Kiosk behaviour
    kiosk_reset_seconds: int = 20

    # SMS
    sms_provider: Literal["console", "twilio"] = "console"
    sms_max_attempts: int = 3
    public_queue_url: str = "http://localhost:5173/display"

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None

    # Prediction service
    prediction_service_url: str = "http://localhost:8001"
    prediction_timeout_seconds: float = 1.5

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    # Seed admin
    seed_admin_username: str = "admin"
    seed_admin_password: str = "admin123"


@lru_cache
def get_settings() -> Settings:
    return Settings()
