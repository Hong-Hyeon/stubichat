from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.services.gpt_embedding_service import GPTEmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.api.embedding_routes import router as embedding_router, set_services
from app.utils.logger import get_logger
import asyncio


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    logger = get_logger("app_factory")
    
    # Create FastAPI app
    app = FastAPI(
        title="Stubichat Embedding Server",
        description="Embedding service for Stubichat application",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize services
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting up embedding server...")
        
        try:
            # Initialize services
            embedding_service = GPTEmbeddingService()
            vector_store_service = VectorStoreService()
            
            # Initialize database
            await vector_store_service.initialize_database()
            
            # Set services for dependency injection
            set_services(embedding_service, vector_store_service)
            
            logger.info("Embedding server started successfully")
            
        except Exception as e:
            logger.error(f"Error during startup: {str(e)}")
            raise
    
    # Add routes
    app.include_router(embedding_router)
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "embedding-server",
            "version": "1.0.0"
        }
    
    return app 