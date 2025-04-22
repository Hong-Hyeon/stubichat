from .mcp import MessageControlProtocol
from .config import AGENTS


# MCP 인스턴스 생성
mcp = MessageControlProtocol()

# 에이전트 등록
for agent in AGENTS.values():
    mcp.register_agent(agent) 