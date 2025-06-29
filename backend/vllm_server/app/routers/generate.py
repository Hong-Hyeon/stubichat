from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from vllm import SamplingParams
import time
import traceback

from app.service.llm_service import LLMService
from app.config.base import settings
from app.logger import (
    get_logger,
    get_request_logger,
    log_exception,
    log_request_info,
    request_id_var
)

# Initialize logger for generate router
logger = get_logger(__name__)

router = APIRouter()


class GenerateRequest(BaseModel):
    """Request model for text generation with validation and logging support."""
    prompt: str
    max_tokens: Optional[int] = settings.MAX_TOKENS
    temperature: Optional[float] = settings.TEMPERATURE
    top_p: Optional[float] = settings.TOP_P
    stop: Optional[List[str]] = None
    stream: Optional[bool] = False
    
    def log_summary(self) -> str:
        """Create a summary of the request for logging purposes."""
        return (f"prompt_length={len(self.prompt)}, max_tokens={self.max_tokens}, "
                f"temperature={self.temperature}, top_p={self.top_p}, "
                f"stream={self.stream}, stop={len(self.stop) if self.stop else 0}")


class GenerateResponse(BaseModel):
    """Response model for text generation."""
    text: str
    usage: dict


class GenerateRouter:
    """Router class for text generation endpoints with comprehensive logging."""
    
    def __init__(self, llm_service: LLMService):
        """
        Initialize the generate router with LLM service.
        
        Args:
            llm_service: The LLM service instance for text generation
        """
        self.llm_service = llm_service
        self.router = APIRouter()
        self.setup_routes()
        logger.info("Generate router initialized successfully")

    def setup_routes(self):
        """Setup the API routes with comprehensive logging."""
        
        @self.router.post("/generate", response_model=GenerateResponse)
        async def generate_text(request: GenerateRequest, http_request: Request):
            """
            Text generation endpoint with comprehensive logging and error handling.
            
            Args:
                request: The generation request parameters
                http_request: FastAPI HTTP request object for logging
                
            Returns:
                Generated text response or streaming response
            """
            # Get request logger (request ID is set by middleware)
            request_id = request_id_var.get() or 'no-req'
            gen_logger = get_request_logger(request_id)
            
            # Log incoming request details
            gen_logger.info("=== Generate Request Received ===")
            gen_logger.info(f"Request parameters: {request.log_summary()}")
            gen_logger.debug(f"Prompt preview: {request.prompt[:200]}..." 
                           if len(request.prompt) > 200 else f"Full prompt: {request.prompt}")
            
            try:
                # Validate request parameters
                if not request.prompt or not request.prompt.strip():
                    gen_logger.warning("Empty prompt received")
                    raise HTTPException(status_code=400, detail="Prompt cannot be empty")
                
                if request.max_tokens and request.max_tokens <= 0:
                    gen_logger.warning(f"Invalid max_tokens: {request.max_tokens}")
                    raise HTTPException(status_code=400, detail="max_tokens must be positive")
                
                if request.temperature and (request.temperature < 0 or request.temperature > 2):
                    gen_logger.warning(f"Invalid temperature: {request.temperature}")
                    raise HTTPException(status_code=400, detail="temperature must be between 0 and 2")
                
                if request.top_p and (request.top_p <= 0 or request.top_p > 1):
                    gen_logger.warning(f"Invalid top_p: {request.top_p}")
                    raise HTTPException(status_code=400, detail="top_p must be between 0 and 1")
                
                gen_logger.info("Request validation passed")
                
                # Create sampling parameters
                sampling_params = SamplingParams(
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens,
                    stop=request.stop or []
                )
                
                gen_logger.debug(f"Sampling parameters created: {sampling_params}")
                
                # Handle streaming vs non-streaming
                if request.stream:
                    gen_logger.info("Processing streaming generation request")
                    
                    # Return streaming response
                    return StreamingResponse(
                        self.llm_service.generate_stream(request.prompt, sampling_params),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "X-Request-ID": request_id
                        }
                    )
                else:
                    gen_logger.info("Processing standard generation request")
                    
                    # Call LLM service for standard generation
                    start_time = time.time()
                    result = self.llm_service.generate(request.prompt, sampling_params)
                    generation_time = time.time() - start_time
                    
                    # Check for errors in result
                    if "error" in result:
                        gen_logger.error(f"LLM service returned error: {result['error']}")
                        raise HTTPException(status_code=500, detail=result["error"])
                    
                    # Log successful generation
                    gen_logger.info(f"Generation completed successfully in {generation_time:.3f}s")
                    gen_logger.info(f"Generated {result['usage']['completion_tokens']} tokens")
                    gen_logger.debug(f"Output preview: {result['text'][:200]}..." 
                                   if len(result['text']) > 200 else f"Full output: {result['text']}")
                    
                    # Create response
                    response = GenerateResponse(**result)
                    gen_logger.info("=== Generate Request Completed Successfully ===")
                    
                    return response
                
            except HTTPException as he:
                # Re-raise HTTP exceptions (already logged above)
                raise he
                
            except Exception as e:
                # Log unexpected errors
                log_exception(gen_logger, "Unexpected error in generate endpoint", e)
                gen_logger.error("=== Generate Request Failed ===")
                
                raise HTTPException(
                    status_code=500, 
                    detail={
                        "error": "Internal server error during text generation",
                        "request_id": request_id,
                        "message": str(e)
                    }
                )

        @self.router.get("/health")
        async def health_check():
            """
            Health check endpoint for the generate router and LLM service.
            
            Returns:
                Health status information
            """
            health_logger = get_logger("generate_health")
            
            try:
                health_logger.debug("Performing generate router health check")
                
                # Basic router health
                health_status = {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "component": "generate_router"
                }
                
                # Check LLM service health
                if self.llm_service:
                    llm_health = self.llm_service.health_check()
                    health_status["llm_service"] = llm_health
                    
                    if llm_health.get("status") != "healthy":
                        health_status["status"] = "degraded"
                        health_logger.warning("LLM service health check failed")
                else:
                    health_status["llm_service"] = {"status": "not_available"}
                    health_status["status"] = "unhealthy"
                    health_logger.error("LLM service not available")
                
                health_logger.debug(f"Generate router health check: {health_status['status']}")
                return health_status
                
            except Exception as e:
                log_exception(health_logger, "Generate router health check failed", e)
                return {
                    "status": "error",
                    "error": str(e),
                    "timestamp": time.time(),
                    "component": "generate_router"
                }

        @self.router.get("/model/info")
        async def model_info():
            """
            Get detailed model information endpoint.
            
            Returns:
                Model configuration and status information
            """
            info_logger = get_logger("model_info_endpoint")
            
            try:
                info_logger.debug("Retrieving model information via API")
                
                if not self.llm_service:
                    info_logger.error("LLM service not available")
                    raise HTTPException(status_code=503, detail="LLM service not available")
                
                # Get model info from LLM service
                model_info = self.llm_service.get_model_info()
                
                if model_info.get("status") == "error":
                    info_logger.error(f"Failed to get model info: {model_info.get('error')}")
                    raise HTTPException(status_code=500, detail="Failed to retrieve model information")
                
                info_logger.debug("Model information retrieved successfully")
                return model_info
                
            except HTTPException as he:
                raise he
                
            except Exception as e:
                log_exception(info_logger, "Model info endpoint failed", e)
                raise HTTPException(status_code=500, detail="Failed to retrieve model information")

        @self.router.get("/stats")
        async def generation_stats():
            """
            Get generation statistics and performance metrics endpoint.
            
            Returns:
                Generation statistics and system metrics
            """
            stats_logger = get_logger("generation_stats")
            
            try:
                stats_logger.debug("Retrieving generation statistics")
                
                # Basic statistics
                stats = {
                    "timestamp": time.time(),
                    "component": "generate_router",
                    "status": "active"
                }
                
                # Add model info if available
                if self.llm_service:
                    model_info = self.llm_service.get_model_info()
                    if model_info.get("status") == "loaded":
                        stats["model"] = {
                            "name": model_info.get("model_name"),
                            "max_length": model_info.get("max_model_length"),
                            "parallel_size": model_info.get("tensor_parallel_size")
                        }
                    
                    # Add service health
                    health = self.llm_service.health_check()
                    stats["service_health"] = health.get("status")
                else:
                    stats["model"] = {"status": "not_available"}
                    stats["service_health"] = "not_available"
                
                stats_logger.debug("Generation statistics retrieved successfully")
                return stats
                
            except Exception as e:
                log_exception(stats_logger, "Failed to get generation statistics", e)
                raise HTTPException(status_code=500, detail="Failed to retrieve statistics")

        logger.info("Generate router routes configured successfully")
        logger.info("Available endpoints: /generate, /health, /model/info, /stats") 