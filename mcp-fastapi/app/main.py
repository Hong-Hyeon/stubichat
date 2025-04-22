from fastapi import FastAPI
from .routes import agents, messages
from .config import EXAONE_MODEL_PATH
from .utils.llm import init_llm, get_llm


app = FastAPI(title="Intellicode HTTP Server")

# LLM 초기화
init_llm(str(EXAONE_MODEL_PATH))

# 라우터 등록
app.include_router(agents.router)
app.include_router(messages.router)