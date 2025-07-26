from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import time
from datetime import datetime
from typing import Optional

from app.core.config import Settings
from app.utils.logger import get_logger, log_request_info
from app.api.chat import router as chat_router
from app.api.mcp_tools import router as mcp_tools_router
from app.api.auth import router as auth_router


class AppFactory:
    """Factory for creating FastAPI application instances."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("app_factory")
    
    def create_lifespan(self):
        """Create application lifespan manager."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan manager for startup and shutdown events."""
            # Startup
            self.logger.info("=== Stubichat Main Backend Starting Up ===")
            self.logger.info(f"App Name: {self.settings.app_name}")
            self.logger.info(f"Version: {self.settings.app_version}")
            self.logger.info(f"Debug Mode: {self.settings.debug}")
            self.logger.info(f"LLM Agent URL: {self.settings.llm_agent_url}")
            
            try:
                # Health check of LLM agent service
                from app.services.llm_client import llm_client
                health = await llm_client.health_check()
                self.logger.info(f"LLM Agent Health: {health.get('status', 'unknown')}")
            except Exception as e:
                self.logger.warning(f"LLM Agent health check failed: {str(e)}")
            
            try:
                # Initialize database
                from app.core.database import init_db
                await init_db()
                self.logger.info("Database initialized successfully")
            except Exception as e:
                self.logger.error(f"Database initialization failed: {str(e)}")
                raise
            
            yield
            
            # Shutdown
            try:
                # Close database connections
                from app.core.database import close_db
                await close_db()
                self.logger.info("Database connections closed")
            except Exception as e:
                self.logger.error(f"Database shutdown failed: {str(e)}")
            
            self.logger.info("=== Stubichat Main Backend Shutting Down ===")
        
        return lifespan
    
    def create_middleware(self, app: FastAPI):
        """Add middleware to the FastAPI application."""
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add trusted host middleware for production
        if not self.settings.debug:
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
            )
        
        # Add request logging middleware
        @app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            start_time = time.time()
            
            # Log request
            self.logger.info(f"Request: {request.method} {request.url.path}")
            
            # Process request
            response = await call_next(request)
            
            # Log response
            duration = time.time() - start_time
            log_request_info(self.logger, request.method, request.url.path, response.status_code, duration)
            
            return response
    
    def create_exception_handlers(self, app: FastAPI):
        """Add exception handlers to the FastAPI application."""
        
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            self.logger.error(f"Unhandled exception: {str(exc)}")
            return HTTPException(status_code=500, detail="Internal server error")
    
    def create_routes(self, app: FastAPI):
        """Add routes to the FastAPI application."""
        
        # Include routers
        app.include_router(chat_router)
        app.include_router(mcp_tools_router)
        app.include_router(auth_router)
        
        # Root endpoint
        @app.get("/")
        async def root():
            return {
                "message": self.settings.app_name,
                "version": self.settings.app_version,
                "status": "running",
                "timestamp": datetime.now().isoformat()
            }
        
        # Health check endpoint
        @app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "service": "main-backend",
                "version": self.settings.app_version,
                "timestamp": datetime.now().isoformat()
            }
    
    def create_app(self, settings: Optional[Settings] = None) -> FastAPI:
        """Create and configure the FastAPI application."""
        
        if settings is None:
            settings = self.settings
        
        app = FastAPI(
            title=settings.app_name,
            version=settings.app_version,
            description="Main backend service for Stubichat with LangGraph orchestration",
            docs_url="/docs" if settings.debug else None,
            redoc_url="/redoc" if settings.debug else None,
            lifespan=self.create_lifespan()
        )
        
        # Add middleware
        self.create_middleware(app)
        
        # Add exception handlers
        self.create_exception_handlers(app)
        
        # Add routes
        self.create_routes(app)
        
        return app


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Factory function to create FastAPI application."""
    from app.core.config import get_settings
    
    if settings is None:
        settings = get_settings()
    
    factory = AppFactory(settings)
    return factory.create_app(settings) 