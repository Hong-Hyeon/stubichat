# Import routers to register them with FastAPI
from .echo_tool import router as echo_router
from .web_search_tool import router as web_search_router
from .rag_tool import router as rag_router

# List of all routers
__all__ = ["echo_router", "web_search_router", "rag_router"] 