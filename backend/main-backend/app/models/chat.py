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