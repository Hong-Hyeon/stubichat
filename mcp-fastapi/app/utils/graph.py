from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.agents import AgentFinish
from langgraph.graph import StateGraph, END
import asyncio
import json

from app.utils.mcp_tools import available_tools
from app.utils.llm import get_llm
from app.utils.utils import UtilsFunctions
from app.utils.parser import ExaOneOutputParser
from app.utils.prompt import prompt_manager
from app.config.constants import ErrorMessage
from app.schema.base import AgentState

utils_functions = UtilsFunctions()


class AgentGraph:
    def __init__(self):
        self.llm = get_llm()
        self.parser = ExaOneOutputParser()

    def create_agent_graph(self):
        """LangGraph 기반 에이전트 생성"""
        # LangGraph 워크플로 정의
        workflow = StateGraph(state_schema=AgentState)

        # 노드 정의
        workflow.add_node("llm", self.call_llm)
        workflow.add_node("tools", self.execute_tools)

        # 시작 노드 설정
        workflow.set_entry_point("llm")

        # 조건부 라우팅 설정
        workflow.add_conditional_edges(
            "llm",
            self.get_next_step,
            {
                "tools": "tools",
                "end": END
            }
        )
        workflow.add_conditional_edges(
            "tools",
            self.get_next_step,
            {
                "llm": "llm",
                "end": END
            }
        )

        return workflow.compile()

    def get_next_step(self, state: AgentState) -> str:
        """다음 단계 결정"""

        if state["loop_count"] > 3:
            return "end"
        return state["next"]

    async def call_llm(self, state: AgentState) -> Dict[str, AgentState]:
        """LLM 호출"""
        messages = state["messages"]
        
        # 메시지와 도구 정보 포맷팅
        formatted_messages = []
        
        # 시스템 메시지 추가
        tools_description = "\n".join([
            f"{tool.name}: {tool.description}" 
            for tool in available_tools
        ])
        if not any("Tools:" in msg.content for msg in messages):
            formatted_messages.append(HumanMessage(content=prompt_manager.get_call_llm_prompt(tools_description)))

        # 사용자 메시지와 이전 대화 기록 추가
        formatted_messages.extend(messages)
        # ExaOne LLM 호출
        messages_text = "\n".join([msg.content for msg in formatted_messages])

        try:
            response = await self.llm.generate(messages_text)
        except Exception as e:
            print(f"Generation error: {e}")
            response = ErrorMessage.GENERATION_ERROR.value

        # ExaOne 전용 파서 사용
        parsed_response = self.parser.parse(response)

        # 상태 업데이트
        new_messages = messages + [AIMessage(
            content=response,
            additional_kwargs={"action": parsed_response}
        )]

        # AgentState를 직접 반환
        next_step = "end" if isinstance(parsed_response, AgentFinish) else "tools"
        
        # TypedDict를 직접 생성
        new_state = AgentState(
            messages=new_messages,
            next=next_step,
            loop_count=state["loop_count"] + 1
        )
        
        return new_state
    
    async def execute_tools(self, state_dict: Dict[str, Any]) -> Dict[str, Any]:
        """도구 실행"""
        messages = state_dict["messages"]
        last_message = messages[-1]

        new_messages = messages.copy()

        if isinstance(last_message, AIMessage):
            action = last_message.additional_kwargs.get("action")
            if action and not isinstance(action, AgentFinish):
                tool_name = action.tool
                tool_args = action.tool_input
                tool = next((t for t in available_tools if t.name == tool_name), None)

                if tool:
                    try:
                        # 도구 실행 (비동기/동기 대응)
                        if asyncio.iscoroutinefunction(tool.invoke):
                            result = await tool.invoke(tool_args)
                        else:
                            result = tool.invoke(tool_args)

                        # 결과를 메시지로 추가
                        new_messages.append(
                            HumanMessage(
                                content=prompt_manager.get_execute_tool_prompt(tool_name, result)
                            )
                        )
                        # 도구 실행 성공 시 LLM으로 돌아가기
                        return AgentState(
                            messages=new_messages,
                            next="llm"
                        )
                    except Exception as e:
                        # 도구 실행 실패 시 에러 메시지 추가하고 종료
                        new_messages.append(HumanMessage(content=f"Error executing tool: {str(e)}"))
                        return AgentState(
                            messages=new_messages,
                            next="end"
                        )

        # 도구 실행이 불필요하거나 실패한 경우 종료
        return AgentState(
            messages=new_messages,
            next="end"
        )


    async def process_with_graph(self, input_data: Dict[str, str]) -> str:
        """LangGraph 에이전트 실행"""
        chain = self.create_agent_graph()
        
        # 초기 상태 생성
        initial_state = utils_functions.build_initial_state(input_data["input"])
        
        # StateGraph에 상태 직접 전달
        result = await chain.ainvoke(initial_state)
        # 최종 메시지 반환
        final_message = result["messages"][-1]

        message_content = final_message.content
        print("message_content", message_content)
        json_str = utils_functions.extract_last_json_block(message_content)
        try:
            json_data = json.loads(json_str)
        except Exception as e:
            print(f"JSON decode error: {e}")
            return ErrorMessage.RESPONSE_ERROR.value

        return json_data.get('result', None)