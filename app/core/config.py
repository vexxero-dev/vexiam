from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "VEX IAM"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "development-secret-key-change-in-production-must-be-32-chars-long"
    
    # Database (Automatically normalizes postgres:// to postgresql+asyncpg://)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vex_iam"
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if isinstance(v, str):
            # Railway provisions PostgreSQL URLs starting with 'postgres://' or 'postgresql://'
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Token Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "EdDSA"
    
    # Offline POS Licensing Settings
    OFFLINE_GRACE_PERIOD_DAYS: int = 30
    
    # Resend Email Settings
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "VEX IAM <onboarding@resend.dev>"
    FRONTEND_URL: str = "http://localhost:3000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
