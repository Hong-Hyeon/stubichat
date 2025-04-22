import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import re
import httpx
from typing import Optional


class ExaOneLLM:
    def __init__(self, model_path: str):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            padding_side="left",
            truncation_side="left"
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="cpu",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        self.model.eval()
        print(f"Model loaded on {self.device}")

    async def generate(self, prompt: str) -> str:
        # 최종 프롬프트로 LLM 생성
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=1024,
                temperature=0.3,
                top_p=0.9,
                do_sample=True
            )
        
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)


# 전역 LLM 인스턴스
llm: Optional[ExaOneLLM] = None

def init_llm(model_path: str) -> None:
    """LLM 초기화"""
    global llm
    llm = ExaOneLLM(model_path)

def get_llm() -> ExaOneLLM:
    """LLM 인스턴스 반환"""
    if llm is None:
        raise RuntimeError("LLM is not initialized")
    return llm 