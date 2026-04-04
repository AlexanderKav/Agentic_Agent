# app/config.py
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Agentic Analyst"
    VERSION: str = "1.0.0"

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    AUDIT_SECRET_KEY: str

    # Database
    DATABASE_URL: str | None = "sqlite:///./agentic_analyst.db"

    # Database Pool Settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # Redis (for session management and caching)
    REDIS_URL: str | None = None
    SESSION_TIMEOUT: int = 3600

    # Celery (for async tasks)
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # OpenAI
    OPENAI_API_KEY: str | None = None

    # Email (SMTP)
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    FROM_EMAIL: str | None = None
    FROM_NAME: str = "Agentic Analyst"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Key Rotation
    KEY_ROTATION_DAYS: int = 90
    KEY_GRACE_PERIOD_DAYS: int = 1

    # Secrets Manager
    SECRETS_BACKEND: str = "local"  # local, aws, or gcp
    SECRETS_FILE: str = "/app/data/secrets.enc"
    SECRETS_KEY_FILE: str = "/app/data/secrets.key"
    SECRETS_MASTER_PASSWORD: str | None = None

    # Encryption
    DB_ENCRYPTION_KEY: str | None = None

    # Google Sheets
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None

    # CORS (comma-separated list)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_ROWS: int = 100000  # Maximum rows to process

    @field_validator('SECRET_KEY', 'AUDIT_SECRET_KEY')
    @classmethod
    def validate_production_secrets(cls, v: str, info) -> str:
        """Validate that required secrets are set in production"""
        if not v and cls.get_env() == "production":
            raise ValueError(f"{info.field_name} must be set in production")
        return v

    @field_validator('OPENAI_API_KEY')
    @classmethod
    def validate_openai_key(cls, v: str | None) -> str | None:
        """Warn if OpenAI key is missing in production"""
        if not v and cls.get_env() == "production":
            print("⚠️ Warning: OPENAI_API_KEY not set. AI features will not work.")
        return v

    @classmethod
    def get_env(cls) -> str:
        """Helper to get current environment"""
        import os
        return os.getenv("ENVIRONMENT", "development")

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT == "development"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS string into a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = "ignore"  # Ignore extra fields from .env
        case_sensitive = True


# Singleton instance
settings = Settings()


# Helper function to get settings (useful for dependency injection)
def get_settings() -> Settings:
    """Return the settings singleton instance."""
    return settings