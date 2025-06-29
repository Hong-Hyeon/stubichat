from typing import Dict, List, Tuple, Any, AsyncGenerator, TypedDict
from langgraph.graph import Graph, StateGraph
from langgraph.prebuilt import ToolExecutor
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
import json
import httpx
from app.config.base import vllm_server_url
from app.core.prompts import TOOL_SELECTION_TEMPLATE, RESULT_SUMMARY_TEMPLATE
import logging
import asyncio

logger = logging.getLogger(__name__)

# 상태 스키마 정의
class GraphState(TypedDict):
    messages: List[Dict]
    tool_name: str
    tool_args: Dict
    tool_result: str
    response: str
    next: str

class MCPGraph:
    def __init__(self, tools: List[Tool], model_url: str = vllm_server_url):
        self.tools = tools
        self.model_url = model_url
        self.tool_executor = ToolExecutor(tools)
        
    def create_graph(self) -> Graph:
        # StateGraph 초기화 시 스키마 전달
        workflow = StateGraph(GraphState)
        
        # 노드 정의
        workflow.add_node("tool_selector", self.tool_selector_node)
        workflow.add_node("tool_executor", self.tool_executor_node)
        workflow.add_node("result_summarizer", self.result_summarizer_node)
        workflow.add_node("end", lambda x: x)  # 종료 노드 추가
        
        # 엣지 정의
        workflow.set_entry_point("tool_selector")
        
        # tool_selector에서 조건부 분기
        workflow.add_conditional_edges(
            "tool_selector",
            lambda x: "tool_executor" if x.get("tool_name") else "end",
            {
                "tool_executor": "tool_executor",
                "end": "end"
            }
        )
        
        # 도구 실행 후 요약
        workflow.add_edge("tool_executor", "result_summarizer")
        
        # 종료 노드 설정
        workflow.set_finish_point("result_summarizer")
        workflow.set_finish_point("end")
        
        return workflow.compile()
    
    async def tool_selector_node(self, state: Dict) -> Dict:
        """도구 선택 노드"""
        messages = state["messages"]
        last_message = messages[-1]["content"]
        
        # VLLM 서버에 도구 선택 요청
        tool_selection = await self.call_vllm_for_tool_selection(last_message)

        if tool_selection.get("use_tool"):
            return {
                "next": "tool_executor",
                "tool_name": tool_selection["tool_name"],
                "tool_args": tool_selection["tool_args"]
            }
        else:
            # 도구를 사용하지 않을 때는 바로 응답 반환
            return {
                "next": "end",
                "tool_name": "",
                "response": tool_selection.get("response", "")
            }
    
    async def tool_executor_node(self, state: Dict) -> Dict:
        """도구 실행 노드"""
        tool_name = state["tool_name"]
        tool_args = state["tool_args"]
        
        tool = next((t for t in self.tools if t.name == tool_name), None)

        if not tool:
            raise ValueError(f"Tool {tool_name} not found")

        result = await tool.ainvoke(tool_args)
        return {
            "next": "result_summarizer",
            "tool_result": result,
            "tool_name": tool_name
        }
    
    async def result_summarizer_node(self, state: Dict) -> Dict:
        """결과 요약 노드"""
        if "tool_result" in state:
            tool_result = state["tool_result"]
            tool_name = state["tool_name"]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.model_url}/generate",
                    json={
                        "prompt": self.create_summary_prompt(tool_name, tool_result),
                        "max_tokens": 2048,
                        "stream": True
                    }
                )

                summary = ""

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    line_content = line[6:].strip()

                    if line_content == "[DONE]":
                        break

                    try:
                        data = json.loads(line_content)
                        if "text" in data:
                            summary += data["text"]
                    except json.JSONDecodeError:
                        continue

            # GraphState의 모든 필드를 포함하여 반환
            return {
                "messages": state["messages"],  # 기존 메시지 유지
                "tool_name": state["tool_name"],
                "tool_args": state["tool_args"],
                "tool_result": state["tool_result"],
                "response": f"{tool_result}\n\n요약:\n{summary}",
                "next": "end",
                # "streaming": True
            }

        else:
            return {
                "messages": state["messages"],  # 기존 메시지 유지
                "tool_name": "",
                "tool_args": {},
                "tool_result": "",
                "response": state.get("response", ""),
                "next": "end",
                # "streaming": False
            }
    
    async def call_vllm_for_tool_selection(self, message: str) -> Dict:
        """VLLM 서버 호출 - 도구 선택"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.model_url}/generate",
                json={
                    "prompt": self.create_tool_selection_prompt(message),
                    "max_tokens": 2048,
                    "stream": True
                }
            )

            raw_text = ""

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue

                content = line[6:].strip()

                if content == "[DONE]":
                    break

                try:
                    data = json.loads(content)
                    if "text" in data:
                        raw_text += data["text"]
                except json.JSONDecodeError:
                    continue

            try:
                return json.loads(raw_text)
            except json.JSONDecodeError:
                return {
                    "use_tool": False,
                    "response": "도구 선택 응답 파싱 실패",
                    "reasoning": "Invalid JSON"
                }
            
    # async def call_vllm_for_summary(self, tool_name: str, tool_result: str) -> str:
    #     """VLLM 서버 호출 - 결과 요약"""
    #     async with httpx.AsyncClient() as client:
    #         response = await client.post(
    #             f"{self.model_url}/generate",
    #             json={
    #                 "prompt": self.create_summary_prompt(tool_name, tool_result),
    #                 "max_tokens": 2048,
    #                 "stream": True
    #             }
    #         )
            
    #         print(f"Response: {response.text}")
            
    #         full_text = ""
    #         async for line in response.aiter_lines():
    #             if line.startswith("data: "):
    #                 data = json.loads(line[6:])
    #                 print(f"Data: {data}")
    #                 if data == "[DONE]":
    #                     break
    #                 if "text" in data:
    #                     text = data["text"].strip()
    #                     if text:
    #                         # 각 청크를 JSON 형식으로 변환
    #                         chunk_json = {
    #                             "tool_executor": {
    #                                 "next": "result_summarizer",
    #                                 "tool_result": tool_result,
    #                                 "summary": text,
    #                                 "tool_name": tool_name
    #                             }
    #                         }
    #                         full_text += text
            
    #         # 최종 텍스트를 JSON 형식으로 변환
    #         return json.dumps({
    #             "tool_executor": {
    #                 "next": "result_summarizer",
    #                 "tool_result": tool_result,
    #                 "summary": full_text,
    #                 "tool_name": tool_name
    #             }
    #         })

    async def astream(self, state: Dict) -> AsyncGenerator[Dict, None]:
        """그래프 실행 결과를 스트리밍으로 반환"""
        try:
            graph = self.create_graph()
            async for chunk in graph.astream(state):
                if "__end__" in chunk:
                    yield chunk["__end__"]
                # 모든 응답을 그대로 전달
                else:
                    yield chunk
        except Exception as e:
            logger.error(f"Error in astream: {e}", exc_info=True)
            yield {"error": str(e)}
    
    def create_tool_selection_prompt(self, message: str) -> str:
        """도구 선택 프롬프트 생성"""
        try:
            tool_descriptions = "\n".join(
                f"- {tool.name}: {tool.description}"
                for tool in self.tools
            )
            prompt = TOOL_SELECTION_TEMPLATE.format(
                tool_descriptions=tool_descriptions,
                user_message=message
            )
            return prompt
        except Exception as e:
            print(f"Error creating prompt: {e}")
            raise
        
    def create_summary_prompt(self, tool_name: str, tool_result: str) -> str:
        """결과 요약 프롬프트 생성"""
        return RESULT_SUMMARY_TEMPLATE.format(
            tool_name=tool_name,
            tool_result=tool_result
        )