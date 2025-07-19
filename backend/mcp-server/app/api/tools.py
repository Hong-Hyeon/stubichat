from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from app.tools import get_all_tools, get_tool_by_name
from app.tools.echo_tool import EchoInput, EchoOutput, echo_tool_function

router = APIRouter(prefix="/tools", tags=["mcp-tools"])


class ToolsListResponse(BaseModel):
    """Response model for tools list."""
    tools: List[Dict[str, Any]]
    count: int
    server: str = "stubichat-mcp"


@router.get("/list", response_model=ToolsListResponse)
async def list_tools():
    """
    Get list of available MCP tools.
    
    This endpoint returns information about all available MCP tools
    that can be called by clients.
    """
    tools = get_all_tools()
    
    # Convert tool metadata to response format
    tools_list = []
    for tool in tools:
        tools_list.append({
            "name": tool["name"],
            "description": tool["description"],
            "endpoint": f"/tools/{tool['name']}",
            "method": "POST",
            "request_model": tool["input_schema"]["title"],
            "response_model": tool["output_schema"]["title"],
            "input_schema": tool["input_schema"],
            "output_schema": tool["output_schema"]
        })
    
    return ToolsListResponse(
        tools=tools_list,
        count=len(tools_list)
    )


@router.post("/echo", response_model=EchoOutput)
async def echo_tool(request: EchoInput):
    """
    Echo tool that returns the input message with an optional prefix.
    
    This is a simple MCP tool that demonstrates basic functionality.
    """
    try:
        result = echo_tool_function(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing echo tool: {str(e)}")


# Generic tool endpoint (for future tools)
@router.post("/{tool_name}")
async def call_tool(tool_name: str, request: Dict[str, Any]):
    """
    Generic endpoint to call any MCP tool by name.
    
    This endpoint dynamically routes to the appropriate tool handler
    based on the tool name.
    """
    tool = get_tool_by_name(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    try:
        # For now, we only have the echo tool
        if tool_name == "echo":
            # Convert dict to EchoInput
            echo_input = EchoInput(**request)
            result = echo_tool_function(echo_input)
            return result
        else:
            raise HTTPException(status_code=501, detail=f"Tool '{tool_name}' not implemented")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing tool '{tool_name}': {str(e)}") 