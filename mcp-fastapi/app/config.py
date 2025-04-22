from .mcp import Agent
from pathlib import Path


# 에이전트 설정
AGENTS = {
    "exaone": Agent(
        id="exaone",
        name="ExaOne Local Agent",
        description="Local ExaOne text generation model",
        endpoint="http://exaone-agent:8000/generate"
    ),
    "nllb": Agent(
        id="nllb",
        name="NLLB Local Agent",
        description="Local NLLB translation model",
        endpoint="http://nllb-agent:8000/translate"
    )
}

# ExaOne 모델 설정
EXAONE_MODEL_PATH = Path("LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct")  # 실제 모델 경로로 수정 필요 