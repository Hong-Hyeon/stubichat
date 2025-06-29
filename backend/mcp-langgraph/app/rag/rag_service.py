"""
RAG Service - Main orchestrator for the RAG system

This module provides the main RAG service that coordinates document ingestion,
query processing, retrieval, and prompt construction for generation.
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from app.rag.embedding_service import embedding_service
from app.rag.text_chunker import text_chunker, TextChunk
from app.rag.vector_store import vector_store, DocumentMetadata, RetrievalResult
from app.config.base import rag_config
from app.logger import get_logger, get_performance_logger, log_exception

# Use centralized logging
logger = get_logger(__name__)


@dataclass
class DocumentIngestionRequest:
    """
    Request for document ingestion.
    
    Attributes:
        text: Document text content
        title: Optional document title
        source: Optional document source
        language: Optional document language
        metadata: Additional custom metadata
        chunking_method: Text chunking method to use
    """
    text: str
    title: Optional[str] = None
    source: Optional[str] = None
    language: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    chunking_method: str = "sentence"


@dataclass
class QueryRequest:
    """
    Request for RAG query processing.
    
    Attributes:
        query: User query text
        top_k: Number of chunks to retrieve
        similarity_threshold: Minimum similarity threshold
        document_ids: Optional filter by specific documents
        include_metadata: Whether to include chunk metadata in response
    """
    query: str
    top_k: Optional[int] = None
    similarity_threshold: Optional[float] = None
    document_ids: Optional[List[str]] = None
    include_metadata: bool = True


@dataclass
class RAGResponse:
    """
    Response from RAG query processing.
    
    Attributes:
        query: Original query
        prompt: Generated prompt for LLM
        context_chunks: Retrieved context chunks
        metadata: Additional response metadata
        processing_stats: Performance statistics
    """
    query: str
    prompt: str
    context_chunks: List[RetrievalResult]
    metadata: Dict[str, Any]
    processing_stats: Dict[str, Any]


class RAGService:
    """
    Main RAG service orchestrating the complete RAG pipeline.
    
    Provides:
    - Document ingestion with embedding and storage
    - Query processing with retrieval and prompt construction
    - Batch operations for efficiency
    - Performance monitoring and statistics
    """
    
    def __init__(self):
        """Initialize the RAG service."""
        self.embedding_service = embedding_service
        self.text_chunker = text_chunker
        self.vector_store = vector_store
        self._initialized = False
        
        logger.info("Initializing RAG Service")
    
    async def initialize(self):
        """Initialize all components of the RAG service."""
        if self._initialized:
            logger.debug("RAG Service already initialized, skipping")
            return
        
        try:
            with get_performance_logger(logger, "rag_service_initialization"):
                # Initialize vector store (which will create tables if needed)
                logger.debug("Initializing vector store")
                await self.vector_store.initialize()
                
                # Load embedding model (will be lazy loaded on first use)
                logger.debug("Checking embedding service health")
                health_check = await self.embedding_service.health_check()
                if health_check["status"] != "healthy":
                    logger.warning(f"Embedding service health check failed: {health_check}")
                
                self._initialized = True
                logger.info("Successfully initialized RAG Service")
            
        except Exception as e:
            log_exception(logger, "Failed to initialize RAG Service", e)
            raise RuntimeError(f"RAG Service initialization failed: {e}")
    
    async def ingest_document(self, request: DocumentIngestionRequest) -> str:
        """
        Ingest a document into the RAG system.
        
        This includes:
        1. Text chunking
        2. Embedding generation
        3. Vector storage
        
        Args:
            request: Document ingestion request
            
        Returns:
            Document ID
        """
        await self.initialize()
        
        start_time = datetime.now()
        title = request.title or 'Untitled'
        
        logger.info(f"Starting document ingestion: '{title}' (length: {len(request.text)}, method: {request.chunking_method})")
        
        try:
            with get_performance_logger(logger, f"document_ingestion_{request.chunking_method}"):
                # Step 1: Chunk the document
                logger.debug("Step 1: Chunking document")
                chunks = self.text_chunker.chunk_document(
                    text=request.text,
                    metadata=request.metadata,
                    method=request.chunking_method
                )
                
                if not chunks:
                    error_msg = f"No chunks generated from document '{title}'"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                chunk_texts = [chunk.text for chunk in chunks]
                logger.info(f"Generated {len(chunks)} chunks for document '{title}'")
                
                # Step 2: Generate embeddings for all chunks
                logger.debug("Step 2: Generating embeddings")
                embeddings = await self.embedding_service.embed_documents(chunk_texts)
                
                if len(embeddings) != len(chunks):
                    error_msg = f"Embedding count ({len(embeddings)}) != chunk count ({len(chunks)})"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Step 3: Prepare document metadata
                logger.debug("Step 3: Preparing document metadata")
                document_id = str(uuid.uuid4())
                doc_metadata = DocumentMetadata(
                    document_id=document_id,
                    title=request.title,
                    source=request.source,
                    language=request.language,
                    custom_metadata=request.metadata or {}
                )
                
                # Step 4: Store in vector database
                logger.debug("Step 4: Storing in vector database")
                stored_doc_id = await self.vector_store.store_document(
                    text=request.text,
                    embeddings=embeddings,
                    chunks=chunks,
                    metadata=doc_metadata
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                logger.info(
                    f"Successfully ingested document '{title}' (ID: {stored_doc_id}) "
                    f"with {len(chunks)} chunks in {processing_time:.2f}s"
                )
                
                return stored_doc_id
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            log_exception(logger, f"Document ingestion failed for '{title}' after {processing_time:.2f}s", e)
            raise RuntimeError(f"Document ingestion failed: {e}")
    
    async def process_query(self, request: QueryRequest) -> RAGResponse:
        """
        Process a RAG query with retrieval and prompt construction.
        
        This includes:
        1. Query embedding
        2. Similarity search
        3. Context ranking and filtering
        4. Prompt construction
        
        Args:
            request: Query processing request
            
        Returns:
            RAG response with prompt and context
        """
        await self.initialize()
        
        start_time = datetime.now()
        query_preview = request.query[:100] + "..." if len(request.query) > 100 else request.query
        
        logger.info(f"Processing RAG query: '{query_preview}' (top_k: {request.top_k}, threshold: {request.similarity_threshold})")
        
        try:
            with get_performance_logger(logger, "query_processing"):
                # Step 1: Embed the query
                logger.debug("Step 1: Embedding query")
                embedding_start = datetime.now()
                query_embedding = await self.embedding_service.embed_query(request.query)
                embedding_time = (datetime.now() - embedding_start).total_seconds()
                
                # Step 2: Perform similarity search
                logger.debug("Step 2: Performing similarity search")
                retrieval_start = datetime.now()
                retrieved_chunks = await self.vector_store.similarity_search(
                    query_embedding=query_embedding,
                    top_k=request.top_k or rag_config.TOP_K_RETRIEVAL,
                    similarity_threshold=request.similarity_threshold or rag_config.SIMILARITY_THRESHOLD,
                    document_ids=request.document_ids
                )
                retrieval_time = (datetime.now() - retrieval_start).total_seconds()
                
                # Step 3: Construct prompt
                logger.debug("Step 3: Constructing prompt")
                prompt_start = datetime.now()
                prompt = self._construct_prompt(request.query, retrieved_chunks)
                prompt_time = (datetime.now() - prompt_start).total_seconds()
                
                # Step 4: Prepare response metadata
                processing_time = (datetime.now() - start_time).total_seconds()
                
                response_metadata = {
                    "query_length": len(request.query),
                    "retrieved_chunks": len(retrieved_chunks),
                    "prompt_length": len(prompt),
                    "processing_time": processing_time
                }
                
                processing_stats = {
                    "embedding_time": embedding_time,
                    "retrieval_time": retrieval_time,
                    "prompt_construction_time": prompt_time,
                    "total_time": processing_time
                }
                
                # Filter metadata if requested
                if not request.include_metadata:
                    logger.debug("Filtering out chunk metadata as requested")
                    for chunk in retrieved_chunks:
                        chunk.metadata = {}
                
                avg_score = sum(chunk.similarity_score for chunk in retrieved_chunks) / len(retrieved_chunks) if retrieved_chunks else 0
                logger.info(
                    f"Successfully processed query with {len(retrieved_chunks)} chunks "
                    f"(avg score: {avg_score:.3f}) in {processing_time:.2f}s"
                )
                
                return RAGResponse(
                    query=request.query,
                    prompt=prompt,
                    context_chunks=retrieved_chunks,
                    metadata=response_metadata,
                    processing_stats=processing_stats
                )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            log_exception(logger, f"Query processing failed for '{query_preview}' after {processing_time:.2f}s", e)
            raise RuntimeError(f"Query processing failed: {e}")
    
    def _construct_prompt(self, query: str, retrieved_chunks: List[RetrievalResult]) -> str:
        """
        Construct a structured prompt with retrieved context.
        
        Args:
            query: User query
            retrieved_chunks: Retrieved context chunks
            
        Returns:
            Formatted prompt for LLM
        """
        logger.debug(f"Constructing prompt with {len(retrieved_chunks)} chunks")
        
        if not retrieved_chunks:
            prompt = f"Based on your knowledge, please answer the following question:\n\n{query}"
            logger.debug("No chunks available, using knowledge-only prompt")
            return prompt
        
        # Build context section
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks):
            # Add document source information if available
            source_info = ""
            if chunk.metadata.get('document_title'):
                source_info = f" (from: {chunk.metadata['document_title']})"
            elif chunk.metadata.get('document_source'):
                source_info = f" (source: {chunk.metadata['document_source']})"
            
            context_parts.append(
                f"[Document {i+1}]{source_info}:\n{chunk.text.strip()}\n"
            )
        
        context_text = "\n".join(context_parts)
        
        # Construct the full prompt
        prompt = f"""You are an assistant with access to the following knowledge base:

