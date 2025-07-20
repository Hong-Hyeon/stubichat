from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


# 매우 단순한 요청 모델들
class SimplePromptRequest(BaseModel):
    """매우 단순한 프롬프트 요청 - 사용자 메시지만 포함"""
    prompt: str = Field(..., description="사용자의 메시지")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Hello, how are you?"
            }
        }


class SimplePromptResponse(BaseModel):
    """매우 단순한 응답"""
    response: str = Field(..., description="AI의 응답")
    success: bool = Field(default=True, description="요청 성공 여부")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SimpleHealthResponse(BaseModel):
    """단순한 헬스 체크 응답"""
    status: str = Field(..., description="상태")
    message: str = Field(..., description="메시지")


# 기존 모델들 (하위 호환성을 위해 유지)
class FrontendMessage(BaseModel):
    """Frontend message format from ai-chatbot"""
    id: str
    role: str
    parts: List[Dict[str, Any]]
    experimental_attachments: Optional[List[Any]] = None


class FrontendChatRequest(BaseModel):
    """Frontend chat request format from ai-chatbot"""
    id: str
    message: FrontendMessage
    selectedChatModel: str = "chat-model"
    selectedVisibilityType: str = "private"
    user: Optional[Dict[str, Any]] = None


class SimpleChatRequest(BaseModel):
    """단순화된 채팅 요청 - 사용자 프롬프트만 포함"""
    prompt: str = Field(..., description="사용자의 메시지")
    model: str = Field(default="chat-model", description="사용할 모델")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Hello, how are you?",
                "model": "chat-model"
            }
        }


class SimpleChatResponse(BaseModel):
    """단순화된 채팅 응답"""
    response: str = Field(..., description="AI의 응답")
    model: str = Field(..., description="사용된 모델")
    success: bool = Field(default=True, description="요청 성공 여부")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="추가 메타데이터")


class HealthTestResponse(BaseModel):
    """헬스 체크 테스트 응답"""
    status: str = Field(..., description="전체 상태")
    message: str = Field(..., description="테스트 메시지")
    model_response: str = Field(..., description="모델 테스트 응답")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(default_factory=dict, description="서비스 상태")
    version: str = Field(default="1.0.0", description="앱 버전")


class ChatRequest(BaseModel):
    messages: List[Message]
    stream: bool = Field(default=True, description="Enable streaming response")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4000)
    model: str = Field(default="gpt-4", description="Model to use for inference")
    
    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, how are you today?"
                    }
                ],
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 1000,
                "model": "gpt-4"
            }
        }


class ChatResponse(BaseModel):
    response: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None
    # MCP tool metadata
    mcp_tools_used: Optional[List[str]] = Field(default=None, description="List of MCP tools that were used")
    mcp_tools_failed: Optional[List[str]] = Field(default=None, description="List of MCP tools that failed")


class StreamChunk(BaseModel):
    content: str
    finish_reason: Optional[str] = None
    model: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MCPToolCall(BaseModel):
    """Model for MCP tool call information."""
    tool_name: str
    input_data: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    success: bool = False
    error: Optional[str] = None


class ConversationState(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    # MCP tool related fields
    mcp_tools_needed: List[str] = Field(default_factory=list, description="List of MCP tools that need to be called")
    mcp_tool_calls: List[MCPToolCall] = Field(default_factory=list, description="List of MCP tool calls and their results")
    mcp_tools_available: List[Dict[str, Any]] = Field(default_factory=list, description="List of available MCP tools")
    
    class Config:
        # Allow extra fields to prevent validation errors during state updates
        extra = "allow"


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(default_factory=dict)
    version: str = "1.0.0" 