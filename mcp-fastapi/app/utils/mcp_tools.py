from app.config.base import MCP_SERVER_URL

from langchain.tools import Tool, StructuredTool

import httpx


# MCP 도구 → LangChain Tool로 래핑
def call_file_read(file_path: str) -> str:
    """파일 내용을 읽어오는 도구"""
    try:
        res = httpx.get(f"{MCP_SERVER_URL}/file_read", params={"file_path": file_path})
        return res.json().get("text", "No content")
    except Exception as e:
        return f"Error: {str(e)}"

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
        res = httpx.get(f"{MCP_SERVER_URL}/calc_sum", params={"numbers": numbers_str})
        return res.json().get("text", "No content")
    except Exception as e:
        return f"Error: {str(e)}"

def call_query_db(arguments: dict) -> str:
    """데이터베이스 쿼리를 실행하는 도구"""
    try:
        sql_query = arguments.get('query', '')
        if not sql_query:
            return "Error: No SQL query provided"
            
        res = httpx.get(f"{MCP_SERVER_URL}/query_db", params={"sql_query": sql_query})
        return res.json().get("text", "No content")
    except Exception as e:
        return f"Error: {str(e)}"


file_read_tool = StructuredTool.from_function(
    name="file_read",
    description="Reads content from a file. Input should be a file path.",
    func=call_file_read
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

query_db_tool = StructuredTool.from_function(
    name="query_db",
    description="""Executes SQL queries to retrieve data from the database. 
    You should create appropriate SQL queries based on the user's request.
    The database contains various tables with information.
    First analyze the user's request, then create and execute an SQL query.
    Return the results in a clear format.""",
    func=call_query_db,
    args_schema={
        "arguments": {
            "type": "object",
            "description": "Dictionary containing SQL query"
        }
    }
)

# 사용 가능한 모든 도구 목록
available_tools = [
    file_read_tool,
    calc_sum_tool,
    query_db_tool
]

