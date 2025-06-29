"""
RAG Tool for MCP LangGraph Integration

This module provides a LangChain tool that integrates the RAG system
with the existing MCP server backend for document ingestion and querying.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.rag.rag_service import (
    rag_service, DocumentIngestionRequest, QueryRequest, RAGResponse
)

logger = logging.getLogger(__name__)


class RAGQueryInput(BaseModel):
    """Input model for RAG query operations."""
    query: str = Field(description="The question or query to search for in the knowledge base")
    top_k: Optional[int] = Field(default=5, description="Number of relevant chunks to retrieve (default: 5)")
    similarity_threshold: Optional[float] = Field(default=0.7, description="Minimum similarity score (0-1, default: 0.7)")
    document_ids: Optional[List[str]] = Field(default=None, description="Optional list of specific document IDs to search in")
    include_metadata: Optional[bool] = Field(default=True, description="Whether to include metadata in the response")


class RAGIngestInput(BaseModel):
    """Input model for RAG document ingestion."""
    text: str = Field(description="The document text content to ingest")
    title: Optional[str] = Field(default=None, description="Optional title for the document")
    source: Optional[str] = Field(default=None, description="Optional source information")
    language: Optional[str] = Field(default=None, description="Optional language code (e.g., 'en', 'ko')")
    chunking_method: Optional[str] = Field(default="sentence", description="Chunking method: 'sentence', 'token', or 'paragraph'")


class RAGTool(BaseTool):
    """
    RAG Tool for document ingestion and querying.
    
    This tool provides access to the RAG system functionality including:
    - Document ingestion with embedding and storage
    - Query processing with retrieval and prompt construction
    - Document management operations
    """
    
    name = "rag"
    description = (
        "Query a knowledge base using Retrieval-Augmented Generation (RAG). "
        "This tool can both ingest documents and answer questions based on stored knowledge. "
        "Use 'action: query' to search the knowledge base, or 'action: ingest' to add new documents. "
        "Input should be a JSON string with the action and relevant parameters."
    )
    
    def _parse_input(self, tool_input: str) -> Dict[str, Any]:
        """Parse the input string as JSON."""
        try:
            if isinstance(tool_input, str):
                return json.loads(tool_input)
            return tool_input
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {e}")
    
    async def _arun(self, tool_input: str) -> str:
        """Execute the RAG tool asynchronously."""
        try:
            # Parse input
            input_data = self._parse_input(tool_input)
            action = input_data.get("action", "query")
            
            if action == "query":
                return await self._handle_query(input_data)
            elif action == "ingest":
                return await self._handle_ingest(input_data)
            elif action == "list":
                return await self._handle_list(input_data)
            elif action == "stats":
                return await self._handle_stats()
            else:
                return json.dumps({
                    "error": f"Unknown action: {action}",
                    "available_actions": ["query", "ingest", "list", "stats"]
                })
                
        except Exception as e:
            logger.error(f"RAG tool error: {e}")
            return json.dumps({
                "error": str(e),
                "type": type(e).__name__
            })
    
    async def _handle_query(self, input_data: Dict[str, Any]) -> str:
        """Handle RAG query operations."""
        try:
            # Validate input
            query_input = RAGQueryInput(**input_data)
            
            # Create query request
            request = QueryRequest(
                query=query_input.query,
                top_k=query_input.top_k,
                similarity_threshold=query_input.similarity_threshold,
                document_ids=query_input.document_ids,
                include_metadata=query_input.include_metadata
            )
            
            # Process query
            response = await rag_service.process_query(request)
            
            # Return formatted response
            return self._format_query_response(response)
            
        except Exception as e:
            logger.error(f"Query handling error: {e}")
            return json.dumps({
                "error": f"Query processing failed: {str(e)}",
                "type": type(e).__name__
            })
    
    async def _handle_ingest(self, input_data: Dict[str, Any]) -> str:
        """Handle document ingestion operations."""
        try:
            # Validate input
            ingest_input = RAGIngestInput(**input_data)
            
            # Create ingestion request
            request = DocumentIngestionRequest(
                text=ingest_input.text,
                title=ingest_input.title,
                source=ingest_input.source,
                language=ingest_input.language,
                chunking_method=ingest_input.chunking_method
            )
            
            # Ingest document
            document_id = await rag_service.ingest_document(request)
            
            # Get document info
            doc_info = await rag_service.get_document_info(document_id)
            
            return json.dumps({
                "success": True,
                "document_id": document_id,
                "document_info": doc_info,
                "message": f"Successfully ingested document: {ingest_input.title or 'Untitled'}"
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Ingestion handling error: {e}")
            return json.dumps({
                "error": f"Document ingestion failed: {str(e)}",
                "type": type(e).__name__
            })
    
    async def _handle_list(self, input_data: Dict[str, Any]) -> str:
        """Handle document listing operations."""
        try:
            limit = input_data.get("limit", 10)
            offset = input_data.get("offset", 0)
            
            documents = await rag_service.list_documents(limit=limit, offset=offset)
            
            return json.dumps({
                "success": True,
                "documents": documents,
                "count": len(documents),
                "limit": limit,
                "offset": offset
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"List handling error: {e}")
            return json.dumps({
                "error": f"Document listing failed: {str(e)}",
                "type": type(e).__name__
            })
    
    async def _handle_stats(self) -> str:
        """Handle system statistics operations."""
        try:
            stats = await rag_service.get_system_stats()
            
            return json.dumps({
                "success": True,
                "stats": stats
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Stats handling error: {e}")
            return json.dumps({
                "error": f"Statistics retrieval failed: {str(e)}",
                "type": type(e).__name__
            })
    
    def _format_query_response(self, response: RAGResponse) -> str:
        """Format the RAG query response for return."""
        try:
            # Build context information
            context_info = []
            for i, chunk in enumerate(response.context_chunks):
                chunk_info = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "text": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                    "similarity_score": round(chunk.similarity_score, 4),
                    "metadata": {
                        "document_title": chunk.metadata.get("document_title"),
                        "document_source": chunk.metadata.get("document_source"),
                        "chunk_index": chunk.metadata.get("chunk_index")
                    }
                }
                context_info.append(chunk_info)
            
            # Build response object
            result = {
                "success": True,
                "query": response.query,
                "answer_prompt": response.prompt,
                "context_chunks": context_info,
                "metadata": {
                    "retrieved_chunks": len(response.context_chunks),
                    "processing_time": response.processing_stats.get("total_time", 0),
                    "prompt_length": len(response.prompt)
                }
            }
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Response formatting error: {e}")
            return json.dumps({
                "error": f"Response formatting failed: {str(e)}",
                "raw_response": str(response)
            })
    
    def _run(self, tool_input: str) -> str:
        """Synchronous execution not supported."""
        raise NotImplementedError("RAG tool only supports async execution")


# Create the RAG tool instance
rag_tool = RAGTool()


# Example usage functions for testing
async def example_ingest_document():
    """Example of document ingestion."""
    sample_text = """
    인공지능(AI)은 컴퓨터가 인간의 지능을 모방하도록 설계된 기술입니다. 
    머신러닝과 딥러닝은 AI의 주요 분야로, 데이터에서 패턴을 학습하여 예측을 수행합니다.
    자연어 처리(NLP)는 컴퓨터가 인간의 언어를 이해하고 생성할 수 있게 하는 AI 기술입니다.
    """
    
    input_data = {
        "action": "ingest",
        "text": sample_text,
        "title": "AI 기초 개념",
        "source": "교육 자료",
        "language": "ko"
    }
    
    result = await rag_tool._arun(json.dumps(input_data))
    print("Ingestion Result:", result)


async def example_query_knowledge():
    """Example of knowledge base querying."""
    input_data = {
        "action": "query",
        "query": "자연어 처리가 무엇인가요?",
        "top_k": 3,
        "similarity_threshold": 0.5
    }
    
    result = await rag_tool._arun(json.dumps(input_data))
    print("Query Result:", result)


# Usage examples for the tool
USAGE_EXAMPLES = {
    "query": {
        "description": "Query the knowledge base",
        "example": {
            "action": "query",
            "query": "What is machine learning?",
            "top_k": 5,
            "similarity_threshold": 0.7
        }
    },
    "ingest": {
        "description": "Ingest a new document",
        "example": {
            "action": "ingest",
            "text": "Your document text here...",
            "title": "Document Title",
            "source": "Document Source",
            "language": "en"
        }
    },
    "list": {
        "description": "List stored documents",
        "example": {
            "action": "list",
            "limit": 10,
            "offset": 0
        }
    },
    "stats": {
        "description": "Get system statistics",
        "example": {
            "action": "stats"
        }
    }
}

# Add usage examples to tool description
rag_tool.description += f"\n\nUsage examples:\n{json.dumps(USAGE_EXAMPLES, indent=2, ensure_ascii=False)}" 