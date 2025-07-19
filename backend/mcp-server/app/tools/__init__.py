# Import routers to register them with FastAPI
from .echo_tool import router as echo_router

# List of all routers
__all__ = ["echo_router"] 