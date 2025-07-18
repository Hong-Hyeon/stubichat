import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.config import settings
from app.utils.logger import get_logger, log_performance
from app.models.requests import Message, StreamChunk


class OpenAIService:
    """Service for interacting with OpenAI API."""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            organization=settings.openai_organization
        )
        self.logger = get_logger("openai_service")
        
        # Initialize LangChain client for compatibility
        self.langchain_client = ChatOpenAI(
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_base_url,
            model=settings.default_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens
        )
    
    def _convert_messages(self, messages: list[Message]) -> list[Dict[str, str]]:
        """Convert Pydantic messages to OpenAI format."""
        openai_messages = []
        for msg in messages:
            openai_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        return openai_messages
    
    async def generate_text(
        self, 
        messages: list[Message], 
        model: str = None,
        temperature: float = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate text using OpenAI API."""
        try:
            with log_performance(self.logger, f"OpenAI text generation with {model}"):
                response = await self.client.chat.completions.create(
                    model=model or settings.default_model,
                    messages=self._convert_messages(messages),
                    temperature=temperature or settings.temperature,
                    max_tokens=max_tokens or settings.max_tokens,
                    stream=False
                )
            
            # Extract response
            content = response.choices[0].message.content
            usage = response.usage.model_dump() if response.usage else None
            finish_reason = response.choices[0].finish_reason
            
            self.logger.info(f"Generated {len(content)} characters with {model}")
            
            return {
                "response": content,
                "model": model or settings.default_model,
                "usage": usage,
                "finish_reason": finish_reason
            }
            
        except Exception as e:
            self.logger.error(f"OpenAI text generation failed: {str(e)}")
            raise
    
    async def stream_text(
        self, 
        messages: list[Message], 
        model: str = None,
        temperature: float = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream text generation using OpenAI API."""
        try:
            with log_performance(self.logger, f"OpenAI stream generation with {model}"):
                stream = await self.client.chat.completions.create(
                    model=model or settings.default_model,
                    messages=self._convert_messages(messages),
                    temperature=temperature or settings.temperature,
                    max_tokens=max_tokens or settings.max_tokens,
                    stream=True
                )
                
                async for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield StreamChunk(
                            content=chunk.choices[0].delta.content,
                            model=model or settings.default_model,
                            finish_reason=None
                        )
                    
                    # Check if stream is finished
                    if chunk.choices[0].finish_reason:
                        yield StreamChunk(
                            content="",
                            model=model or settings.default_model,
                            finish_reason=chunk.choices[0].finish_reason
                        )
                        break
                        
        except Exception as e:
            self.logger.error(f"OpenAI stream generation failed: {str(e)}")
            yield StreamChunk(
                content="",
                model=model or settings.default_model,
                finish_reason="error"
            )
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI API health."""
        try:
            # Simple test with a minimal request
            await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            
            return {
                "status": "healthy",
                "openai_status": "connected",
                "model_available": True
            }
            
        except Exception as e:
            self.logger.error(f"OpenAI health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "openai_status": "disconnected",
                "error": str(e)
            }


# Global OpenAI service instance
openai_service = OpenAIService() 