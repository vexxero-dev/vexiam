from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "VEX IAM"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "development-secret-key-change-in-production-must-be-32-chars-long"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vex_iam"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Token Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "EdDSA"
    
    # Offline POS Licensing Settings
    OFFLINE_GRACE_PERIOD_DAYS: int = 30
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
