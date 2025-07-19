import httpx
from typing import Dict, Any, Optional
from app.utils.logger import get_logger
from app.core.config import get_settings


class MCPClient:
    """Client for calling MCP tools from the main backend."""
    
    def __init__(self, base_url: str = None):
        self.settings = get_settings()
        # Use the MCP server URL from environment or default to localhost:8002
        self.base_url = base_url or getattr(self.settings, 'mcp_server_url', 'http://mcp-server:8002')
        self.logger = get_logger("mcp_client")
    
    async def call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool by name with input data.
        
        Args:
            tool_name: Name of the MCP tool to call
            input_data: Input data for the tool
            
        Returns:
            Tool response data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/tools/{tool_name}",
                    json=input_data,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error calling tool {tool_name}: {e.response.status_code}")
            raise
        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name}: {str(e)}")
            raise
    
    async def list_tools(self) -> Dict[str, Any]:
        """
        Get list of available MCP tools.
        
        Returns:
            List of available tools
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/tools/list",
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error listing tools: {e.response.status_code}")
            raise
        except Exception as e:
            self.logger.error(f"Error listing tools: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check MCP server health.
        
        Returns:
            Health status
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=5.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error in health check: {e.response.status_code}")
            return {"status": "unhealthy", "error": str(e)}
        except Exception as e:
            self.logger.error(f"Error in health check: {str(e)}")
            return {"status": "unhealthy", "error": str(e)} 