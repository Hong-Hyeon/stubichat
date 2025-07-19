from fastapi import APIRouter, HTTPException, Request, Depends, Body
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json
import uuid
from datetime import datetime

from app.models.chat import (
    ChatRequest, ChatResponse, ConversationState, HealthResponse,
    FrontendChatRequest, FrontendMessage, Message, MessageRole
)
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


def convert_frontend_message_to_backend(frontend_msg: FrontendMessage) -> Message:
    """Convert frontend message format to backend format."""
    # Extract content from parts
    content = ""
    for part in frontend_msg.parts:
        if isinstance(part, dict) and "text" in part:
            content += part["text"]
        elif isinstance(part, str):
            content += part
    
    return Message(
        role=MessageRole(frontend_msg.role),
        content=content,
        timestamp=datetime.utcnow()
    )


def map_model_name(frontend_model: str) -> str:
    """Map frontend model names to actual OpenAI model names."""
    model_mapping = {
        "chat-model": "gpt-3.5-turbo",
        "gpt-4": "gpt-4",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
        "gpt-4-turbo": "gpt-4-turbo-preview",
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini"
    }
    
    return model_mapping.get(frontend_model, "gpt-3.5-turbo")


@router.post("/", response_model=ChatResponse)
async def chat(
    http_request: Request,
    request: FrontendChatRequest = Body(..., embed=True),
    llm_client=Depends(get_llm_client),
    conversation_graph=Depends(get_conversation_graph)
):
    """Process a chat request using LangGraph workflow and return a response."""
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing frontend chat request for chat ID: {request.id}")
        
        # Convert frontend message to backend format
        backend_message = convert_frontend_message_to_backend(request.message)
        
        # Map frontend model name to actual OpenAI model name
        actual_model = map_model_name(request.selectedChatModel)
        
        # Create conversation state with the single message
        state = ConversationState(
            messages=[backend_message],
            session_id=request.id,
            metadata={
                "temperature": 0.7,
                "max_tokens": 1000,
                "model": actual_model,  # Use mapped model name
                "stream": True,
                "chat_id": request.id,
                "visibility": request.selectedVisibilityType,
                "user": request.user
            }
        )
        
        # Execute LangGraph workflow
        with log_performance(logger, "langgraph_conversation_workflow"):
            # Convert ConversationState to dictionary for LangGraph
            state_dict = {
                "messages": state.messages,
                "metadata": state.metadata,
                "session_id": state.session_id,
                "mcp_tools_needed": state.mcp_tools_needed,
                "mcp_tool_calls": state.mcp_tool_calls,
                "mcp_tools_available": state.mcp_tools_available
            }
            final_state = await conversation_graph.ainvoke(state_dict)
        
        # Extract the last assistant message as response
        messages = final_state.get("messages", [])
        
        if not messages:
            raise HTTPException(status_code=500, detail="No messages in final state from LangGraph workflow")
        
        # Find the last assistant message - handle both dict and object formats
        assistant_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("role") == "assistant":
                    assistant_messages.append(msg)
            else:
                # Handle Message objects
                if hasattr(msg, 'role') and msg.role == MessageRole.ASSISTANT:
                    assistant_messages.append({
                        "role": "assistant",
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
                    })
        
        if not assistant_messages:
            raise HTTPException(status_code=500, detail="No response generated from LangGraph workflow")
        
        last_assistant_message = assistant_messages[-1]
        
        # Extract MCP tool metadata from final state
        metadata = final_state.get("metadata", {})
        mcp_tools_used = metadata.get("mcp_tools_used", [])
        mcp_tools_failed = metadata.get("mcp_tools_failed", [])
        
        # Create response with MCP tool metadata
        response = ChatResponse(
            response=last_assistant_message.get("content", ""),
            model=request.selectedChatModel,
            usage=metadata.get("llm_usage"),
            finish_reason="stop",
            metadata=metadata,
            mcp_tools_used=mcp_tools_used if mcp_tools_used else None,
            mcp_tools_failed=mcp_tools_failed if mcp_tools_failed else None
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 200, duration)
        
        logger.info(f"Chat request processed successfully. Response length: {len(response.response)}")
        if mcp_tools_used:
            logger.info(f"MCP tools used: {mcp_tools_used}")
        if mcp_tools_failed:
            logger.warning(f"MCP tools failed: {mcp_tools_failed}")
        
        return response
        
    except Exception as e:
        logger.error(f"Chat request failed: {str(e)}")
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 500, duration)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(
    http_request: Request,
    request: FrontendChatRequest = Body(..., embed=True),
    llm_client=Depends(get_llm_client)
):
    """Process a chat request and stream the response directly from LLM agent."""
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing streaming chat request for chat ID: {request.id}")
        
        # Convert frontend message to backend format
        backend_message = convert_frontend_message_to_backend(request.message)
        
        # Map frontend model name to actual OpenAI model name
        actual_model = map_model_name(request.selectedChatModel)
        
        # Create backend request format
        backend_request = ChatRequest(
            messages=[backend_message],
            stream=True,
            temperature=0.7,
            max_tokens=1000,
            model=actual_model  # Use mapped model name
        )
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            try:
                # Stream directly from LLM agent service
                async for chunk in llm_client.stream_text(backend_request):
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