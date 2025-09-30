"""
Shared configuration utilities and base classes.

This module provides common configuration patterns and utilities
used across all services in the chat-agent system.
"""

from typing import Literal, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Base configuration class for all services."""

    # Common environment settings
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )

    # Pydantic configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_assignment=True
    )

    @validator("log_level", pre=True)
    def validate_log_level(cls, v):
        """Ensure log level is uppercase."""
        if isinstance(v, str):
            return v.upper()
        return v


class ServicePorts:
    """Standard port definitions for all services."""
    AI_AGENT = 8001
    MCP_SERVER = 8002
    SVC_BUILDER = 8000


class ServiceNames:
    """Standard service names for consistent identification."""
    AI_AGENT = "ai-agent"
    MCP_SERVER = "mcp-server"
    SVC_BUILDER = "svc-builder"


class NetworkConfig:
    """Network configuration constants."""

    @staticmethod
    def get_service_url(service_name: str, port: int, use_docker: bool = True) -> str:
        """
        Generate service URL based on environment.

        Args:
            service_name: Name of the service
            port: Port number
            use_docker: Whether to use Docker network naming

        Returns:
            Complete service URL
        """
        host = service_name if use_docker else "localhost"
        return f"http://{host}:{port}"


def validate_required_env_var(value: Optional[str], var_name: str) -> str:
    """
    Validate that a required environment variable is set.

    Args:
        value: The environment variable value
        var_name: Name of the environment variable

    Returns:
        The validated value

    Raises:
        ValueError: If the environment variable is not set
    """
    if not value or value.strip() == "":
        raise ValueError(f"Required environment variable {var_name} is not set")
    return value.strip()