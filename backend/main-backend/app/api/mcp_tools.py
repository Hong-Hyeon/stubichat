from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List
from app.factory.service_factory import get_service_factory, ServiceFactory
from app.utils.logger import get_logger

router = APIRouter(prefix="/mcp", tags=["mcp-tools"])
logger = get_logger("mcp_tools_api")


class MCPToolCallRequest(BaseModel):
    """Request model for calling MCP tools."""
    tool_name: str
    input_data: Dict[str, Any]


class MCPToolCallResponse(BaseModel):
    """Response model for MCP tool calls."""
    tool_name: str
    result: Dict[str, Any]
    success: bool


class MCPToolInfo(BaseModel):
    """Model for MCP tool information."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


class MCPToolsListResponse(BaseModel):
    """Response model for listing MCP tools."""
    tools: List[MCPToolInfo]
    count: int


def get_mcp_client(service_factory: ServiceFactory = Depends(get_service_factory)):
    """Dependency to get MCP client from service factory."""
    return service_factory.mcp_client


@router.post("/tools/call", response_model=MCPToolCallResponse)
async def call_mcp_tool(
    request: MCPToolCallRequest,
    mcp_client=Depends(get_mcp_client)
):
    """
    Call an MCP tool by name with input data.
    
    This endpoint allows the main backend to call MCP tools
    and integrate their functionality into the conversation flow.
    """
    try:
        logger.info(f"Calling MCP tool: {request.tool_name}")
        
        # Call the MCP tool
        result = await mcp_client.call_tool(request.tool_name, request.input_data)
        
        logger.info(f"MCP tool {request.tool_name} called successfully")
        
        return MCPToolCallResponse(
            tool_name=request.tool_name,
            result=result,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error calling MCP tool {request.tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error calling MCP tool: {str(e)}")


@router.get("/tools/list", response_model=MCPToolsListResponse)
async def list_mcp_tools(mcp_client=Depends(get_mcp_client)):
    """
    Get list of available MCP tools.
    
    This endpoint returns information about all available MCP tools
    that can be called by the main backend.
    """
    try:
        logger.info("Listing available MCP tools")
        
        # Get tools list from MCP server
        tools_data = await mcp_client.list_tools()
        
        # Convert to our response format
        tools = []
        for tool_info in tools_data.get("tools", []):
            tools.append(MCPToolInfo(
                name=tool_info.get("name", ""),
                description=tool_info.get("description", ""),
                input_schema=tool_info.get("input_schema", {}),
                output_schema=tool_info.get("output_schema", {})
            ))
        
        logger.info(f"Found {len(tools)} MCP tools")
        
        return MCPToolsListResponse(
            tools=tools,
            count=len(tools)
        )
        
    except Exception as e:
        logger.error(f"Error listing MCP tools: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing MCP tools: {str(e)}")


@router.get("/health")
async def mcp_health_check(mcp_client=Depends(get_mcp_client)):
    """
    Check MCP server health.
    
    This endpoint checks the health of the MCP server
    and returns its status.
    """
    try:
        logger.info("Checking MCP server health")
        
        health_status = await mcp_client.health_check()
        
        logger.info(f"MCP server health: {health_status.get('status', 'unknown')}")
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error checking MCP server health: {str(e)}")
        return {"status": "unhealthy", "error": str(e)} 