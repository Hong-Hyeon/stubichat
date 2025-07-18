from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json
from datetime import datetime

from app.models.requests import GenerateRequest, GenerateResponse, StreamChunk, HealthResponse
from app.factory.service_factory import get_service_factory, ServiceFactory
from app.utils.logger import get_logger, log_performance, log_request_info
from app.core.config import settings

router = APIRouter(prefix="/generate", tags=["generate"])
logger = get_logger("generate_api")


def get_openai_service(service_factory: ServiceFactory = Depends(get_service_factory)):
    """Dependency to get OpenAI service from service factory."""
    return service_factory.openai_service


@router.post("/", response_model=GenerateResponse)
async def generate_text(
    request: GenerateRequest,
    http_request: Request,
    openai_service=Depends(get_openai_service)
):
    """Generate text using OpenAI API."""
    start_time = datetime.now()
    
    try:
        logger.info(f"Generating text with model {request.model}")
        
        # Generate text
        with log_performance(logger, f"OpenAI text generation with {request.model}"):
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
            usage=result["usage"],
            finish_reason=result["finish_reason"]
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 200, duration)
        
        return response
        
    except Exception as e:
        logger.error(f"Text generation failed: {str(e)}")
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 500, duration)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def generate_stream(
    request: GenerateRequest,
    http_request: Request,
    openai_service=Depends(get_openai_service)
):
    """Stream text generation using OpenAI API."""
    start_time = datetime.now()
    
    try:
        logger.info(f"Streaming text generation with model {request.model}")
        
        async def generate_stream_response() -> AsyncGenerator[str, None]:
            try:
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
                error_chunk = StreamChunk(
                    content="",
                    model=request.model,
                    finish_reason="error"
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
        
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
        logger.error(f"Streaming generation failed: {str(e)}")
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 500, duration)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check(openai_service=Depends(get_openai_service)):
    """Health check endpoint."""
    try:
        # Check OpenAI service health
        health = await openai_service.health_check()
        
        services_status = {
            "openai": health.get("status", "unknown")
        }
        
        # Determine overall status
        overall_status = "healthy" if all(
            status == "healthy" for status in services_status.values()
        ) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            services=services_status,
            version=settings.app_version
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            services={"openai": "unhealthy"},
            version=settings.app_version
        ) 