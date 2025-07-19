from .echo_tool import echo_tool_metadata

# Registry of all available MCP tools
MCP_TOOLS = [
    echo_tool_metadata,
]


# Function to get all tools
def get_all_tools():
    """Get all registered MCP tools."""
    return MCP_TOOLS


# Function to get a specific tool by name
def get_tool_by_name(name: str):
    """Get a specific MCP tool by name."""
    for tool in MCP_TOOLS:
        if tool.name == name:
            return tool
    return None 