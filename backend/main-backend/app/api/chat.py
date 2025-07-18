from fastapi import APIRouter, HTTPException, Request, Depends, Body
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json
import uuid
from datetime import datetime

from app.models.chat import ChatRequest, ChatResponse, ConversationState, HealthResponse
from app.factory.service_factory import get_service_factory, ServiceFactory
from app.utils.logger import get_logger, log_performance, log_request_info
from app.core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger("chat_api")


def get_llm_client(service_factory: ServiceFactory = Depends(get_service_factory)):
    """Dependency to get LLM client from service factory."""
    return service_factory.llm_client


def get_conversation_graph(service_factory: ServiceFactory = Depends(get_service_factory)):
    """Dependency to get conversation graph from service factory."""
    return service_factory.conversation_graph


@router.post("/", response_model=ChatResponse)
async def chat(
    http_request: Request,
    request: ChatRequest = Body(..., embed=True),
    llm_client=Depends(get_llm_client),
    conversation_graph=Depends(get_conversation_graph)
):
    """Process a chat request using LangGraph workflow and return a response."""
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
                "model": request.model,
                "stream": request.stream
            }
        )
        
        # Execute LangGraph workflow
        with log_performance(logger, "langgraph_conversation_workflow"):
            # Convert ConversationState to dictionary for LangGraph
            state_dict = {
                "messages": state.messages,
                "metadata": state.metadata,
                "session_id": state.session_id
            }
            final_state = await conversation_graph.ainvoke(state_dict)
        
        # Extract the last assistant message as response
        # final_state is now a dictionary, not a ConversationState object
        messages = final_state.get("messages", [])
        if not messages:
            raise HTTPException(status_code=500, detail="No messages in final state from LangGraph workflow")
        
        # Find the last assistant message
        assistant_messages = [msg for msg in messages if msg.get("role") == "assistant"]
        if not assistant_messages:
            raise HTTPException(status_code=500, detail="No response generated from LangGraph workflow")
        
        last_assistant_message = assistant_messages[-1]
        
        # Create response
        response = ChatResponse(
            response=last_assistant_message.get("content", ""),
            model=request.model,
            usage=final_state.get("metadata", {}).get("usage"),
            finish_reason="stop"
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 200, duration)
        
        logger.info(f"Chat request processed successfully. Response length: {len(response.response)}")
        
        return response
        
    except Exception as e:
        logger.error(f"Chat request failed: {str(e)}")
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 500, duration)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(
    http_request: Request,
    request: ChatRequest = Body(..., embed=True),
    llm_client=Depends(get_llm_client)
):
    """Process a chat request and stream the response directly from LLM agent."""
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing streaming chat request with {len(request.messages)} messages")
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            try:
                # Stream directly from LLM agent service
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