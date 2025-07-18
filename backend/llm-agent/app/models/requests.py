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


class GenerateRequest(BaseModel):
    messages: List[Message]
    stream: bool = Field(default=False, description="Enable streaming response")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4000)
    model: str = Field(default="gpt-4", description="OpenAI model to use")
    
    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, how are you today?"
                    }
                ],
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 1000,
                "model": "gpt-4"
            }
        }


class GenerateResponse(BaseModel):
    response: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StreamChunk(BaseModel):
    content: str
    finish_reason: Optional[str] = None
    model: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    status: str
    service: str = "llm-agent"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    openai_status: Optional[str] = None
    version: str = "1.0.0" 