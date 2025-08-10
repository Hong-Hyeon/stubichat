from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from typing import Literal
from datetime import datetime


class EmbeddingRequest(BaseModel):
    """Request model for creating embeddings."""
    text: str = Field(..., description="Text to embed")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class EmbeddingResponse(BaseModel):
    """Response model for embedding creation."""
    document_id: str = Field(..., description="Stored document ID")
    embedding: List[float] = Field(..., description="Generated embedding vector")
    model: str = Field(..., description="Model used for embedding")
    text: str = Field(..., description="Original text")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BatchEmbeddingRequest(BaseModel):
    """Request model for batch embedding creation."""
    documents: List[Dict[str, Any]] = Field(..., description="List of documents to embed")
    batch_size: Optional[int] = Field(default=100, description="Batch size for processing")


class BatchEmbeddingResponse(BaseModel):
    """Response model for batch embedding creation."""
    job_id: str = Field(..., description="Job ID for tracking")
    total_documents: int = Field(..., description="Total number of documents")
    status: str = Field(..., description="Job status")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str = Field(..., description="Job ID")
    status: str = Field(..., description="Job status")
    total_documents: int = Field(..., description="Total number of documents")
    processed_documents: int = Field(..., description="Number of processed documents")
    failed_documents: int = Field(..., description="Number of failed documents")
    progress: float = Field(..., description="Progress percentage")
    created_at: datetime = Field(..., description="Job creation time")
    updated_at: datetime = Field(..., description="Last update time")
    errors: Optional[List[str]] = Field(default=None, description="Error messages")


class SearchRequest(BaseModel):
    """Request model for vector search."""
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=10, description="Number of results to return")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Search filters")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold")


class GeoSearchRequest(BaseModel):
    """Request model for geospatial vector search within radius."""
    query: str = Field(..., description="Search query")
    lat: float = Field(..., description="Center latitude")
    lon: float = Field(..., description="Center longitude")
    radius_m: int = Field(default=1000, description="Search radius in meters")
    top_k: int = Field(default=10, description="Number of results to return")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata filters")
    order_by: Literal['similarity', 'distance', 'hybrid'] = Field(default='hybrid', description="Ranking criterion")
    alpha: float = Field(default=0.7, ge=0.0, le=1.0, description="Hybrid weight: similarity(alpha) vs distance(1-alpha)")


class SearchResult(BaseModel):
    """Model for search result."""
    document_id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    similarity_score: float = Field(..., description="Similarity score")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Document metadata")


class SearchResponse(BaseModel):
    """Response model for vector search."""
    query: str = Field(..., description="Original query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    search_time: float = Field(..., description="Search execution time")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database: str = Field(..., description="Database status")
    redis: str = Field(..., description="Redis status")
    openai: str = Field(..., description="OpenAI API status")
    celery: str = Field(..., description="Celery status")


# Table Management Models
class TableCreationRequest(BaseModel):
    """Request model for creating embedding tables."""
    table_name: str = Field(..., description="Name of the table to create", min_length=1, max_length=63)
    description: Optional[str] = Field(default=None, description="Optional description for the table")


class TableInfo(BaseModel):
    """Model for table information."""
    table_name: str = Field(..., description="Name of the table")
    description: Optional[str] = Field(default=None, description="Table description")
    document_count: int = Field(..., description="Number of documents in the table")
    created_at: datetime = Field(..., description="When the table was created")
    last_updated: datetime = Field(..., description="Last update time")


class TableCreationResponse(BaseModel):
    """Response model for table creation."""
    success: bool = Field(..., description="Whether the table was created successfully")
    table_name: str = Field(..., description="Name of the created table")
    table_id: str = Field(..., description="Unique identifier for the table")
    table_schema: Dict[str, Any] = Field(..., description="Table schema information")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TableListResponse(BaseModel):
    """Response model for listing tables."""
    tables: List[TableInfo] = Field(..., description="List of available tables")
    total_count: int = Field(..., description="Total number of tables")


class TableDeletionResponse(BaseModel):
    """Response model for table deletion."""
    success: bool = Field(..., description="Whether the table was deleted successfully")
    table_name: str = Field(..., description="Name of the deleted table")
    deleted_at: datetime = Field(default_factory=datetime.utcnow)


class TableSwitchResponse(BaseModel):
    """Response model for switching active table."""
    success: bool = Field(..., description="Whether the table switch was successful")
    previous_table: Optional[str] = Field(default=None, description="Previously active table")
    current_table: str = Field(..., description="Currently active table")
    switched_at: datetime = Field(default_factory=datetime.utcnow)
