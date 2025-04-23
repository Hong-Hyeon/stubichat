from fastapi import FastAPI
from app.routes import messages
from app.config.base import EXAONE_MODEL_PATH
from app.utils.llm import init_llm


app = FastAPI(title="Intellicode HTTP Server")

# LLM 초기화
init_llm(str(EXAONE_MODEL_PATH))

# 라우터 등록
app.include_router(messages.router)