import uvicorn
from app.factory.app_factory import create_app
from app.core.config import get_settings

# Create the FastAPI application using the factory pattern
app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 