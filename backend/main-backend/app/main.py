from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import time
from datetime import datetime

from app.core.config import settings
from app.utils.logger import get_logger, log_request_info
from app.api.chat import router as chat_router


# Initialize logger
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("=== Stubichat Main Backend Starting Up ===")
    logger.info(f"App Name: {settings.app_name}")
    logger.info(f"Version: {settings.app_version}")
    logger.info(f"Debug Mode: {settings.debug}")
    logger.info(f"LLM Agent URL: {settings.llm_agent_url}")
    
    try:
        # Health check of LLM agent service
        from app.services.llm_client import llm_client
        health = await llm_client.health_check()
        logger.info(f"LLM Agent Health: {health.get('status', 'unknown')}")
    except Exception as e:
        logger.warning(f"LLM Agent health check failed: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("=== Stubichat Main Backend Shutting Down ===")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Main backend service for Stubichat with LangGraph orchestration",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware for production
    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
        )
    
    # Add request logging middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        log_request_info(logger, request.method, request.url.path, response.status_code, duration)
        
        return response
    
    # Add exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}")
        return HTTPException(status_code=500, detail="Internal server error")
    
    # Include routers
    app.include_router(chat_router)
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "message": "Stubichat Main Backend",
            "version": settings.app_version,
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }
    
    # Health check endpoint
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "service": "main-backend",
            "version": settings.app_version,
            "timestamp": datetime.now().isoformat()
        }
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 