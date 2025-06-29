from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any

from app.factory.model_factory import ModelFactory
from app.service.llm_service import LLMService
from app.routers.generate import GenerateRouter
from app.logger import (
    get_logger, 
    get_request_logger,
    log_request_info,
    log_exception,
    get_logging_stats,
    request_id_var
)

# Initialize logger for main module
logger = get_logger(__name__)

# Global variables for storing initialized components
model = None
llm_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("=== VLLM Server Starting Up ===")
    
    try:
        global model, llm_service
        
        # Initialize model
        logger.info("Initializing VLLM model...")
        start_time = time.time()
        model = ModelFactory.create_model()
        init_time = time.time() - start_time
        logger.info(f"Model initialized successfully in {init_time:.2f}s")
        
        # Initialize LLM service
        logger.info("Initializing LLM service...")
        llm_service = LLMService(model)
        logger.info("LLM service initialized successfully")
        
        # Log system information
        logger.info("=== System Information ===")
        logger.info(f"Model path: {model.llm_engine.model_config.model}")
        logger.info(f"Max model length: {model.llm_engine.model_config.max_model_len}")
        logger.info(f"Tensor parallel size: {model.llm_engine.parallel_config.tensor_parallel_size}")
        
        # Log logging system stats
        log_stats = get_logging_stats()
        logger.info(f"Logging system: {log_stats['total_loggers']} loggers initialized")
        logger.info(f"Log directory: {log_stats['log_directory']}")
        
        logger.info("=== VLLM Server Ready ===")
        
    except Exception as e:
        log_exception(logger, "Failed to initialize VLLM server", e)
        raise
    
    yield
    
    # Shutdown
    logger.info("=== VLLM Server Shutting Down ===")
    try:
        # Cleanup operations
        if llm_service:
            logger.info("Cleaning up LLM service...")
            # Add any cleanup logic here
            
        if model:
            logger.info("Cleaning up VLLM model...")
            # Add any cleanup logic here
            
        logger.info("VLLM server shutdown completed successfully")
        
    except Exception as e:
        log_exception(logger, "Error during shutdown", e)


def create_app() -> FastAPI:
    """Application factory with integrated logging"""
    logger.info("Creating VLLM Server FastAPI application")
    
    app = FastAPI(
        title="VLLM Server",
        description="High-performance text generation server with comprehensive logging",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add request logging middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        """Middleware for logging all HTTP requests and responses"""
        # Generate request ID
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        request_id_var.set(request_id)
        
        # Get request logger
        request_logger = get_request_logger(request_id)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get request body size (if available)
        body_size = None
        body_preview = None
        
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                body_size = len(body)
                
                # Create body preview (for logging)
                if body:
                    body_str = body.decode('utf-8', errors='ignore')
                    body_preview = body_str[:200] + "..." if len(body_str) > 200 else body_str
                    
                # Reset request body for downstream processing
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
                
            except Exception as e:
                request_logger.warning(f"Could not read request body: {e}")
        
        # Log incoming request
        log_request_info(
            request_logger,
            request.method,
            str(request.url.path),
            client_ip,
            body_size,
            body_preview
        )
        
        # Process request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log response
            duration = time.time() - start_time
            request_logger.info(
                f"Request completed: {response.status_code} | duration: {duration:.3f}s"
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            log_exception(request_logger, f"Request failed after {duration:.3f}s", e)
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "message": str(e)
                },
                headers={"X-Request-ID": request_id}
            )
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Enhanced health check endpoint with system information"""
        health_logger = get_logger("health")
        
        try:
            # Basic health check
            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "server": "vllm-server"
            }
            
            # Add model information if available
            if model:
                health_status.update({
                    "model_loaded": True,
                    "model_path": model.llm_engine.model_config.model,
                    "max_model_length": model.llm_engine.model_config.max_model_len
                })
            else:
                health_status.update({
                    "model_loaded": False
                })
            
            # Add logging system stats
            log_stats = get_logging_stats()
            health_status.update({
                "logging": {
                    "total_loggers": log_stats["total_loggers"],
                    "log_level": log_stats["current_level"],
                    "log_directory": log_stats["log_directory"]
                }
            })
            
            health_logger.debug("Health check completed successfully")
            return health_status
            
        except Exception as e:
            log_exception(health_logger, "Health check failed", e)
            raise HTTPException(status_code=500, detail="Health check failed")
    
    # Add logging stats endpoint
    @app.get("/logging/stats")
    async def logging_stats():
        """Get comprehensive logging system statistics"""
        stats_logger = get_logger("logging_stats") 
        
        try:
            stats = get_logging_stats()
            stats_logger.info("Logging statistics retrieved")
            return stats
            
        except Exception as e:
            log_exception(stats_logger, "Failed to get logging statistics", e)
            raise HTTPException(status_code=500, detail="Failed to get logging statistics")
    
    # Setup routers
    if llm_service:
        generate_router = GenerateRouter(llm_service)
        app.include_router(generate_router.router)
        logger.info("Generate router configured successfully")
    else:
        logger.warning("LLM service not initialized - generate router not configured")
    
    logger.info("VLLM Server FastAPI application created successfully")
    return app


# Create the FastAPI app instance
app = create_app()