from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, AsyncGenerator, Literal
from app.core.graph import MCPGraph
from app.tools import available_tools
import json
import logging
import asyncio

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        async for chunk in mcp.astream(state):
            print(chunk)  # 디버깅용
            
            if "response" in chunk and chunk.get("streaming"):
                # 스트리밍이 필요한 응답은 문장 단위로 나누어 전송
                sentences = chunk["response"].split(". ")
                for sentence in sentences:
                    if sentence.strip():
                        yield f"data: {json.dumps({'text': sentence.strip() + '.'}, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.1)
            elif "response" in chunk:
                # 일반 응답은 그대로 전송
                yield f"data: {json.dumps({'text': chunk['response']}, ensure_ascii=False)}\n\n"
            elif "error" in chunk:
                yield f"data: {json.dumps({'error': chunk['error']}, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"Error in stream_chat_response: {e}")
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    finally:
        yield "data: [DONE]\n\n"


@app.post("/chat")
async def chat(request: ChatRequest):
    """채팅 엔드포인트"""
    try:
        logger.info(f"Received chat request: {request}")
        
        # MCP 그래프 생성
        mcp = MCPGraph(tools=available_tools)
        
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
        
        logger.info(f"Created initial state: {initial_state}")
        
        return StreamingResponse(
            stream_chat_response(mcp, initial_state),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
