import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AURA GAMING"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "9e8c3b7a1d5f2e4b6c8a0d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4c6d8e0f2a"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = "sqlite:///./real_money_game.db"
    
    # Uploads
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 5
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "kyc"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "deposits"), exist_ok=True)
