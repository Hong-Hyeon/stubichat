from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import uuid
import time
from datetime import datetime

from app.models.embedding_models import (
    EmbeddingRequest, EmbeddingResponse,
    SearchRequest, SearchResponse, SearchResult
)
from app.services.gpt_embedding_service import GPTEmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.utils.logger import get_logger

router = APIRouter(prefix="/embed", tags=["embedding"])
logger = get_logger("embedding_routes")


# Global service instances
_embedding_service: GPTEmbeddingService = None
_vector_store_service: VectorStoreService = None


def set_services(embedding_service: GPTEmbeddingService, vector_store_service: VectorStoreService):
    """Set global service instances."""
    global _embedding_service, _vector_store_service
    _embedding_service = embedding_service
    _vector_store_service = vector_store_service


def get_embedding_service() -> GPTEmbeddingService:
    """Get embedding service instance."""
    if _embedding_service is None:
        raise HTTPException(status_code=500, detail="Embedding service not initialized")
    return _embedding_service


def get_vector_store_service() -> VectorStoreService:
    """Get vector store service instance."""
    if _vector_store_service is None:
        raise HTTPException(status_code=500, detail="Vector store service not initialized")
    return _vector_store_service


@router.post("/", response_model=EmbeddingResponse)
async def create_embedding(
    request: EmbeddingRequest,
    embedding_svc: GPTEmbeddingService = Depends(get_embedding_service),
    vector_svc: VectorStoreService = Depends(get_vector_store_service)
):
    """Create an embedding for a single text."""
    try:
        start_time = time.time()
        
        # Create embedding
        embedding = await embedding_svc.create_embedding(request.text)
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Store in vector database
        await vector_svc.store_embedding(
            document_id=document_id,
            content=request.text,
            embedding=embedding,
            metadata=request.metadata
        )
        
        processing_time = time.time() - start_time
        
        logger.info(f"Embedding created successfully in {processing_time:.3f}s")
        
        return EmbeddingResponse(
            embedding=embedding,
            model=embedding_svc.model,
            text=request.text,
            metadata=request.metadata
        )
        
    except Exception as e:
        logger.error(f"Error creating embedding: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create embedding: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_embeddings(
    request: SearchRequest,
    embedding_svc: GPTEmbeddingService = Depends(get_embedding_service),
    vector_svc: VectorStoreService = Depends(get_vector_store_service)
):
    """Search for similar embeddings."""
    try:
        start_time = time.time()
        
        # Create embedding for query
        query_embedding = await embedding_svc.create_embedding(request.query)
        
        # Search for similar documents
        search_results = await vector_svc.search_similar(
            query_embedding=query_embedding,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )
        
        # Convert to response format
        results = []
        for result in search_results:
            results.append(SearchResult(
                document_id=result["document_id"],
                content=result["content"],
                similarity_score=result["similarity_score"],
                metadata=result["metadata"]
            ))
        
        search_time = time.time() - start_time
        
        logger.info(f"Search completed in {search_time:.3f}s, found {len(results)} results")
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            search_time=search_time
        )
        
    except Exception as e:
        logger.error(f"Error searching embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search embeddings: {str(e)}")


@router.get("/statistics")
async def get_statistics(
    vector_svc: VectorStoreService = Depends(get_vector_store_service)
):
    """Get embedding database statistics."""
    try:
        stats = await vector_svc.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}") 