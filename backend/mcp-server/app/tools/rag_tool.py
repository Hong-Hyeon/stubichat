"""
RAG (Retrieval-Augmented Generation) Tool for MCP Server.
This tool provides vector search capabilities using the embedding server.
"""

import httpx
import json
from typing import List, Dict, Any, Optional
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.utils.logger import get_logger
from app.core.config import get_settings
from app.services.geocoding_service import GeocodingService

# Create router
router = APIRouter(prefix="/rag", tags=["rag"])


class SearchRequest(BaseModel):
    """Request model for vector search."""
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results to return")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Search filters")


class GeoSearchRequest(BaseModel):
    """Request model for geospatial vector search within radius."""
    query: str = Field(..., description="Search query")
    lat: float = Field(..., description="Center latitude")
    lon: float = Field(..., description="Center longitude")
    radius_m: int = Field(default=1000, description="Search radius in meters")
    top_k: int = Field(default=10, description="Number of results to return")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata filters")
    order_by: str = Field(default='hybrid', description="Rank by 'similarity'|'distance'|'hybrid'")
    alpha: float = Field(default=0.7, ge=0.0, le=1.0, description="Hybrid weight")



class SearchResult(BaseModel):
    """Model for search result."""
    document_id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    similarity_score: float = Field(..., description="Similarity score")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Document metadata")
    distance_m: Optional[float] = Field(default=None, description="Distance in meters if geo search")
    hybrid_score: Optional[float] = Field(default=None, description="Hybrid score if used")


