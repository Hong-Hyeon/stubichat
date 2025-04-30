from typing import List, Union, TypedDict
from langchain_core.messages import HumanMessage, AIMessage


# 상태 정의
class AgentState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]
    next: str
    # 추가
    loop_count: int