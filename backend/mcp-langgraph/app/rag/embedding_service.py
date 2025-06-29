"""
Embedding Service for RAG System

This module handles text embedding using the intfloat/multilingual-e5-large model.
Supports multilingual input and batch processing for efficient embedding generation.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
from app.config.base import rag_config
from app.logger import get_logger, get_performance_logger, log_exception

# Use centralized logging
logger = get_logger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using intfloat/multilingual-e5-large model.
    
    This service provides:
    - Multilingual text embedding
    - Batch processing for efficiency
    - Query and document embedding with proper prefixes
    - Async support for non-blocking operations
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the embedding model to use
        """
        self.model_name = model_name or rag_config.EMBEDDING_MODEL
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model_loaded = False
        
        logger.info(f"Initializing EmbeddingService with model: {self.model_name}")
        logger.info(f"Using device: {self.device}")
    
    async def _load_model(self):
        """Load the embedding model asynchronously."""
        if self._model_loaded:
            return
            
        try:
            with get_performance_logger(logger, "model_loading"):
                # Load model in a thread to avoid blocking
                loop = asyncio.get_event_loop()
                self.model = await loop.run_in_executor(
                    None, 
                    lambda: SentenceTransformer(self.model_name, device=self.device)
                )
                self._model_loaded = True
                logger.info(f"Successfully loaded model: {self.model_name}")
            
        except Exception as e:
            log_exception(logger, "Failed to load embedding model", e)
            raise RuntimeError(f"Could not load embedding model: {e}")
    
    def _add_prefix(self, text: str, is_query: bool = False) -> str:
        """
        Add appropriate prefix for multilingual-e5-large model.
        
        Args:
            text: Input text to embed
            is_query: Whether this is a query (True) or document (False)
            
        Returns:
            Text with appropriate prefix
        """
        prefix = "query" if is_query else "passage"
        logger.debug(f"Adding prefix '{prefix}' to text of length {len(text)}")
        return f"{prefix}: {text}"
    
    async def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a single query text.
        
        Args:
            query: Query text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        await self._load_model()
        
        logger.debug(f"Embedding query: '{query[:50]}...' (length: {len(query)})")
        
        # Add query prefix for better performance
        prefixed_query = self._add_prefix(query, is_query=True)
        
        try:
            with get_performance_logger(logger, "query_embedding"):
                # Run embedding in executor to avoid blocking
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None,
                    lambda: self.model.encode([prefixed_query], normalize_embeddings=True)
                )
                
                result = embedding[0]
                logger.debug(f"Generated query embedding with shape: {result.shape}")
                return result
            
        except Exception as e:
            log_exception(logger, f"Failed to embed query: '{query[:100]}...'", e)
            raise RuntimeError(f"Query embedding failed: {e}")
    
    async def embed_documents(self, documents: List[str]) -> List[np.ndarray]:
        """
        Embed multiple documents with batch processing.
        
        Args:
            documents: List of document texts to embed
            
        Returns:
            List of embedding vectors
        """
        await self._load_model()
        
        if not documents:
            logger.warning("No documents provided for embedding")
            return []
        
        logger.info(f"Embedding {len(documents)} documents")
        
        # Add document prefixes
        prefixed_docs = [self._add_prefix(doc, is_query=False) for doc in documents]
        
        try:
            with get_performance_logger(logger, f"document_embedding_{len(documents)}_docs"):
                # Process in batches to manage memory
                batch_size = rag_config.BATCH_SIZE
                all_embeddings = []
                
                for i in range(0, len(prefixed_docs), batch_size):
                    batch = prefixed_docs[i:i + batch_size]
                    batch_start = i + 1
                    batch_end = min(i + batch_size, len(prefixed_docs))
                    
                    logger.debug(f"Processing batch {batch_start}-{batch_end}/{len(prefixed_docs)}")
                    
                    # Run batch embedding in executor
                    loop = asyncio.get_event_loop()
                    batch_embeddings = await loop.run_in_executor(
                        None,
                        lambda b=batch: self.model.encode(b, normalize_embeddings=True)
                    )
                    
                    all_embeddings.extend(batch_embeddings)
                    
                    # Log progress for large batches
                    if len(prefixed_docs) > batch_size:
                        progress_pct = (batch_end / len(prefixed_docs)) * 100
                        logger.info(f"Embedding progress: {batch_end}/{len(prefixed_docs)} ({progress_pct:.1f}%)")
                
                logger.info(f"Successfully embedded {len(all_embeddings)} documents")
                return all_embeddings
            
        except Exception as e:
            log_exception(logger, f"Failed to embed {len(documents)} documents", e)
            raise RuntimeError(f"Document embedding failed: {e}")
    
    async def embed_single_document(self, document: str) -> np.ndarray:
        """
        Embed a single document.
        
        Args:
            document: Document text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        logger.debug(f"Embedding single document of length: {len(document)}")
        embeddings = await self.embed_documents([document])
        return embeddings[0] if embeddings else None
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.
        
        Returns:
            Embedding dimension
        """
        dimension = rag_config.EMBEDDING_DIMENSION
        logger.debug(f"Embedding dimension: {dimension}")
        return dimension
    
    async def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score
        """
        try:
            # Normalize embeddings if not already normalized
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                logger.warning("Zero-norm embedding detected in similarity computation")
                return 0.0
            
            # Compute cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            similarity_score = float(similarity)
            
            logger.debug(f"Computed similarity score: {similarity_score:.4f}")
            return similarity_score
            
        except Exception as e:
            log_exception(logger, "Failed to compute similarity", e)
            return 0.0
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the embedding service.
        
        Returns:
            Health check results
        """
        logger.info("Performing embedding service health check")
        
        try:
            with get_performance_logger(logger, "health_check"):
                await self._load_model()
                
                # Test embedding generation
                test_text = "health check test"
                test_embedding = await self.embed_query(test_text)
                
                health_status = {
                    "status": "healthy",
                    "model_name": self.model_name,
                    "device": self.device,
                    "embedding_dimension": len(test_embedding),
                    "model_loaded": self._model_loaded,
                    "test_embedding_shape": test_embedding.shape,
                    "test_text": test_text
                }
                
                logger.info("Embedding service health check passed")
                return health_status
            
        except Exception as e:
            health_status = {
                "status": "unhealthy",
                "error": str(e),
                "model_name": self.model_name,
                "device": self.device,
                "model_loaded": self._model_loaded
            }
            
            log_exception(logger, "Embedding service health check failed", e)
            return health_status


# Global embedding service instance
embedding_service = EmbeddingService()
logger.info("Global embedding service instance created") 