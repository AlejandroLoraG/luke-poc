from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # AI Agent Configuration
    google_api_key: str = "AIzaSyCFl2hfT-ZoWK-jSsrDw_Q9YGLycKdRblA"
    ai_agent_port: int = 8001
    ai_model: str = "gemini-2.5-flash-lite"

    # MCP Client Configuration
    mcp_server_url: str = "http://localhost:8002"
    mcp_connection_timeout: int = 30

    # Conversation Management
    max_conversation_length: int = 15

    # Environment
    environment: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()