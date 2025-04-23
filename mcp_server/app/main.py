from fastapi import FastAPI, Query, HTTPException
from fastapi_mcp import FastApiMCP
from mcp.types import TextContent
from pathlib import Path
from typing import Optional, List
import re

### MCP 서버 설정
mcp_app = FastAPI(title="Intellicode MCP Server")

# MCP 서버 초기화
mcp = FastApiMCP(
    mcp_app,
    name="intellicode-mcp",
    description="Intellicode MCP Server",
    # LLM 서버 주소
    base_url="http://localhost:8001",
    include_operations=["file_read", "calc_sum", "reverse_text"]
)
# MCP 서버 마운트
mcp.mount(mcp_app)

@mcp_app.get("/file_read", operation_id="file_read")
async def read_file(file_path: str) -> TextContent:
    """파일 내용 읽기"""
    try:
        path = Path(file_path)
        if not path.exists():
            return TextContent(text=f"Error: File not found - {file_path}", type="text")
        
        if not path.is_file():
            return TextContent(text=f"Error: Not a file - {file_path}", type="text")
            
        content = path.read_text(encoding='utf-8')
        # 파일 내용을 문자열로 안전하게 처리
        print("content", content)
        result = f"The file content retrieved by file_read is:\n{str(content).replace('%', '%%')}"
        return TextContent(text=result, type="text")
    except Exception as e:
        return TextContent(text=f"Error reading file: {str(e)}", type="text")


@mcp_app.get("/calc_sum", operation_id="calc_sum")
async def calc_sum(numbers: str = Query(..., description="Numbers to sum, separated by comma")) -> TextContent:
    """여러 숫자의 합을 계산"""
    try:
        # 입력 문자열에서 숫자만 추출
        nums = re.findall(r'-?\d+', numbers)  # 음수도 처리 가능하도록
        
        if not nums:
            raise ValueError("At least one number is required")
        
        # 문자열을 정수로 변환
        nums = list(map(int, nums))
        result = sum(nums)
        
        # TextContent 타입으로 반환
        if len(nums) == 1:
            return TextContent(text=f"The Final result is {result}", type="text")
        else:
            return TextContent(text=f"The Final result of calc_sum is {result}", type="text")
            
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))


@mcp_app.get("/reverse_text", operation_id="reverse_text")
async def reverse_text(text: str = Query(...)) -> TextContent:
    reversed_text = text[::-1]
    return TextContent(text=reversed_text, type="text")

mcp.setup_server()