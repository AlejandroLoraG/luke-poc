from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Service Configuration
    service_port: int = 8000
    environment: str = "development"
    log_level: str = "INFO"

    # Storage Configuration
    storage_path: str = "storage/workflows"

    # Application Configuration
    app_name: str = "svc-builder"
    app_version: str = "0.1.0"

    model_config = {"extra": "ignore", "env_file": ".env"}


settings = Settings()

# Ensure storage directory exists
storage_dir = Path(settings.storage_path)
storage_dir.mkdir(parents=True, exist_ok=True)