from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json
import uuid
from datetime import datetime

from app.models.chat import ChatRequest, ChatResponse, ConversationState, HealthResponse
from app.core.graph import conversation_graph
from app.factory.service_factory import get_service_factory, ServiceFactory
from app.utils.logger import get_logger, log_performance, log_request_info
from app.core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger("chat_api")


def get_llm_client(service_factory: ServiceFactory = Depends(get_service_factory)):
    """Dependency to get LLM client from service factory."""
    return service_factory.llm_client


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    llm_client=Depends(get_llm_client)
):
    """Process a chat request and return a response."""
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing chat request with {len(request.messages)} messages")
        
        # Create conversation state
        state = ConversationState(
            messages=request.messages,
            session_id=str(uuid.uuid4()),
            metadata={
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "model": request.model
            }
        )
        
        # Execute conversation graph
        with log_performance(logger, "conversation_graph_execution"):
            final_state = await conversation_graph.ainvoke(state)
        
        # Extract response
        if final_state.messages and final_state.messages[-1].role.value == "assistant":
            response_content = final_state.messages[-1].content
        else:
            raise HTTPException(status_code=500, detail="No response generated")
        
        # Create response
        response = ChatResponse(
            response=response_content,
            model=request.model,
            usage=final_state.metadata.get("llm_response", {}).get("usage"),
            finish_reason="stop"
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 200, duration)
        
        return response
        
    except Exception as e:
        logger.error(f"Chat request failed: {str(e)}")
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 500, duration)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    http_request: Request,
    llm_client=Depends(get_llm_client)
):
    """Process a chat request and stream the response."""
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing streaming chat request with {len(request.messages)} messages")
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            try:
                # Stream from LLM agent service
                async for chunk in llm_client.stream_text(request):
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
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming chat request failed: {str(e)}")
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 500, duration)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check(llm_client=Depends(get_llm_client)):
    """Health check endpoint."""
    try:
        # Check LLM agent service health
        llm_health = await llm_client.health_check()
        
        services_status = {
            "llm_agent": llm_health.get("status", "unknown")
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
            services={"llm_agent": "unhealthy"},
            version=settings.app_version
        ) 