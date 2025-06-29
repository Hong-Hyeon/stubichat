"""
Vector Store Service for RAG System

This module handles vector storage and retrieval using Supabase PostgreSQL
with pgvector extension for efficient similarity search.
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass, asdict
from datetime import datetime
import json

try:
    from supabase import create_client, Client
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
except ImportError as e:
    from app.logger import get_logger, log_exception
    logger = get_logger(__name__)
    log_exception(logger, "Failed to import required dependencies", e)
    logger.error("Please install: pip install supabase psycopg2-binary")
    raise

from app.config.base import (
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL, rag_config
)
from app.rag.text_chunker import TextChunk
from app.logger import get_logger, get_performance_logger, log_exception

# Use centralized logging
logger = get_logger(__name__)


@dataclass
class DocumentMetadata:
    """
    Document metadata structure for storage.
    
    Attributes:
        document_id: Unique document identifier
        title: Document title
        source: Document source/origin
        language: Document language
        created_at: Creation timestamp
        updated_at: Last update timestamp
        custom_metadata: Additional custom metadata
    """
    document_id: str
    title: Optional[str] = None
    source: Optional[str] = None
    language: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    custom_metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class RetrievalResult:
    """
    Result from vector similarity search.
    
    Attributes:
        chunk_id: Unique chunk identifier
        document_id: Parent document identifier
        text: Chunk text content
        similarity_score: Cosine similarity score
        metadata: Chunk and document metadata
        embedding: Optional embedding vector
    """
    chunk_id: str
    document_id: str
    text: str
    similarity_score: float
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None


class VectorStore:
    """
    Vector store service using Supabase PostgreSQL with pgvector.
    
    Provides:
    - Document and chunk storage with embeddings
    - Vector similarity search
    - Metadata management
    - Batch operations for efficiency
    """
    
    def __init__(self):
        """Initialize the vector store."""
        self.supabase = None
        self.db_connection = None
        self._initialized = False
        
        logger.info("Initializing VectorStore with Supabase")
    
    async def initialize(self):
        """Initialize connections and create tables if needed."""
        if self._initialized:
            logger.debug("VectorStore already initialized, skipping")
            return
        
        try:
            with get_performance_logger(logger, "vector_store_initialization"):
                # Initialize Supabase client
                logger.debug(f"Connecting to Supabase: {SUPABASE_URL}")
                self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                
                # Test connection
                try:
                    _ = self.supabase.table(rag_config.METADATA_TABLE_NAME).select("count").execute()
                    logger.debug("Supabase connection test successful")
                except Exception as e:
                    logger.warning(f"Supabase connection test failed: {e}, continuing with initialization")
                
                # Create tables if they don't exist
                await self._create_tables()
                
                self._initialized = True
                logger.info("Successfully initialized VectorStore")
            
        except Exception as e:
            log_exception(logger, "Failed to initialize VectorStore", e)
            raise RuntimeError(f"VectorStore initialization failed: {e}")
    
    async def _create_tables(self):
        """Create necessary tables with pgvector extension."""
        try:
            with get_performance_logger(logger, "table_creation"):
                logger.info("Creating/verifying database tables")
                
                # Connect directly to PostgreSQL for table creation
                import psycopg2
                logger.debug(f"Connecting to PostgreSQL: {DATABASE_URL[:50]}...")
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                
                # Enable pgvector extension
                logger.debug("Enabling pgvector extension")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Create document metadata table
                logger.debug(f"Creating metadata table: {rag_config.METADATA_TABLE_NAME}")
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {rag_config.METADATA_TABLE_NAME} (
                        document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        title TEXT,
                        source TEXT,
                        language TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        custom_metadata JSONB DEFAULT '{{}}'::jsonb
                    );
                """)
                
                # Create document embeddings table
                logger.debug(f"Creating embeddings table: {rag_config.VECTOR_TABLE_NAME}")
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {rag_config.VECTOR_TABLE_NAME} (
                        chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        document_id UUID REFERENCES {rag_config.METADATA_TABLE_NAME}(document_id) ON DELETE CASCADE,
                        text TEXT NOT NULL,
                        embedding VECTOR({rag_config.EMBEDDING_DIMENSION}),
                        chunk_index INTEGER,
                        token_count INTEGER,
                        start_index INTEGER,
                        end_index INTEGER,
                        chunk_metadata JSONB DEFAULT '{{}}'::jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """)
                
                # Create indexes for better performance
                logger.debug("Creating vector similarity index")
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{rag_config.VECTOR_TABLE_NAME}_embedding 
                    ON {rag_config.VECTOR_TABLE_NAME} USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
                
                logger.debug("Creating document ID index")
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{rag_config.VECTOR_TABLE_NAME}_document_id
                    ON {rag_config.VECTOR_TABLE_NAME} (document_id);
                """)
                
                conn.commit()
                cursor.close()
                conn.close()
                
                logger.info("Successfully created/verified database tables")
            
        except Exception as e:
            log_exception(logger, "Failed to create tables", e)
            raise
    
    async def store_document(self,
                           text: str,
                           embeddings: List[np.ndarray],
                           chunks: List[TextChunk],
                           metadata: DocumentMetadata) -> str:
        """
        Store a document with its chunks and embeddings.
        
        Args:
            text: Original document text
            embeddings: List of chunk embeddings
            chunks: List of text chunks
            metadata: Document metadata
            
        Returns:
            Document ID
        """
        await self.initialize()
        
        if len(embeddings) != len(chunks):
            error_msg = f"Embedding count ({len(embeddings)}) != chunk count ({len(chunks)})"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Storing document '{metadata.title}' with {len(chunks)} chunks")
        
        try:
            with get_performance_logger(logger, f"store_document_{len(chunks)}_chunks"):
                # Store document metadata first
                logger.debug("Storing document metadata")
                doc_metadata = asdict(metadata)
                doc_metadata['custom_metadata'] = Json(doc_metadata.get('custom_metadata', {}))
                
                response = self.supabase.table(rag_config.METADATA_TABLE_NAME).insert(doc_metadata).execute()
                document_id = response.data[0]['document_id']
                logger.debug(f"Document metadata stored with ID: {document_id}")
                
                # Store chunks with embeddings
                logger.debug(f"Preparing {len(chunks)} chunk records for storage")
                chunk_data = []
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    chunk_record = {
                        'document_id': document_id,
                        'text': chunk.text,
                        'embedding': embedding.tolist(),  # Convert numpy array to list
                        'chunk_index': chunk.chunk_index,
                        'token_count': chunk.token_count,
                        'start_index': chunk.start_index,
                        'end_index': chunk.end_index,
                        'chunk_metadata': Json(chunk.metadata)
                    }
                    chunk_data.append(chunk_record)
                
                # Batch insert chunks
                batch_size = 100  # Adjust based on your needs
                logger.debug(f"Inserting chunks in batches of {batch_size}")
                for i in range(0, len(chunk_data), batch_size):
                    batch = chunk_data[i:i + batch_size]
                    batch_start = i + 1
                    batch_end = min(i + batch_size, len(chunk_data))
                    
                    logger.debug(f"Inserting chunk batch {batch_start}-{batch_end}")
                    self.supabase.table(rag_config.VECTOR_TABLE_NAME).insert(batch).execute()
                
                logger.info(f"Successfully stored document {document_id} with {len(chunks)} chunks")
                return document_id
            
        except Exception as e:
            log_exception(logger, f"Failed to store document '{metadata.title}'", e)
            raise RuntimeError(f"Document storage failed: {e}")
    
    async def similarity_search(self,
                              query_embedding: np.ndarray,
                              top_k: int = None,
                              similarity_threshold: float = None,
                              document_ids: Optional[List[str]] = None) -> List[RetrievalResult]:
        """
        Perform similarity search to retrieve relevant chunks.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            document_ids: Optional filter by document IDs
            
        Returns:
            List of retrieval results sorted by similarity
        """
        await self.initialize()
        
        top_k = top_k or rag_config.TOP_K_RETRIEVAL
        similarity_threshold = similarity_threshold or rag_config.SIMILARITY_THRESHOLD
        
        filter_str = f" (filtered by {len(document_ids)} docs)" if document_ids else ""
        logger.info(f"Similarity search: top_k={top_k}, threshold={similarity_threshold}{filter_str}")
        
        try:
            with get_performance_logger(logger, "similarity_search"):
                # Build query with vector similarity
                query_vector = query_embedding.tolist()
                
                # Use direct SQL for vector similarity search
                logger.debug("Connecting to PostgreSQL for similarity search")
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Build WHERE clause for document filtering
                where_clause = ""
                params = [query_vector, top_k]
                
                if document_ids:
                    placeholders = ','.join(['%s'] * len(document_ids))
                    where_clause = f" AND e.document_id IN ({placeholders})"
                    params.extend(document_ids)
                    logger.debug(f"Filtering by {len(document_ids)} document IDs")
                
                # Vector similarity search query
                query = f"""
                    SELECT 
                        e.chunk_id,
                        e.document_id,
                        e.text,
                        e.chunk_index,
                        e.token_count,
                        e.chunk_metadata,
                        m.title,
                        m.source,
                        m.language,
                        m.custom_metadata,
                        1 - (e.embedding <=> %s::vector) as similarity_score
                    FROM {rag_config.VECTOR_TABLE_NAME} e
                    JOIN {rag_config.METADATA_TABLE_NAME} m ON e.document_id = m.document_id
                    WHERE 1 - (e.embedding <=> %s::vector) >= {similarity_threshold}
                    {where_clause}
                    ORDER BY e.embedding <=> %s::vector
                    LIMIT %s;
                """
                
                # Add query vector again for ORDER BY clause
                params.insert(-1, query_vector)
                
                logger.debug("Executing vector similarity search query")
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                cursor.close()
                conn.close()
                
                # Convert to RetrievalResult objects
                retrieval_results = []
                for row in results:
                    metadata = {
                        'chunk_index': row['chunk_index'],
                        'token_count': row['token_count'],
                        'chunk_metadata': row['chunk_metadata'],
                        'document_title': row['title'],
                        'document_source': row['source'],
                        'document_language': row['language'],
                        'document_metadata': row['custom_metadata']
                    }
                    
                    retrieval_results.append(RetrievalResult(
                        chunk_id=str(row['chunk_id']),
                        document_id=str(row['document_id']),
                        text=row['text'],
                        similarity_score=float(row['similarity_score']),
                        metadata=metadata
                    ))
                
                logger.info(f"Retrieved {len(retrieval_results)} chunks (scores: {[r.similarity_score for r in retrieval_results[:3]]})")
                return retrieval_results
            
        except Exception as e:
            log_exception(logger, "Similarity search failed", e)
            raise RuntimeError(f"Similarity search failed: {e}")
    
    async def get_document_chunks(self, document_id: str) -> List[RetrievalResult]:
        """
        Get all chunks for a specific document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            List of document chunks
        """
        await self.initialize()
        
        logger.debug(f"Retrieving chunks for document: {document_id}")
        
        try:
            with get_performance_logger(logger, "get_document_chunks"):
                response = self.supabase.table(rag_config.VECTOR_TABLE_NAME)\
                    .select("*, document_metadata:document_id(*)")\
                    .eq('document_id', document_id)\
                    .order('chunk_index')\
                    .execute()
                
                results = []
                for row in response.data:
                    metadata = {
                        'chunk_index': row['chunk_index'],
                        'token_count': row['token_count'],
                        'chunk_metadata': row['chunk_metadata'],
                        'document_metadata': row.get('document_metadata', {})
                    }
                    
                    results.append(RetrievalResult(
                        chunk_id=str(row['chunk_id']),
                        document_id=str(row['document_id']),
                        text=row['text'],
                        similarity_score=1.0,  # Not applicable for direct retrieval
                        metadata=metadata
                    ))
                
                logger.info(f"Retrieved {len(results)} chunks for document {document_id}")
                return results
            
        except Exception as e:
            log_exception(logger, f"Failed to get chunks for document {document_id}", e)
            raise RuntimeError(f"Failed to get document chunks: {e}")
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and all its chunks.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if successful
        """
        await self.initialize()
        
        logger.info(f"Deleting document: {document_id}")
        
        try:
            with get_performance_logger(logger, "delete_document"):
                # Delete document (cascades to chunks)
                response = self.supabase.table(rag_config.METADATA_TABLE_NAME)\
                    .delete()\
                    .eq('document_id', document_id)\
                    .execute()
                
                deleted_count = len(response.data)
                if deleted_count > 0:
                    logger.info(f"Successfully deleted document {document_id}")
                else:
                    logger.warning(f"No document found with ID {document_id}")
                
                return deleted_count > 0
            
        except Exception as e:
            log_exception(logger, f"Failed to delete document {document_id}", e)
            return False
    
    async def list_documents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List stored documents with metadata.
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List of document metadata
        """
        await self.initialize()
        
        logger.debug(f"Listing documents: limit={limit}, offset={offset}")
        
        try:
            with get_performance_logger(logger, "list_documents"):
                response = self.supabase.table(rag_config.METADATA_TABLE_NAME)\
                    .select("*")\
                    .order('created_at', desc=True)\
                    .limit(limit)\
                    .offset(offset)\
                    .execute()
                
                documents = response.data
                logger.info(f"Retrieved {len(documents)} document records")
                return documents
            
        except Exception as e:
            log_exception(logger, "Failed to list documents", e)
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics.
        
        Returns:
            Statistics about stored documents and chunks
        """
        await self.initialize()
        
        logger.debug("Retrieving vector store statistics")
        
        try:
            with get_performance_logger(logger, "get_stats"):
                # Count documents
                doc_response = self.supabase.table(rag_config.METADATA_TABLE_NAME)\
                    .select("count")\
                    .execute()
                
                # Count chunks
                chunk_response = self.supabase.table(rag_config.VECTOR_TABLE_NAME)\
                    .select("count")\
                    .execute()
                
                stats = {
                    "total_documents": doc_response.count,
                    "total_chunks": chunk_response.count,
                    "embedding_dimension": rag_config.EMBEDDING_DIMENSION,
                    "initialized": self._initialized
                }
                
                logger.debug(f"Vector store stats: {stats}")
                return stats
            
        except Exception as e:
            log_exception(logger, "Failed to get vector store stats", e)
            return {
                "error": str(e),
                "initialized": self._initialized
            }


# Global vector store instance
vector_store = VectorStore()
logger.info("Global vector store instance created") 