class RAGTool:
    """RAG tool for vector search and retrieval."""
    
    def __init__(self):
        self.logger = get_logger("rag_tool")
        settings = get_settings()
        self.embedding_server_url = getattr(settings, 'embedding_server_url', 'http://embedding-server:8003')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.geocoder = GeocodingService()
        # Simple Korean location parser patterns
        self.coord_pattern = re.compile(r"(?P<lat>\d{2}\.\d+)[,\s]+(?P<lon>\d{3}\.\d+)")
        # e.g., "강남구", "세곡동" etc.
        self.gu_pattern = re.compile(r"(?P<gu>..구)")
        self.dong_pattern = re.compile(r"(?P<dong>..동)")
    
    async def search_similar_documents(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
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
                "similarity_threshold": similarity_threshold,
                "filters": filters
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

    async def search_similar_documents_geo(
        self,
        query: str,
        lat: float,
        lon: float,
        radius_m: int = 1000,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = 'hybrid',
        alpha: float = 0.7
    ) -> List[SearchResult]:
        """Search for similar documents within radius."""
        try:
            self.logger.info(f"Geo searching near ({lat},{lon}) radius {radius_m}m for: {query}")
            payload = {
                "query": query,
                "lat": lat,
                "lon": lon,
                "radius_m": radius_m,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold,
                "filters": filters,
                "order_by": order_by,
                "alpha": alpha
            }
            response = await self.client.post(f"{self.embedding_server_url}/embed/search_geo", json=payload)
            if response.status_code != 200:
                raise Exception(f"Embedding server error: {response.status_code} - {response.text}")
            data = response.json()
            results = []
            for result_data in data.get("results", []):
                results.append(SearchResult(
                    document_id=result_data["document_id"],
                    content=result_data["content"],
                    similarity_score=result_data["similarity_score"],
                    metadata=result_data.get("metadata"),
                    distance_m=result_data.get("distance_m"),
                    hybrid_score=result_data.get("hybrid_score")
                ))
            return results
        except Exception as e:
            self.logger.error(f"Error in geo search: {str(e)}")
            raise


    async def resolve_location_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse natural language to approximate a location seed.
        - Prefer explicit coordinates '37.49, 127.05'
        - Else use '구/동' metadata to seed filter
        """
        m = self.coord_pattern.search(text)
        if m:
            return {"lat": float(m.group("lat")), "lon": float(m.group("lon"))}
        gu = None
        dong = None
        m = self.gu_pattern.search(text)
        if m:
            gu = m.group("gu")
        m = self.dong_pattern.search(text)
        if m:
            dong = m.group("dong")
        if gu or dong:
            return {"filters": {k: v for k, v in {"gu": gu, "dong": dong}.items() if v}}
        return None

    async def search_nearby_from_prompt(
        self,
        prompt: str,
        default_lat: Optional[float] = None,
        default_lon: Optional[float] = None,
        radius_m: int = 1500,
        top_k: int = 10,
        similarity_threshold: float = 0.6
    ) -> List[SearchResult]:
        """High-level helper: infer location from prompt and run geo or filtered search."""
        hint = await self.resolve_location_from_text(prompt)
        if hint and "lat" in hint and "lon" in hint:
            return await self.search_similar_documents_geo(
                query=prompt,
                lat=hint["lat"],
                lon=hint["lon"],
                radius_m=radius_m,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                order_by='hybrid',
                alpha=0.7
            )
        filters = None
        if hint and "filters" in hint:
            filters = hint["filters"]
        if default_lat is not None and default_lon is not None:
            return await self.search_similar_documents_geo(
                query=prompt,
                lat=default_lat,
                lon=default_lon,
                radius_m=radius_m,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                filters=filters,
                order_by='hybrid',
                alpha=0.7
            )
        # Try geocoding full text as last resort
        geo = await self.geocoder.geocode_text(prompt)
        if geo:
            lat, lon = geo
            return await self.search_similar_documents_geo(
                query=prompt,
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                filters=filters,
                order_by='hybrid',
                alpha=0.7
            )
        # Fallback to non-geo filtered search
        return await self.search_similar_documents(
            query=prompt,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            filters=filters
        )


class PromptSearchRequest(BaseModel):
    """Prompt-driven search with optional fallback coordinates."""
    prompt: str = Field(..., description="User prompt containing intent and possibly location")
    lat: Optional[float] = Field(default=None, description="Fallback latitude if prompt lacks coords")
    lon: Optional[float] = Field(default=None, description="Fallback longitude if prompt lacks coords")
    radius_m: int = Field(default=1500, description="Search radius in meters")
    top_k: int = Field(default=10, description="Number of results to return")
    similarity_threshold: float = Field(default=0.6, description="Similarity threshold")
    
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
async def search_documents_endpoint(request: SearchRequest):
    """
    Search for documents similar to the query.
    """
    try:
        results = await rag_tool.search_similar_documents(
            request.query,
            request.top_k,
            request.similarity_threshold,
            request.filters
        )
        return {
            "query": request.query,
            "results": [result.dict() for result in results],
            "total_results": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search_geo")
async def search_documents_geo_endpoint(request: GeoSearchRequest):
    """Geo constrained semantic search."""
    try:
        results = await rag_tool.search_similar_documents_geo(
            request.query,
            request.lat,
            request.lon,
            request.radius_m,
            request.top_k,
            request.similarity_threshold,
            request.filters,
            request.order_by,
            request.alpha
        )
        return {
            "query": request.query,
            "results": [r.dict() for r in results],
            "total_results": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search_prompt")
async def search_documents_prompt_endpoint(request: PromptSearchRequest):
    """Natural-language location search endpoint."""
    try:
        results = await rag_tool.search_nearby_from_prompt(
            prompt=request.prompt,
            default_lat=request.lat,
            default_lon=request.lon,
            radius_m=request.radius_m,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )
        return {
            "query": request.prompt,
            "results": [r.dict() for r in results],
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
async def search_documents(query: str, top_k: int = 5, similarity_threshold: float = 0.7, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Search for documents similar to the query.
    
    Args:
        query: Search query
        top_k: Number of results to return
        
    Returns:
        List of search results
    """
    results = await rag_tool.search_similar_documents(query, top_k, similarity_threshold, filters)
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