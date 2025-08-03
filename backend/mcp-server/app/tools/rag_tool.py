"""
RAG (Retrieval-Augmented Generation) Tool for MCP Server.
This tool provides vector search capabilities using the embedding server.
"""

import httpx
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.utils.logger import get_logger
from app.core.config import settings

# Create router
router = APIRouter(prefix="/rag", tags=["rag"])


class SearchRequest(BaseModel):
    """Request model for vector search."""
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results to return")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold")


class SearchResult(BaseModel):
    """Model for search result."""
    document_id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    similarity_score: float = Field(..., description="Similarity score")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Document metadata")


class RAGTool:
    """RAG tool for vector search and retrieval."""
    
    def __init__(self):
        self.logger = get_logger("rag_tool")
        self.embedding_server_url = getattr(settings, 'EMBEDDING_SERVER_URL', 'http://embedding-server:8003')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_similar_documents(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[SearchResult]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query: Search query
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of search results
        """
        try:
            self.logger.info(f"Searching for documents similar to: {query}")
            
            # Prepare search request
            search_request = {
                "query": query,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold
            }
            
            # Make request to embedding server
            response = await self.client.post(
                f"{self.embedding_server_url}/embed/search",
                json=search_request
            )
            
            if response.status_code != 200:
                raise Exception(f"Embedding server error: {response.status_code} - {response.text}")
            
            # Parse response
            search_response = response.json()
            results = []
            
            for result_data in search_response.get("results", []):
                result = SearchResult(
                    document_id=result_data["document_id"],
                    content=result_data["content"],
                    similarity_score=result_data["similarity_score"],
                    metadata=result_data.get("metadata")
                )
                results.append(result)
            
            self.logger.info(f"Found {len(results)} similar documents")
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching documents: {str(e)}")
            raise
    
    async def create_embedding(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an embedding for the given text.
        
        Args:
            text: Text to embed
            metadata: Optional metadata
            
        Returns:
            Embedding response
        """
        try:
            self.logger.info(f"Creating embedding for text (length: {len(text)})")
            
            # Prepare embedding request
            embedding_request = {
                "text": text,
                "metadata": metadata or {}
            }
            
            # Make request to embedding server
            response = await self.client.post(
                f"{self.embedding_server_url}/embed/",
                json=embedding_request
            )
            
            if response.status_code != 200:
                raise Exception(f"Embedding server error: {response.status_code} - {response.text}")
            
            result = response.json()
            self.logger.info("Embedding created successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating embedding: {str(e)}")
            raise
    
    async def batch_embed_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> str:
        """
        Create embeddings for multiple documents in batch.
        
        Args:
            documents: List of documents to embed
            batch_size: Batch size for processing
            
        Returns:
            Job ID for tracking
        """
        try:
            self.logger.info(f"Creating batch embedding job for {len(documents)} documents")
            
            # Prepare batch request
            batch_request = {
                "documents": documents,
                "batch_size": batch_size
            }
            
            # Make request to embedding server
            response = await self.client.post(
                f"{self.embedding_server_url}/batch/embed",
                json=batch_request
            )
            
            if response.status_code != 200:
                raise Exception(f"Embedding server error: {response.status_code} - {response.text}")
            
            result = response.json()
            job_id = result["job_id"]
            
            self.logger.info(f"Batch embedding job created: {job_id}")
            return job_id
            
        except Exception as e:
            self.logger.error(f"Error creating batch embedding job: {str(e)}")
            raise
    
    async def get_batch_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a batch embedding job.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            Job status information
        """
        try:
            self.logger.info(f"Checking status for batch job: {job_id}")
            
            # Make request to embedding server
            response = await self.client.get(
                f"{self.embedding_server_url}/batch/status/{job_id}"
            )
            
            if response.status_code != 200:
                raise Exception(f"Embedding server error: {response.status_code} - {response.text}")
            
            result = response.json()
            self.logger.info(f"Batch job status: {result['status']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting batch status: {str(e)}")
            raise
    
    async def get_embedding_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the embedding database.
        
        Returns:
            Database statistics
        """
        try:
            self.logger.info("Getting embedding database statistics")
            
            # Make request to embedding server
            response = await self.client.get(
                f"{self.embedding_server_url}/embed/statistics"
            )
            
            if response.status_code != 200:
                raise Exception(f"Embedding server error: {response.status_code} - {response.text}")
            
            result = response.json()
            self.logger.info("Retrieved embedding statistics")
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting embedding statistics: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of the embedding server.
        
        Returns:
            Health status
        """
        try:
            self.logger.info("Checking embedding server health")
            
            # Make request to embedding server
            response = await self.client.get(
                f"{self.embedding_server_url}/health"
            )
            
            if response.status_code != 200:
                raise Exception(f"Embedding server error: {response.status_code} - {response.text}")
            
            result = response.json()
            self.logger.info("Embedding server health check completed")
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking embedding server health: {str(e)}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Create global instance
rag_tool = RAGTool()


# API Endpoints
@router.post("/search")
async def search_documents_endpoint(query: str, top_k: int = 5):
    """
    Search for documents similar to the query.
    """
    try:
        results = await rag_tool.search_similar_documents(query, top_k)
        return {
            "query": query,
            "results": [result.dict() for result in results],
            "total_results": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embed")
async def create_embedding_endpoint(text: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Create an embedding for a document.
    """
    try:
        result = await rag_tool.create_embedding(text, metadata)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_embedding_stats_endpoint():
    """
    Get embedding database statistics.
    """
    try:
        return await rag_tool.get_embedding_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check_endpoint():
    """
    Check embedding server health.
    """
    try:
        return await rag_tool.health_check()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions for internal use
async def search_documents(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search for documents similar to the query.
    
    Args:
        query: Search query
        top_k: Number of results to return
        
    Returns:
        List of search results
    """
    results = await rag_tool.search_similar_documents(query, top_k)
    return [result.dict() for result in results]


async def create_document_embedding(text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create an embedding for a document.
    
    Args:
        text: Document text
        metadata: Optional metadata
        
    Returns:
        Embedding response
    """
    return await rag_tool.create_embedding(text, metadata)


async def get_embedding_stats() -> Dict[str, Any]:
    """
    Get embedding database statistics.
    
    Returns:
        Database statistics
    """
    return await rag_tool.get_embedding_statistics() 