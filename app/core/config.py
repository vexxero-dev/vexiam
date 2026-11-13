from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "VEX IAM"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "development-secret-key-change-in-production-must-be-32-chars-long"
    PLATFORM_ADMIN_KEY: str = "dev-platform-admin-key-change-in-production"
    
    # Allowed CORS Origins
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://vexiam.vexxero.com",
        "https://api.vexxero.com",
        "https://vexxero.com",
    ]

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: any) -> list[str]:
        if isinstance(v, str):
            if v.strip().startswith("[") and v.strip().endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
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
    JWT_ISSUER: str = "https://iam.vexxero.com"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "EdDSA"
    JWT_PRIVATE_KEY_PEM: Optional[str] = None
    
    # Offline POS Licensing Settings
    OFFLINE_GRACE_PERIOD_DAYS: int = 7
    
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
