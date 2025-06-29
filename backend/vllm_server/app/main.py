from fastapi import FastAPI
from app.factory.model_factory import ModelFactory
from app.service.llm_service import LLMService
from app.routers.generate import GenerateRouter

def create_app() -> FastAPI:
    """애플리케이션 팩토리"""
    app = FastAPI(title="VLLM Server")
    
    # 모델 및 서비스 초기화
    model = ModelFactory.create_model()
    llm_service = LLMService(model)
    
    # 라우터 설정
    generate_router = GenerateRouter(llm_service)
    app.include_router(generate_router.router)
    
    return app

app = create_app()