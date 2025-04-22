from langchain.tools import Tool, StructuredTool
from typing import List

import httpx


# MCP 도구 → LangChain Tool로 래핑
def call_file_read(file_path: str) -> str:
    """파일 내용을 읽어오는 도구"""
    res = httpx.get("http://localhost:8001/file_read", params={"file_path": file_path})
    return res.json().get("text", "No content")

def call_echo(message: str) -> str:
    """메시지를 그대로 반환하는 도구"""
    res = httpx.get("http://localhost:8001/echo", params={"message": message})
    return res.json().get("text", "No content")

def call_calc_sum(arguments: dict) -> str:
    """여러 숫자의 합을 계산하는 도구"""
    try:
        # 딕셔너리에서 숫자들을 추출하여 리스트로 변환
        numbers = []
        for key, value in sorted(arguments.items()):  # 정렬하여 순서 보장
            if key.startswith('arg'):
                numbers.append(str(value))
        
        # 쉼표로 구분된 문자열로 변환
        numbers_str = ",".join(numbers)
        res = httpx.get("http://localhost:8001/calc_sum", params={"numbers": numbers_str})
        return res.json().get("text", "No content")
    except Exception as e:
        return f"Error: {str(e)}"

def call_reverse_text(text: str) -> str:
    """텍스트를 뒤집는 도구"""
    res = httpx.get("http://localhost:8001/reverse_text", params={"text": text})
    return res.json().get("text", "No content")

def call_word_count(text: str) -> str:
    """텍스트의 단어 수를 세는 도구"""
    res = httpx.get("http://localhost:8001/word_count", params={"text": text})
    return res.json().get("text", "No content")




file_read_tool = Tool.from_function(
    name="file_read",
    description="Reads content from a file. Input should be a file path.",
    func=call_file_read
)

echo_tool = Tool.from_function(
    name="echo",
    description="Repeats the input message back.",
    func=call_echo
)

calc_sum_tool = StructuredTool.from_function(
    name="calc_sum",
    description="Calculates the sum of numbers. Input should be a dictionary with numbered arguments (e.g. {'arguments': {'arg1': '2', 'arg2': '3'}}).",
    func=call_calc_sum,
    args_schema={
        "arguments": {
            "type": "object",
            "description": "Dictionary containing numbered arguments"
        }
    }
)

reverse_text_tool = Tool.from_function(
    name="reverse_text",
    description="Reverses the input text.",
    func=call_reverse_text
)

word_count_tool = Tool.from_function(
    name="word_count",
    description="Counts the number of words in the input text.",
    func=call_word_count
)

# 사용 가능한 모든 도구 목록
available_tools = [
    file_read_tool,
    echo_tool,
    calc_sum_tool,
    reverse_text_tool,
    word_count_tool
]

