from pydantic import BaseModel, Field
from typing import Dict, Any


class EchoInput(BaseModel):
    """Input schema for the echo tool."""
    message: str = Field(..., description="The message to echo back")
    prefix: str = Field(default="Echo: ", description="Optional prefix to add to the message")


class EchoOutput(BaseModel):
    """Output schema for the echo tool."""
    result: str = Field(..., description="The echoed message with prefix")
    original_message: str = Field(..., description="The original message that was echoed")
    prefix: str = Field(..., description="The prefix that was used")


def echo_tool_function(input_data: EchoInput) -> EchoOutput:
    """
    Echo tool that returns the input message with an optional prefix.
    
    This is a simple MCP tool that demonstrates basic functionality.
    """
    result = f"{input_data.prefix}{input_data.message}"
    
    return EchoOutput(
        result=result,
        original_message=input_data.message,
        prefix=input_data.prefix
    )


# Tool metadata for MCP
echo_tool_metadata = {
    "name": "echo",
    "description": "Echo tool that returns the input message with an optional prefix",
    "input_schema": EchoInput.model_json_schema(),
    "output_schema": EchoOutput.model_json_schema(),
    "handler": echo_tool_function
} 