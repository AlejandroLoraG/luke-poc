from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MCP Server Configuration
    mcp_server_port: int = 8002
    server_name: str = "Workflow Management MCP Server"

    # svc-builder Integration
    svc_builder_url: str = "http://localhost:8000"
    svc_builder_timeout: int = 30

    # Application Configuration
    environment: str = "development"
    log_level: str = "INFO"

    model_config = {"extra": "ignore", "env_file": ".env"}


settings = Settings()