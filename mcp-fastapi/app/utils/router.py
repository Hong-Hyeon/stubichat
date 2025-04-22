from typing import Dict
from ..models import RoutingDecision, ModelType
from .llm import get_llm


ROUTING_PROMPT = """입력: {content}

입력의 의도를 파악해서 입력값이 번역 요청이면 'nllb', 그 외의 경우는 'exaone'으로 답변하세요.
"""


async def determine_route(content: str) -> RoutingDecision:
    """LLM을 사용하여 라우팅 결정"""
    llm = get_llm()
    
    # 라우팅 결정을 위한 프롬프트 생성
    prompt = ROUTING_PROMPT.format(content=content)
    
    # LLM 응답 받기
    response = llm.generate(
        prompt,
        max_length=200,
        temperature=0.3,
        top_p=0.7
    )
    print(response)
    
    # 응답 파싱
    lines = response.strip().split('\n')
    model_line = next(line for line in lines if line.startswith('모델:'))
    reason_line = next(line for line in lines if line.startswith('이유:'))
    
    model = model_line.split(':')[1].strip().lower()
    reason = reason_line.split(':')[1].strip()
    
    return RoutingDecision(
        model_type=ModelType(model),
        reason=reason
    ) 