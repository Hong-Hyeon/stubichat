from typing import Optional
from langchain_core.messages import HumanMessage
import re

from app.schema.base import AgentState


class UtilsFunctions:
    def __init__(self):
        pass
    
    def build_initial_state(self, user_input: str) -> AgentState:
        """초기 상태 생성"""
        return AgentState(
            messages=[HumanMessage(content=user_input)],
            next="llm",
            # 추가
            loop_count=0
        )

    def extract_last_json_block(self, text: str) -> Optional[str]:
        # LLM은 ```json``` 블럭 형태를 인식을 잘함. 프롬프트에 꼭 넣어주세요. 그냥 json으로 써달라고 하면 인식이 잘 안됨
        try:
            matches = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
            if matches:
                return matches[-1]  # 마지막 JSON 블럭
        except Exception as e:
            print(f"JSON extract error: {e}")
        return None