from fastapi import APIRouter, HTTPException
import httpx
from ..models import MCPMessage, AgentResponse
from ..utils.graph import process_with_graph

router = APIRouter()


@router.post("/process", response_model=AgentResponse)
async def process_message(message: MCPMessage):
    """메시지 처리"""
    try:
        result = await process_with_graph({
            "input": message.prompt,
            "model": message.model,
            "parameters": message.parameters
        })
        return AgentResponse(
            status="success",
            response={"output": result}
        )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error communicating with agent: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 