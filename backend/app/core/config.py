"""Application configuration loaded from environment variables."""

import json
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Google Sheets
    google_sheets_spreadsheet_id: str = ""
    google_service_account_file: str = "credentials.json"

    # JWT
    jwt_secret_key: str = "your-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # App
    app_title: str = "Pencatatan Keuangan Pribadi"
    app_version: str = "1.0.0"
    cors_origins: str = '["http://localhost:3000","http://localhost:5173"]'

    # Cache
    cache_ttl: int = 300

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.cors_origins)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from .env (e.g., telegram bot config)


settings = Settings()