{context_text}

Based on the above information, please answer the following question. If the answer cannot be found in the provided context, please indicate that clearly.

Question: {query}

Answer:"""
        
        # Check if prompt is too long and truncate if necessary
        if len(prompt) > rag_config.MAX_CONTEXT_LENGTH:
            logger.warning(f"Prompt too long ({len(prompt)} chars), truncating to {rag_config.MAX_CONTEXT_LENGTH}")
            
            # Calculate available space for context
            base_prompt_length = len(prompt) - len(context_text)
            available_context_length = rag_config.MAX_CONTEXT_LENGTH - base_prompt_length - 100  # Buffer
            
            # Truncate context while preserving complete chunks
            truncated_context = ""
            chunks_included = 0
            for part in context_parts:
                if len(truncated_context) + len(part) <= available_context_length:
                    truncated_context += part + "\n"
                    chunks_included += 1
                else:
                    break
            
            logger.info(f"Included {chunks_included}/{len(context_parts)} chunks in truncated prompt")
            
            prompt = f"""You are an assistant with access to the following knowledge base:

{truncated_context.strip()}

Based on the above information, please answer the following question. If the answer cannot be found in the provided context, please indicate that clearly.

Question: {query}

Answer:"""
        
        logger.debug(f"Constructed prompt of length: {len(prompt)}")
        return prompt
    
    async def batch_ingest_documents(self, requests: List[DocumentIngestionRequest]) -> List[str]:
        """
        Batch ingest multiple documents.
        
        Args:
            requests: List of document ingestion requests
            
        Returns:
            List of document IDs
        """
        await self.initialize()
        
        logger.info(f"Starting batch ingestion of {len(requests)} documents")
        
        document_ids = []
        successful_count = 0
        
        try:
            with get_performance_logger(logger, f"batch_ingestion_{len(requests)}_docs"):
                for i, request in enumerate(requests):
                    try:
                        logger.debug(f"Processing document {i+1}/{len(requests)}: {request.title or 'Untitled'}")
                        doc_id = await self.ingest_document(request)
                        document_ids.append(doc_id)
                        successful_count += 1
                        
                        # Log progress for large batches
                        if len(requests) > 5:
                            progress_pct = ((i + 1) / len(requests)) * 100
                            logger.info(f"Batch progress: {i+1}/{len(requests)} ({progress_pct:.1f}%)")
                        
                    except Exception as e:
                        log_exception(logger, f"Failed to ingest document {i+1}: {request.title or 'Untitled'}", e)
                        document_ids.append(None)  # Placeholder for failed ingestion
                
                logger.info(f"Batch ingestion completed: {successful_count}/{len(requests)} successful")
                return document_ids
            
        except Exception as e:
            log_exception(logger, f"Batch ingestion failed after processing {len(document_ids)} documents", e)
            return document_ids
    
    async def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a stored document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document information or None if not found
        """
        await self.initialize()
        
        logger.debug(f"Retrieving information for document: {document_id}")
        
        try:
            with get_performance_logger(logger, "get_document_info"):
                # Get document metadata
                documents = await self.vector_store.list_documents(limit=1000)
                doc_info = next((doc for doc in documents if doc['document_id'] == document_id), None)
                
                if not doc_info:
                    logger.warning(f"Document not found: {document_id}")
                    return None
                
                # Get chunk count
                chunks = await self.vector_store.get_document_chunks(document_id)
                doc_info['chunk_count'] = len(chunks)
                
                logger.debug(f"Retrieved info for document {document_id}: {doc_info.get('title', 'Untitled')} ({len(chunks)} chunks)")
                return doc_info
            
        except Exception as e:
            log_exception(logger, f"Failed to get info for document {document_id}", e)
            return None
    
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
                success = await self.vector_store.delete_document(document_id)
                
                if success:
                    logger.info(f"Successfully deleted document: {document_id}")
                else:
                    logger.warning(f"Document deletion returned False: {document_id}")
                
                return success
            
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
                documents = await self.vector_store.list_documents(limit, offset)
                logger.info(f"Retrieved {len(documents)} document records")
                return documents
            
        except Exception as e:
            log_exception(logger, "Failed to list documents", e)
            return []
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics.
        
        Returns:
            System statistics including performance metrics
        """
        await self.initialize()
        
        logger.debug("Retrieving comprehensive system statistics")
        
        try:
            with get_performance_logger(logger, "get_system_stats"):
                # Get vector store stats
                vector_stats = await self.vector_store.get_stats()
                
                # Get embedding service health
                embedding_health = await self.embedding_service.health_check()
                
                stats = {
                    "vector_store": vector_stats,
                    "embedding_service": embedding_health,
                    "configuration": {
                        "embedding_model": rag_config.EMBEDDING_MODEL,
                        "chunk_size": rag_config.CHUNK_SIZE,
                        "top_k_retrieval": rag_config.TOP_K_RETRIEVAL,
                        "similarity_threshold": rag_config.SIMILARITY_THRESHOLD
                    },
                    "initialized": self._initialized
                }
                
                logger.debug(f"System stats retrieved: {vector_stats.get('total_documents', 0)} docs, {vector_stats.get('total_chunks', 0)} chunks")
                return stats
            
        except Exception as e:
            log_exception(logger, "Failed to get system stats", e)
            return {
                "error": str(e),
                "initialized": self._initialized
            }


# Global RAG service instance
rag_service = RAGService()
logger.info("Global RAG service instance created") 