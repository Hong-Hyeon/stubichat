from openai import OpenAI
from typing import List
from app.core.config import settings
from app.utils.logger import get_logger


class GPTEmbeddingService:
    """Service for creating embeddings using OpenAI GPT models."""

    def __init__(self):
        self.logger = get_logger("gpt_embedding_service")
        self.model = settings.openai_model
        
        # Configure OpenAI client
        if settings.openai_api_key:
            self.client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url if settings.openai_base_url else None
            )
        else:
            self.logger.warning("OpenAI API key not provided")
            self.client = None

    async def create_embedding(self, text: str) -> List[float]:
        """Create an embedding for the given text."""
        try:
            if not self.client:
                raise ValueError("OpenAI API key not configured")

            # Create embedding using OpenAI API
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            
            embedding = response.data[0].embedding
            self.logger.info(f"Created embedding for text (length: {len(text)})")
            
            return embedding

        except Exception as e:
            self.logger.error(f"Error creating embedding: {str(e)}")
            raise

    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for multiple texts in batch."""
        try:
            if not self.client:
                raise ValueError("OpenAI API key not configured")

            # Create embeddings using OpenAI API
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            self.logger.info(f"Created {len(embeddings)} embeddings in batch")
            
            return embeddings

        except Exception as e:
            self.logger.error(f"Error creating batch embeddings: {str(e)}")
            raise

    def get_model_info(self) -> dict:
        """Get information about the embedding model."""
        return {
            "model": self.model,
            "provider": "OpenAI",
            "api_key_configured": bool(self.client is not None)
        } 