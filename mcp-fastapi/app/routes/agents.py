from fastapi import APIRouter, HTTPException
from typing import Dict

from ..mcp import Agent
from ..core import mcp


router = APIRouter()


@router.get("/agents")
async def get_agents():
    """등록된 모든 에이전트 정보 조회"""
    return mcp.list_agents()


@router.post("/agents/{agent_id}/status")
async def update_agent_status(agent_id: str, status: str):
    """에이전트 상태 업데이트"""
    try:
        agent = mcp.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent {agent_id} not found"
            )
        
        if status not in ["active", "inactive", "maintenance"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid status"
            )
        
        mcp.update_agent_status(agent_id, status)
        return {"message": f"Agent {agent_id} status updated to {status}"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """서버 헬스 체크"""
    agents_status = {
        agent.id: agent.status 
        for agent in mcp.list_agents()
    }
    return {
        "status": "healthy",
        "agents": agents_status
    } 