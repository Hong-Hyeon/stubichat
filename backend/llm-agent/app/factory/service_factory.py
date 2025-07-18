from typing import Optional
from app.core.config import Settings
from app.services.openai_service import OpenAIService


class ServiceFactory:
    """Factory for creating and managing service dependencies."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._openai_service: Optional[OpenAIService] = None
    
    @property
    def openai_service(self) -> OpenAIService:
        """Get or create OpenAI service instance."""
        if self._openai_service is None:
            self._openai_service = OpenAIService()
        return self._openai_service
    
    def reset(self):
        """Reset all service instances (useful for testing)."""
        self._openai_service = None


# Global service factory instance
def get_service_factory(settings: Optional[Settings] = None) -> ServiceFactory:
    """Get service factory instance."""
    from app.core.config import get_settings
    
    if settings is None:
        settings = get_settings()
    
    return ServiceFactory(settings) 