from vllm import LLM
from app.config.base import settings
import huggingface_hub
import os

class ModelFactory:
    @staticmethod
    def create_model() -> LLM:
        """VLLM 모델 생성"""
        if settings.HUGGING_FACE_TOKEN:
            huggingface_hub.login(token=settings.HUGGING_FACE_TOKEN)
            os.environ["HUGGING_FACE_TOKEN"] = settings.HUGGING_FACE_TOKEN

        return LLM(
            model=settings.MODEL_PATH,
            tensor_parallel_size=settings.TENSOR_PARALLEL_SIZE,
            gpu_memory_utilization=settings.GPU_MEMORY_UTILIZATION,
            max_num_seqs=128,
            trust_remote_code=True,
            download_dir="/tmp/model_cache",
            max_model_len=settings.MAX_MODEL_LENGTH
        ) 