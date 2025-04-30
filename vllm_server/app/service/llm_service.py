# 엑사원은 head_size가 80이라 vllm에서 지원하지 않음.
import os
os.environ["VLLM_USE_V1"] = "0"

from vllm import LLM, SamplingParams
from typing import List, Optional, Dict, AsyncGenerator
import json
import asyncio

class LLMService:
    def __init__(self, model: LLM):
        self.model = model

    async def generate_stream(self, prompt: str, sampling_params: SamplingParams) -> AsyncGenerator[str, None]:
        """스트리밍 방식으로 텍스트 생성"""
        try:
            # 일반 generate 메서드 사용
            print(f"Generating with prompt: {prompt}")
            outputs = self.model.generate(prompts=[prompt], sampling_params=sampling_params)
            
            # 결과를 작은 청크로 나누어 스트리밍
            for output in outputs[0].outputs:
                text = output.text
                if text and text.strip():  # 빈 텍스트 필터링
                    # 디버깅을 위한 로그
                    print(f"Raw text chunk: {text}")
                    
                    try:
                        # JSON인지 확인
                        json.loads(text)
                        # JSON이면 그대로 전달
                        yield f"data: {json.dumps({'text': text})}\n\n"
                    except json.JSONDecodeError:
                        # JSON이 아니면 문장 단위로 나누기
                        chunks = [c.strip() for c in text.split('.') if c.strip()]
                        for chunk in chunks:
                            response_json = json.dumps({'text': chunk + '.'})
                            print(f"Sending chunk: {response_json}")
                            yield f"data: {response_json}\n\n"
                            await asyncio.sleep(0.1)
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"Error in generate_stream: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    def generate(self, prompt: str, sampling_params: SamplingParams) -> Dict:
        """일반 방식으로 텍스트 생성"""
        outputs = self.model.generate(prompts=[prompt], sampling_params=sampling_params)
        generated_text = outputs[0].outputs[0].text
        
        usage = {
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": len(generated_text.split()),
            "total_tokens": len(prompt.split()) + len(generated_text.split())
        }
        
        return {
            "text": generated_text,
            "usage": usage
        } 