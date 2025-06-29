from pydantic_settings import BaseSettings
from typing import Optional

import os

from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    MODEL_PATH: str = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"  # 또는 다른 공개 모델
    # MODEL_PATH: str = "google/gemma-3-1b-it"
    MAX_TOKENS: int = 2048
    TEMPERATURE: float = 0.7
    TOP_P: float = 0.95
    TENSOR_PARALLEL_SIZE: int = 1  # GPU 수
    GPU_MEMORY_UTILIZATION: float = 0.95
    HUGGING_FACE_TOKEN: str = os.getenv("HUGGING_FACE_TOKEN")
    MAX_MODEL_LENGTH: int = 8192

    
    class Config:
        env_file = ".env"

settings = Settings() 