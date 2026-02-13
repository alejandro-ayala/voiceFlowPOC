"""
VoiceFlow PoC Web UI - Main FastAPI Application
Implements SOLID principles for scalable demo interface.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from application.api.v1 import audio, chat, health
from application.models.responses import ErrorResponse, StatusEnum
from integration.configuration.settings import get_cors_config, get_settings
from shared.exceptions.exceptions import EXCEPTION_STATUS_CODES, VoiceFlowException
from shared.utils.dependencies import initialize_services

# Configure structured logging
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout if "sys" in globals() else None,
    level=logging.INFO,
)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting VoiceFlow PoC Web UI")
    settings = get_settings()
    logger.info(
        "Configuration loaded",
        app_name=settings.app_name,
        version=settings.version,
        debug=settings.debug,
    )

    # Initialize all services
    logger.info("Initializing services...")
    await initialize_services()
    logger.info("All services initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down VoiceFlow PoC Web UI")


def create_application() -> FastAPI:
    """
    Application factory following SOLID principles.
    Allows easy testing and configuration.
    """
    settings = get_settings()

    # Create FastAPI application
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )

    # Add CORS middleware
    cors_config = get_cors_config()
    app.add_middleware(CORSMiddleware, **cors_config)

    # Add API routes
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(audio.router, prefix="/api/v1", tags=["audio"])
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])

    # Setup static files and templates
    static_path = Path(__file__).parent / "static"
    templates_path = Path(__file__).parent / "templates"

    if static_path.exists():
        app.mount("/static", StaticFiles(directory=static_path), name="static")

    templates = Jinja2Templates(directory=templates_path)

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        """Serve main application page"""
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "app_name": settings.app_name,
                "app_description": settings.app_description,
                "version": settings.version,
                "debug": settings.debug,
            },
        )

    # Global exception handler
    @app.exception_handler(VoiceFlowException)
    async def voiceflow_exception_handler(request: Request, exc: VoiceFlowException):
        """Handle custom VoiceFlow exceptions"""
        status_code = EXCEPTION_STATUS_CODES.get(type(exc), 500)

        logger.error(
            "VoiceFlow exception occurred",
            exception_type=type(exc).__name__,
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
        )

        return JSONResponse(
            status_code=status_code,
            content=ErrorResponse(
                status=StatusEnum.ERROR,
                message=exc.message,
                error_code=exc.error_code,
                details=exc.details,
            ).dict(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions"""
        logger.error(
            "Unexpected exception occurred",
            exception_type=type(exc).__name__,
            message=str(exc),
        )

        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                status=StatusEnum.ERROR,
                message="Internal server error" if not settings.debug else str(exc),
                error_code="INTERNAL_ERROR",
            ).dict(),
        )

    return app


# Create application instance
app = create_application()


def main():
    """
    Main entry point for the application.
    Used by run-ui.py script.
    """
    settings = get_settings()

    logger.info(
        "Starting VoiceFlow PoC Web UI Server",
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
    )

    uvicorn.run(
        "presentation.fastapi_factory:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.debug,
        log_level="info" if not settings.debug else "debug",
    )


if __name__ == "__main__":
    main()
