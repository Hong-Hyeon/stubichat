from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi_mcp import FastApiMCP
from contextlib import asynccontextmanager
import time
from datetime import datetime
from typing import Optional

from app.core.config import Settings
from app.utils.logger import get_logger, log_request_info


class AppFactory:
    """Factory for creating FastAPI application instances with MCP integration."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("app_factory")
    
    def create_lifespan(self):
        """Create application lifespan manager."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan manager for startup and shutdown events."""
            # Startup
            self.logger.info("=== Stubichat MCP Server Starting Up ===")
            self.logger.info(f"App Name: {self.settings.app_name}")
            self.logger.info(f"Version: {self.settings.app_version}")
            self.logger.info(f"Debug Mode: {self.settings.debug}")
            self.logger.info(f"MCP Server Name: {self.settings.mcp_server_name}")
            self.logger.info(f"MCP Server Version: {self.settings.mcp_server_version}")
            
            yield
            
            # Shutdown
            self.logger.info("=== Stubichat MCP Server Shutting Down ===")
        
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
        
        # Import and include routers
        from app.tools import echo_router, web_search_router
        app.include_router(echo_router)
        app.include_router(web_search_router)
        
        # Root endpoint
        @app.get("/")
        async def root():
            return {
                "message": self.settings.app_name,
                "version": self.settings.app_version,
                "mcp_server": self.settings.mcp_server_name,
                "mcp_version": self.settings.mcp_server_version,
                "status": "running",
                "timestamp": datetime.now().isoformat()
            }
        
        # Health check endpoint
        @app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "service": "mcp-server",
                "version": self.settings.app_version,
                "mcp_server": self.settings.mcp_server_name,
                "timestamp": datetime.now().isoformat()
            }
    
    def create_mcp_server(self, app: FastAPI):
        """Create and mount the MCP server to the FastAPI application."""
        try:
            # Create FastApiMCP instance
            mcp = FastApiMCP(
                app,
                name=self.settings.mcp_server_name,
                description=self.settings.mcp_server_description
            )
            
            # Mount the MCP server
            mcp.mount()
            
            self.logger.info("MCP server mounted successfully at /mcp")
            
        except Exception as e:
            self.logger.error(f"Failed to create MCP server: {str(e)}")
            raise
    
    def create_app(self, settings: Optional[Settings] = None) -> FastAPI:
        """Create and configure the FastAPI application with MCP integration."""
        
        if settings is None:
            settings = self.settings
        
        app = FastAPI(
            title=settings.app_name,
            version=settings.app_version,
            description=settings.mcp_server_description,
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
        
        # Create and mount MCP server
        self.create_mcp_server(app)
        
        return app


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Factory function to create FastAPI application with MCP integration."""
    from app.core.config import get_settings
    
    if settings is None:
        settings = get_settings()
    
    factory = AppFactory(settings)
    return factory.create_app(settings) 