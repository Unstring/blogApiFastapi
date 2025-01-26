from pydantic_settings import BaseSettings
from datetime import timedelta

class Settings(BaseSettings):
    # Database settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "new_user"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "blog_api"
    
    # JWT settings
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Blog API"
    VERSION: str = "1.0.0"
    
    # CORS settings
    CORS_ORIGINS: list = ["*"]
    
    # Add admin password hash
    ADMIN_PASSWORD_HASH: str = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYMyzJ/eRm"  # "admin123"

    class Config:
        env_file = ".env"

settings = Settings()