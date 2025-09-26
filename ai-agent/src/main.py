import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api.chat_router import router as chat_router
from .api.workflow_router import router as workflow_router

# Create FastAPI application
app = FastAPI(
    title="Workflow AI Agent",
    description="AI Agent for natural workflow conversations with MCP integration",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(workflow_router)


@app.get("/")
async def root():
    return {
        "message": "Workflow AI Agent API",
        "version": "0.1.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.ai_agent_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )