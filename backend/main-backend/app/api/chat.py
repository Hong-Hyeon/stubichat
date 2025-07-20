from fastapi import APIRouter, HTTPException, Request, Depends, Body
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json
import uuid
from datetime import datetime

from app.models.chat import (
    ChatRequest, ChatResponse, ConversationState, HealthResponse,
    FrontendChatRequest, FrontendMessage, Message, MessageRole,
    SimpleChatRequest, SimpleChatResponse, HealthTestResponse,
    SimplePromptRequest, SimplePromptResponse, SimpleHealthResponse
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


# 매우 단순한 채팅 엔드포인트 - 사용자 프롬프트만 받음
@router.post("/", response_model=SimplePromptResponse)
async def chat(
    http_request: Request,
    llm_client=Depends(get_llm_client),
    conversation_graph=Depends(get_conversation_graph)
):
    """매우 단순한 채팅 요청 처리 - 사용자 프롬프트만 받아서 응답"""
    start_time = datetime.now()
    
    try:
        # JSON 직접 파싱
        body = await http_request.json()
        prompt = body.get("prompt", "")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")
        
        logger.info(f"Processing simple chat request with prompt: {prompt[:50]}...")
        
        # 사용자 메시지 생성
        user_message = Message(
            role=MessageRole.USER,
            content=prompt,
            timestamp=datetime.utcnow()
        )
        
        # 기본 모델 사용 (사용자가 선택할 필요 없음)
        default_model = "gpt-3.5-turbo"
        
        # 세션 ID 생성
        session_id = str(uuid.uuid4())
        
        # 대화 상태 생성
        state = ConversationState(
            messages=[user_message],
            session_id=session_id,
            metadata={
                "temperature": 0.7,
                "max_tokens": 1000,
                "model": default_model,
                "stream": False,
                "chat_id": session_id,
                "visibility": "private",
                "user": {"id": "simple-user", "type": "guest"}
            }
        )
        
        # LangGraph 워크플로우 실행
        with log_performance(logger, "simple_langgraph_conversation_workflow"):
            state_dict = {
                "messages": state.messages,
                "metadata": state.metadata,
                "session_id": state.session_id,
                "mcp_tools_needed": state.mcp_tools_needed,
                "mcp_tool_calls": state.mcp_tool_calls,
                "mcp_tools_available": state.mcp_tools_available
            }
            final_state = await conversation_graph.ainvoke(state_dict)
        
        # 응답 추출
        messages = final_state.get("messages", [])
        
        if not messages:
            raise HTTPException(status_code=500, detail="No messages in final state from LangGraph workflow")
        
        # 마지막 어시스턴트 메시지 찾기
        assistant_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("role") == "assistant":
                    assistant_messages.append(msg)
            else:
                if hasattr(msg, 'role') and msg.role == MessageRole.ASSISTANT:
                    assistant_messages.append({
                        "role": "assistant",
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
                    })
        
        if not assistant_messages:
            raise HTTPException(status_code=500, detail="No response generated from LangGraph workflow")
        
        last_assistant_message = assistant_messages[-1]
        
        # 응답 생성
        response = SimplePromptResponse(
            response=last_assistant_message.get("content", ""),
            success=True
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 200, duration)
        
        logger.info(f"Simple chat request processed successfully. Response length: {len(response.response)}")
        
        return response
        
    except Exception as e:
        logger.error(f"Simple chat request failed: {str(e)}")
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 500, duration)
        raise HTTPException(status_code=500, detail=str(e))


# 매우 단순한 스트리밍 엔드포인트 - 사용자 프롬프트만 받음
@router.post("/stream")
async def chat_stream(
    http_request: Request,
    llm_client=Depends(get_llm_client)
):
    """매우 단순한 스트리밍 채팅 요청 처리 - 사용자 프롬프트만 받음"""
    start_time = datetime.now()
    
    try:
        # JSON 직접 파싱
        body = await http_request.json()
        prompt = body.get("prompt", "")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")
        
        logger.info(f"Processing simple streaming chat request with prompt: {prompt[:50]}...")
        
        # 사용자 메시지 생성
        user_message = Message(
            role=MessageRole.USER,
            content=prompt,
            timestamp=datetime.utcnow()
        )
        
        # 기본 모델 사용 (사용자가 선택할 필요 없음)
        default_model = "gpt-3.5-turbo"
        
        # 백엔드 요청 형식 생성
        backend_request = ChatRequest(
            messages=[user_message],
            stream=True,
            temperature=0.7,
            max_tokens=1000,
            model=default_model
        )
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            try:
                # LLM 에이전트 서비스에서 직접 스트리밍
                async for chunk in llm_client.stream_text(backend_request):
                    yield f"data: {chunk.model_dump_json()}\n\n"
                
                # 종료 마커
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Simple streaming failed: {str(e)}")
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
        logger.error(f"Simple streaming chat request failed: {str(e)}")
        duration = (datetime.now() - start_time).total_seconds()
        log_request_info(logger, http_request.method, http_request.url.path, 500, duration)
        raise HTTPException(status_code=500, detail=str(e))


# 매우 단순한 헬스 체크 엔드포인트
@router.get("/health", response_model=SimpleHealthResponse)
async def health_check(
    llm_client=Depends(get_llm_client),
    conversation_graph=Depends(get_conversation_graph)
):
    """매우 단순한 헬스 체크 엔드포인트 - 내부적으로 테스트 프롬프트를 모델에 전송"""
    try:
        logger.info("Starting simple health check with model test")
        
        # LLM 에이전트 서비스 헬스 체크
        await llm_client.health_check()
        
        # 테스트 프롬프트로 모델 응답 확인
        test_prompt = "Hello, this is a health check. Please respond with 'Health check successful'."
        test_message = Message(
            role=MessageRole.USER,
            content=test_prompt,
            timestamp=datetime.utcnow()
        )
        
        # 간단한 테스트를 위해 직접 LLM 에이전트 호출
        test_request = ChatRequest(
            messages=[test_message],
            stream=False,
            temperature=0.7,
            max_tokens=50,
            model="gpt-3.5-turbo"
        )
        
        try:
            await llm_client.generate_text(test_request)
            # 응답이 성공적으로 왔으면 Healthy
            return SimpleHealthResponse(
                status="Healthy",
                message="Health check successful"
            )
        except Exception as model_error:
            logger.warning(f"Model test failed: {str(model_error)}")
            return SimpleHealthResponse(
                status="Unhealthy",
                message="Health check failed"
            )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return SimpleHealthResponse(
            status="Unhealthy",
            message="Health check failed"
        ) 