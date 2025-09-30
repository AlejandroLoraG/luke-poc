from pydantic import Field, validator
from shared.config import BaseServiceSettings, ServicePorts, ServiceNames, NetworkConfig


class Settings(BaseServiceSettings):
    # MCP Server Configuration
    mcp_server_port: int = Field(
        default=ServicePorts.MCP_SERVER,
        description="Port for the MCP server"
    )
    server_name: str = Field(
        default="Workflow Management MCP Server",
        description="Human-readable server name"
    )

    # svc-builder Integration
    svc_builder_url: str = Field(
        default_factory=lambda: NetworkConfig.get_service_url(
            ServiceNames.SVC_BUILDER,
            ServicePorts.SVC_BUILDER,
            use_docker=False  # Default to localhost for development
        ),
        description="URL for the svc-builder service"
    )
    svc_builder_timeout: int = Field(
        default=30,
        description="Timeout for svc-builder connections in seconds"
    )

    @validator("svc_builder_url")
    def validate_svc_builder_url(cls, v):
        """Ensure svc-builder URL is properly formatted."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("svc-builder URL must start with http:// or https://")
        return v


settings = Settings()