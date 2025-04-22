from enum import Enum
from pydantic import BaseModel
from typing import Dict, Optional


class ModelType(str, Enum):
    EXAONE = "exaone"
    NLLB = "nllb"


class MCPMessage(BaseModel):
    prompt: str
    model: Optional[str] = "exaone-3.5"
    parameters: Optional[Dict] = {}


class AgentResponse(BaseModel):
    status: str
    response: Dict


class RoutingDecision(BaseModel):
    model_type: ModelType
    reason: str 