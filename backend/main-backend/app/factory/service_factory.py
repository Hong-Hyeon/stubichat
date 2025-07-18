from typing import Optional
from app.core.config import Settings
from app.services.llm_client import LLMClient
from app.core.graph import create_conversation_graph


class ServiceFactory:
    """Factory for creating and managing service dependencies."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm_client: Optional[LLMClient] = None
        self._conversation_graph = None
    
    @property
    def llm_client(self) -> LLMClient:
        """Get or create LLM client instance."""
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client
    
    @property
    def conversation_graph(self):
        """Get or create conversation graph instance."""
        if self._conversation_graph is None:
            self._conversation_graph = create_conversation_graph()
        return self._conversation_graph
    
    def reset(self):
        """Reset all service instances (useful for testing)."""
        self._llm_client = None
        self._conversation_graph = None


# Global service factory instance
def get_service_factory(settings: Optional[Settings] = None) -> ServiceFactory:
    """Get service factory instance."""
    from app.core.config import get_settings
    
    if settings is None:
        settings = get_settings()
    
    return ServiceFactory(settings) 