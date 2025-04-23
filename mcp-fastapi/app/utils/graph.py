from typing import List, Dict, Any, TypedDict, Union, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.agents import AgentFinish, AgentAction
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END
import asyncio
import json
import re

from .mcp_tools import available_tools
from .llm import get_llm
from .utils import UtilsFunctions, AgentState


utils_functions = UtilsFunctions()


class ExaOneOutputParser:
    """ExaOne 출력을 파싱하는 클래스"""
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        json_str = utils_functions.extract_last_json_block(text)
        print(json_str)
        if json_str:
            try:
                data = json.loads(json_str)
                if "result" in data:
                    return AgentFinish(return_values={"output": data["result"]}, log=text)
                elif "name" in data and "arguments" in data:
                    return AgentAction(tool=data["name"], tool_input=data["arguments"], log=text)
            except json.JSONDecodeError as e:
                print(f"[parse] JSON decode error: {e}")
        
        return AgentAction(tool="retry", tool_input={}, log=text)  # fallback



def create_agent_graph():
    """LangGraph 기반 에이전트 생성"""
    llm = get_llm()

    def get_next_step(state: AgentState) -> str:
        """다음 단계 결정"""

        if state["loop_count"] > 3:
            return "end"
        return state["next"]

    async def call_llm(state: AgentState) -> Dict[str, AgentState]:
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
            formatted_messages.append(HumanMessage(content=f"""Tools: {tools_description}
            Format:
            ```json
            {{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}
            ```
            Please strictly follow the format above and return a valid JSON object inside a json code block (```json). The "name" must be the tool name, and "arguments" must contain the input parameters."""))
            

        # 사용자 메시지와 이전 대화 기록 추가
        formatted_messages.extend(messages)

        # ExaOne LLM 호출
        messages_text = "\n".join([msg.content for msg in formatted_messages])
        
        try:
            response = await llm.generate(messages_text)
        except Exception as e:
            print(f"Generation error: {e}")
            response = "I apologize, but I couldn't process that request."

        # ExaOne 전용 파서 사용
        parser = ExaOneOutputParser()
        parsed_response = parser.parse(response)

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
    
    async def execute_tools(state_dict: Dict[str, Any]) -> Dict[str, Any]:
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
                        # new_messages.append(HumanMessage(content=f"The result of {tool_name} is '{str(result)}'. Please summarize the final answer in a user-friendly sentence."))
                        new_messages.append(
                            HumanMessage(
                                content=f"The result of {tool_name} is '{str(result)}'. "
                                    "Is this a final and appropriate answer? If yes, return it in the following JSON format:\n\n"
                                    "```json\n"
                                    '{"result": "The final answer you would say directly to the user."}\n'
                                    "```\n"
                                    "If not, think again and select another tool to try."
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

    # LangGraph 워크플로 정의
    workflow = StateGraph(state_schema=AgentState)

    # 노드 정의
    workflow.add_node("llm", call_llm)
    workflow.add_node("tools", execute_tools)

    # 시작 노드 설정
    workflow.set_entry_point("llm")

    # 조건부 라우팅 설정
    workflow.add_conditional_edges(
        "llm",
        get_next_step,
        {
            "tools": "tools",
            "end": END
        }
    )
    workflow.add_conditional_edges(
        "tools",
        get_next_step,
        {
            "llm": "llm",
            "end": END
        }
    )

    return workflow.compile()


async def process_with_graph(input_data: Dict[str, str]) -> str:
    """LangGraph 에이전트 실행"""
    chain = create_agent_graph()
    
    # 초기 상태 생성
    initial_state = utils_functions.build_initial_state(input_data["input"])
    
    # StateGraph에 상태 직접 전달
    result = await chain.ainvoke(initial_state)
    
    # 최종 메시지 반환
    final_message = result["messages"][-1]

    message_content = final_message.content
    
    json_str = utils_functions.extract_last_json_block(message_content)
    try:
        json_data = json.loads(json_str)
    except Exception as e:
        print(f"JSON decode error: {e}")
        return "I apologize, This is not a valid response."

    return json_data.get('result', None)