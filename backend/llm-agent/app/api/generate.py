from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json
from datetime import datetime

from app.models.requests import GenerateRequest, GenerateResponse, StreamChunk, HealthResponse
from app.services.openai_service import openai_service
from app.utils.logger import get_logger, log_performance, log_request_info
from app.core.config import settings

router = APIRouter(prefix="/generate", tags=["generate"])
logger = get_logger("generate_api")


@router.post("/", response_model=GenerateResponse)
async def generate_text(request: GenerateRequest, http_request: Request):
    """Generate text using OpenAI API."""
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing generate request with {len(request.messages)} messages")
        
        # Generate text using OpenAI service
        result = await openai_service.generate_text(
            messages=request.messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # Create response
        response = GenerateResponse(
            response=result["response"],
            model=result["model"],
            usage=result.get("usage"),
            finish_reason=result.get("finish_reason")
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 200, duration)
        
        return response
        
    except Exception as e:
        logger.error(f"Generate request failed: {str(e)}")
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 500, duration)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def generate_stream(request: GenerateRequest, http_request: Request):
    """Generate streaming text using OpenAI API."""
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing streaming generate request with {len(request.messages)} messages")
        
        async def generate_stream_response() -> AsyncGenerator[str, None]:
            try:
                # Stream from OpenAI service
                async for chunk in openai_service.stream_text(
                    messages=request.messages,
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ):
                    yield f"data: {chunk.model_dump_json()}\n\n"
                
                # Send end marker
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Streaming failed: {str(e)}")
                error_chunk = {
                    "content": "",
                    "finish_reason": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 200, duration)
        
        return StreamingResponse(
            generate_stream_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming generate request failed: {str(e)}")
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 500, duration)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check OpenAI service health
        openai_health = await openai_service.health_check()
        
        return HealthResponse(
            status=openai_health.get("status", "unknown"),
            openai_status=openai_health.get("openai_status"),
            version=settings.app_version
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            openai_status="disconnected",
            version=settings.app_version
        ) 