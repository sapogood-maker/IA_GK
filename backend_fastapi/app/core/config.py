from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    refresh_token_expiration_days: int = 7
    env: str = "development"
    
    # R2 Configuration
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_public_url: str = ""
    
    # Upload Configuration
    max_video_size_bytes: int = 500 * 1024 * 1024  # 500 MB default
    allowed_video_extensions: list = ["mp4", "mov", "avi", "mkv"]

    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v
    
    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret(cls, v):
        if not v:
            raise ValueError("JWT_SECRET_KEY is required")
        if len(v) < 32:
            logger.warning("JWT_SECRET_KEY is shorter than recommended (32+ characters)")
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()
