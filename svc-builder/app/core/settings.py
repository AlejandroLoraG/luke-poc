from pathlib import Path
from pydantic import Field, validator
from shared.config import BaseServiceSettings, ServicePorts, ServiceNames


class Settings(BaseServiceSettings):
    # Service Configuration
    service_port: int = Field(
        default=ServicePorts.SVC_BUILDER,
        description="Port for the svc-builder service"
    )

    # Storage Configuration
    storage_path: str = Field(
        default="storage/workflows",
        description="Path to workflow storage directory"
    )

    # Application Configuration
    app_name: str = Field(
        default=ServiceNames.SVC_BUILDER,
        description="Application name"
    )
    app_version: str = Field(
        default="0.1.0",
        description="Application version"
    )

    @validator("storage_path")
    def validate_storage_path(cls, v):
        """Ensure storage directory exists."""
        storage_dir = Path(v)
        storage_dir.mkdir(parents=True, exist_ok=True)
        return v


settings = Settings()