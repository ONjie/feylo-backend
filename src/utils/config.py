from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """
    Global Application Settings.
    Loads values from environment variables, falls back to a local .env file.
    """
   
    ENVIRONMENT: str = Field(default="development", validation_alias="APP_ENV")
    DEBUG: bool = Field(default=True)
    APP_NAME: str = "Feylo Merchant Payment Backend"
    BASE_URL: str = "http://localhost:8000"
    JWT_SECRET_KEY: str = ''
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRE_DAYS: int = 15
    WEBHOOK_SECRET_KEY: str = ''
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://feylo_postgres_user:feylo_postgres_password@localhost:5432/feylo_db"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0"
    )
    SMS_GATEWAY: str = "simulator"
    AT_API_KEY: str = ""
    AT_USERNAME: str = "sandbox"

    PLATFORM_FEE_PCT: float = 0.01
    OTP_TTL_SECONDS: int = 600
    MAX_OTP_ATTEMPTS: int = 5
    QR_EXPIRY_MINUTES: int = 5

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()