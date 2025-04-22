from typing import Dict, Optional, List
from pydantic import BaseModel


class Agent(BaseModel):
    id: str
    name: str
    description: str
    endpoint: str
    status: str = "active"
    metadata: Dict = {}


class MessageControlProtocol:
    def __init__(self):
        self._agents: Dict[str, Agent] = {}

    def register_agent(self, agent: Agent) -> None:
        """새로운 에이전트 등록"""
        self._agents[agent.id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        """에이전트 등록 해제"""
        if agent_id in self._agents:
            del self._agents[agent_id]

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """에이전트 조회"""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Agent]:
        """등록된 모든 에이전트 목록 반환"""
        return list(self._agents.values())

    def update_agent_status(self, agent_id: str, status: str) -> None:
        """에이전트 상태 업데이트"""
        if agent_id in self._agents:
            self._agents[agent_id].status = status 