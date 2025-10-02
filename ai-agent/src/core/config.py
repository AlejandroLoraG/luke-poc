from typing import Optional
from pydantic import Field, validator
from shared.config import BaseServiceSettings, ServicePorts, ServiceNames, NetworkConfig, validate_required_env_var


class Settings(BaseServiceSettings):
    # AI Agent Configuration
    google_api_key: str = Field(
        ...,
        description="Google Gemini API key for AI functionality"
    )
    ai_agent_port: int = Field(
        default=ServicePorts.AI_AGENT,
        description="Port for the AI Agent service"
    )
    ai_model: str = Field(
        default="gemini-2.5-flash-lite",
        description="AI model to use for conversations"
    )

    # MCP Client Configuration
    mcp_server_url: str = Field(
        default_factory=lambda: NetworkConfig.get_service_url(
            ServiceNames.MCP_SERVER,
            ServicePorts.MCP_SERVER,
            use_docker=False  # Default to localhost for development
        ),
        description="URL for the MCP server"
    )
    mcp_connection_timeout: int = Field(
        default=30,
        description="Timeout for MCP server connections in seconds"
    )

    # Conversation Management
    max_conversation_length: int = Field(
        default=15,
        description="Maximum number of messages to keep in conversation history"
    )

    # Debug Configuration
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode with direct svc-builder API calls for diagnostics"
    )
    svc_builder_url: str = Field(
        default="http://svc-builder:8000",
        description="Direct svc-builder API URL for debug mode"
    )

    @validator("google_api_key")
    def validate_google_api_key(cls, v):
        """Validate that Google API key is provided."""
        return validate_required_env_var(v, "GOOGLE_API_KEY")

    @validator("mcp_server_url")
    def validate_mcp_server_url(cls, v):
        """Ensure MCP server URL is properly formatted."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("MCP server URL must start with http:// or https://")
        return v


settings = Settings()