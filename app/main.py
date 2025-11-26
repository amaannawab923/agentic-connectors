"""FastAPI application for connector generation."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Connector Generator API...")

    settings = Settings()
    logger.info(f"Max budget per connector: ${settings.max_budget:.2f}")
    logger.info(f"Max test retries: {settings.max_test_retries}")
    logger.info(f"Max review cycles: {settings.max_review_cycles}")
    logger.info(f"Using model: {settings.claude_model}")

    yield

    # Shutdown
    logger.info("Shutting down Connector Generator API...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = Settings()

    app = FastAPI(
        title="Connector Generator API",
        description="""
AI-powered connector generation platform using Claude Agent SDK.

## Features

- **Research Agent**: Gathers implementation patterns from GitHub and documentation
- **Generator Agent**: Creates production-ready connector code
- **Tester Agent**: Validates generated code with syntax, import, and runtime tests
- **Reviewer Agent**: Performs comprehensive code review
- **Publisher Agent**: Commits and creates PRs on GitHub

## Pipeline Flow

1. **Research** → Gather best practices ($0.60)
2. **Generate** → Create connector code ($0.80)
3. **Test** → Validate code works ($0.10)
4. **Fix** → Fix failures (up to 3 times)
5. **Review** → Code quality check ($0.13)
6. **Improve** → Address feedback (up to 2 times)
7. **Publish** → Push to GitHub

## Budget Control

- Maximum budget: $7.00 per connector
- Warning threshold: $5.00
- Force publish threshold: $6.00
        """,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router)

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "Connector Generator API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=["output/*", "*.pyc", "__pycache__", ".pytest_cache"],
        log_level="info",
    )
