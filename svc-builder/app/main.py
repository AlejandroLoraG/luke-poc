import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .core.settings import settings
from .core.sample_loader import load_sample_workflows
from .core.error_handlers import global_exception_handler, http_exception_handler
from .api.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    try:
        results = load_sample_workflows()
        loaded_count = sum(1 for success in results.values() if success)
        print(f"Loaded {loaded_count}/{len(results)} sample workflows")
        for workflow_id, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {workflow_id}")
    except Exception as e:
        print(f"Error loading sample workflows: {e}")

    yield

    # Shutdown (if needed)
    print("svc-builder shutting down...")


# Create FastAPI application
app = FastAPI(
    title="svc-builder",
    description="Workflow JSON DSL Configuration Management Service",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add error handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# Include routers
app.include_router(router)


@app.get("/")
async def root():
    return {
        "service": "svc-builder",
        "description": "Workflow JSON DSL Configuration Management",
        "version": "0.1.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )