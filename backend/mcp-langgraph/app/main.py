from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, AsyncGenerator, Literal
from app.core.graph import MCPGraph
from app.tools import available_tools
import json
import asyncio

# Use centralized logging system
from app.logger import get_logger, get_performance_logger, log_exception

# Initialize logger for main application
logger = get_logger(__name__)

app = FastAPI()

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    stream: Optional[bool] = True

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "role": "user",
                        "content": "파일의 내용을 읽어와줘"
                    }
                ],
                "stream": True
            }
        }

async def stream_chat_response(mcp: MCPGraph, state: Dict) -> AsyncGenerator[str, None]:
    """채팅 응답을 스트리밍으로 반환"""
    try:
        logger.debug("Starting chat response streaming")
        chunk_count = 0
        
        async for chunk in mcp.astream(state):
            chunk_count += 1
            logger.debug(f"Processing chunk {chunk_count}: {list(chunk.keys())}")
            
            if "response" in chunk and chunk.get("streaming"):
                # 스트리밍이 필요한 응답은 문장 단위로 나누어 전송
                sentences = chunk["response"].split(". ")
                for sentence in sentences:
                    if sentence.strip():
                        yield f"data: {json.dumps({'text': sentence.strip() + '.'}, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.1)
                        
            elif "response" in chunk:
                # 일반 응답은 그대로 전송
                response_data = {'text': chunk['response']}
                yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                logger.debug(f"Sent response chunk of length: {len(chunk['response'])}")
                
            elif "error" in chunk:
                error_data = {'error': chunk['error']}
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                logger.warning(f"Sent error chunk: {chunk['error']}")
                
        logger.info(f"Completed streaming response with {chunk_count} chunks")
        
    except Exception as e:
        log_exception(logger, "Error in stream_chat_response", e)
        error_data = {'error': str(e)}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    finally:
        yield "data: [DONE]\n\n"
        logger.debug("Streaming response completed")


@app.post("/chat")
async def chat(request: ChatRequest):
    """채팅 엔드포인트"""
    try:
        # Log request details (excluding sensitive content)
        logger.info(f"Received chat request with {len(request.messages)} messages, streaming: {request.stream}")
        if request.messages:
            last_msg = request.messages[-1]
            msg_preview = last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content
            logger.debug(f"Last message ({last_msg.role}): '{msg_preview}'")
        
        with get_performance_logger(logger, "chat_request_processing"):
            # MCP 그래프 생성
            mcp = MCPGraph(tools=available_tools)
            logger.debug(f"Created MCP graph with {len(available_tools)} tools")
            
            # 사용자 요청을 GraphState 형식으로 변환
            messages_dict = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            initial_state = {
                "messages": messages_dict,
                "tool_name": "",
                "tool_args": {},
                "tool_result": "",
                "response": "",
                "next": ""
            }
            
            logger.debug("Created initial state for MCP graph processing")
            
            return StreamingResponse(
                stream_chat_response(mcp, initial_state),
                media_type="text/event-stream"
            )
        
    except Exception as e:
        log_exception(logger, "Error in chat endpoint", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint with system status"""
    try:
        logger.debug("Health check requested")
        
        # Get system statistics if RAG service is available
        try:
            from app.rag.rag_service import rag_service
            rag_stats = await rag_service.get_system_stats()
            logger.debug("RAG system stats retrieved for health check")
        except Exception as e:
            logger.warning(f"Could not get RAG stats for health check: {e}")
            rag_stats = {"error": str(e)}
        
        # Get logging system stats
        from app.logger import get_logging_stats
        logging_stats = get_logging_stats()
        
        health_data = {
            "status": "healthy",
            "timestamp": "2025-01-19T10:00:00Z",  # You might want to use actual timestamp
            "components": {
                "rag_service": rag_stats,
                "logging_system": logging_stats,
                "available_tools": [tool.name for tool in available_tools]
            }
        }
        
        logger.info("Health check completed successfully")
        return health_data
        
    except Exception as e:
        log_exception(logger, "Health check failed", e)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-01-19T10:00:00Z"
        }

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("=== MCP Server Starting Up ===")
    logger.info(f"Available tools: {[tool.name for tool in available_tools]}")
    
    # Initialize RAG service
    try:
        logger.info("Initializing RAG service...")
        from app.rag.rag_service import rag_service
        await rag_service.initialize()
        logger.info("RAG service initialized successfully")
    except Exception as e:
        log_exception(logger, "Failed to initialize RAG service during startup", e)
        logger.warning("RAG service will be initialized on first use")
    
    logger.info("=== MCP Server Startup Complete ===")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("=== MCP Server Shutting Down ===")
    
    # Log final statistics
    try:
        from app.logger import get_logging_stats
        final_stats = get_logging_stats()
        logger.info(f"Final logging stats: {final_stats}")
    except Exception as e:
        logger.warning(f"Could not retrieve final stats: {e}")
    
    logger.info("=== MCP Server Shutdown Complete ===")

# Log application initialization
logger.info(f"MCP Server application initialized with {len(available_tools)} tools")
logger.info("FastAPI application ready to serve requests")
