from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from vllm import SamplingParams
from app.service.llm_service import LLMService
from app.config.base import settings

router = APIRouter()

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = settings.MAX_TOKENS
    temperature: Optional[float] = settings.TEMPERATURE
    top_p: Optional[float] = settings.TOP_P
    stop: Optional[List[str]] = None
    stream: Optional[bool] = False

class GenerateResponse(BaseModel):
    text: str
    usage: dict

class GenerateRouter:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.router = APIRouter()
        self.setup_routes()

    def setup_routes(self):
        @self.router.post("/generate", response_model=GenerateResponse)
        async def generate_text(request: GenerateRequest):
            """텍스트 생성 엔드포인트"""
            try:
                sampling_params = SamplingParams(
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens,
                    stop=request.stop or []
                )

                if request.stream:
                    return StreamingResponse(
                        self.llm_service.generate_stream(request.prompt, sampling_params),
                        media_type="text/event-stream"
                    )
                
                result = self.llm_service.generate(request.prompt, sampling_params)
                return GenerateResponse(**result)
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.get("/health")
        async def health_check():
            """서버 상태 확인"""
            return {"status": "healthy"} 