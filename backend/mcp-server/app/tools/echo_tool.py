from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, Any

router = APIRouter(tags=["echo"])


class EchoInput(BaseModel):
    """Input schema for the echo tool."""
    message: str = Field(..., description="The message to echo back")
    prefix: str = Field(default="Echo: ", description="Optional prefix to add to the message")


class EchoOutput(BaseModel):
    """Output schema for the echo tool."""
    result: str = Field(..., description="The echoed message with prefix")
    original_message: str = Field(..., description="The original message that was echoed")
    prefix: str = Field(..., description="The prefix that was used")


@router.post("/echo", response_model=EchoOutput, operation_id="echo_tool")
async def echo_tool(input_data: EchoInput) -> EchoOutput:
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