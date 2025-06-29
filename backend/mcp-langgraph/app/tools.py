from langchain.tools import BaseTool
import httpx
from app.config.base import vllm_server_url
import json
from typing import Optional

class VLLMTool(BaseTool):
    name = "vllm"
    description = "Generate creative text based on a prompt. Input should be the prompt text."
    
    async def _arun(self, args: str) -> str:
        """VLLM 서버 호출"""
        try:
        # args는 프롬프트 문자열
            args_dict = {
                "prompt": args,
                "max_tokens": 2048,
                "stream": False  # 스트리밍 비활성화
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{vllm_server_url}/generate",
                    json=args_dict,
                    timeout=30.0
                )
                
                result = response.json()
                print("VLLM response:", result)  # 디버깅
                return result["text"]
                
        except Exception as e:
            print(f"Error in VLLM tool: {e}")
            return str(e)
    
    def _run(self, args: str) -> str:
        raise NotImplementedError("VLLMTool only supports async execution")

class EchoTool(BaseTool):
    name = "echo"
    description = "Repeats back the input text. Use this tool when you need to echo back what the user said."
    
    async def _arun(self, text: str) -> str:
        """에코 기능: 입력받은 텍스트를 그대로 반환"""
        return f"Echo: {text}"
    
    def _run(self, text: str) -> str:
        raise NotImplementedError("EchoTool only supports async execution")

# 도구 인스턴스 생성
vllm_tool = VLLMTool()
echo_tool = EchoTool()

# 사용 가능한 도구 목록
available_tools = [vllm_tool, echo_tool]

# 도구 설명 검증
for tool in available_tools:
    print(f"Tool {tool.name}: {tool.description}") 