# RAG System Implementation

This document describes the complete Retrieval-Augmented Generation (RAG) system implementation for the MCP server backend.

## 🏗️ Architecture Overview

The RAG system consists of several modular components:

### Core Components

1. **Embedding Service** (`app/rag/embedding_service.py`)
   - Uses `intfloat/multilingual-e5-large` model
   - Supports multilingual text embedding
   - Batch processing for efficiency
   - Async support for non-blocking operations

2. **Text Chunker** (`app/rag/text_chunker.py`)
   - Multiple chunking strategies (sentence, token, paragraph)
   - Optimized for multilingual content
   - Configurable chunk size and overlap
   - Metadata preservation

3. **Vector Store** (`app/rag/vector_store.py`)
   - Supabase PostgreSQL with pgvector extension
   - Efficient similarity search using cosine similarity
   - Batch operations for large datasets
   - Metadata and document management

4. **RAG Service** (`app/rag/rag_service.py`)
   - Main orchestrator for the RAG pipeline
   - Document ingestion and query processing
   - Prompt construction for LLM generation
   - Performance monitoring and statistics

5. **RAG Tool** (`app/rag_tool.py`)
   - LangChain tool integration
   - JSON-based API for easy interaction
   - Multiple actions: query, ingest, list, stats

## 🚀 Setup Instructions

### 1. Environment Setup

Create a `.env` file with the following variables:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# PostgreSQL Database Configuration
DATABASE_URL=postgresql://postgres:your-password@db.your-project-ref.supabase.co:5432/postgres

# VLLM Server Configuration
VLLM_SERVER_URL=http://localhost:8003
```

### 2. Database Setup

1. Create a Supabase project
2. Enable the pgvector extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. The RAG system will automatically create the required tables on first run

### 3. Dependencies Installation

The required dependencies are already added to `requirements.txt`:

```bash
pip install -r requirements.txt
```

Key dependencies:
- `supabase==2.3.4` - Supabase client
- `psycopg2-binary==2.9.9` - PostgreSQL adapter
- `pgvector==0.2.4` - Vector operations
- `torch==2.1.2` - PyTorch for ML models
- `transformers==4.36.2` - Hugging Face transformers
- `sentence-transformers==2.2.2` - Sentence embeddings
- `tiktoken==0.5.2` - Token counting
- `nltk==3.8.1` - Natural language processing

### 4. Database Schema

The system creates two main tables:

#### Document Metadata Table
```sql
CREATE TABLE document_metadata (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    source TEXT,
    language TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    custom_metadata JSONB DEFAULT '{}'::jsonb
);
```

#### Document Embeddings Table
```sql
CREATE TABLE document_embeddings (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES document_metadata(document_id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    embedding VECTOR(1024),
    chunk_index INTEGER,
    token_count INTEGER,
    start_index INTEGER,
    end_index INTEGER,
    chunk_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 📖 Usage Guide

### Using the RAG Tool

The RAG system is integrated as a LangChain tool that can be used by the MCP graph system. The tool accepts JSON input with different actions:

#### 1. Document Ingestion

```json
{
    "action": "ingest",
    "text": "Your document text content here...",
    "title": "Document Title",
    "source": "Document Source",
    "language": "en",
    "chunking_method": "sentence"
}
```

#### 2. Knowledge Base Query

```json
{
    "action": "query",
    "query": "What is machine learning?",
    "top_k": 5,
    "similarity_threshold": 0.7,
    "include_metadata": true
}
```

#### 3. List Documents

```json
{
    "action": "list",
    "limit": 10,
    "offset": 0
}
```

#### 4. System Statistics

```json
{
    "action": "stats"
}
```

### Example Chat Interactions

#### Document Ingestion Example

**User:** "문서를 추가해줘"

**System:** Uses RAG tool with:
```json
{
    "action": "ingest",
    "text": "인공지능(AI)은 컴퓨터가 인간의 지능을 모방하도록 설계된 기술입니다...",
    "title": "AI 기초 개념",
    "language": "ko"
}
```

#### Knowledge Query Example

**User:** "AI에 대해 알려줘"

**System:** Uses RAG tool with:
```json
{
    "action": "query",
    "query": "AI에 대해 알려줘",
    "top_k": 3
}
```

The system will:
1. Embed the query using multilingual-e5-large
2. Search the vector database for relevant chunks
3. Construct a prompt with retrieved context
4. Return the prompt for LLM generation

## 🔧 Configuration

### RAG Configuration (`app/config/base.py`)

```python
class RAGConfig:
    # Embedding Model Configuration
    EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
    EMBEDDING_DIMENSION = 1024
    
    # Text Chunking Configuration
    CHUNK_SIZE = 512  # tokens per chunk
    CHUNK_OVERLAP = 50  # overlap between chunks
    
    # Retrieval Configuration
    TOP_K_RETRIEVAL = 5  # number of chunks to retrieve
    SIMILARITY_THRESHOLD = 0.7  # minimum similarity score
    
    # Vector Store Configuration
    VECTOR_TABLE_NAME = "document_embeddings"
    METADATA_TABLE_NAME = "document_metadata"
    
    # Query Configuration
    MAX_CONTEXT_LENGTH = 4000  # maximum context length for LLM
    
    # Batch Processing Configuration
    BATCH_SIZE = 32  # batch size for embedding generation
```

## 🎯 Features

### Multilingual Support
- Uses multilingual-e5-large for embedding generation
- Supports query and document text in multiple languages
- Proper prefixes for query vs document embedding

### Chunking Strategies
- **Sentence-based**: Recommended for multilingual content
- **Token-based**: Precise token count control with overlap
- **Paragraph-based**: Preserves document structure

### Vector Search
- Cosine similarity search using pgvector
- Configurable similarity thresholds
- Efficient indexing with IVFFlat algorithm

### Performance Optimization
- Batch processing for embedding generation
- Async operations throughout the pipeline
- Connection pooling and efficient database queries

### Metadata Management
- Rich metadata support for documents and chunks
- Source tracking and language detection
- Custom metadata fields

## 🔍 Monitoring and Debugging

### System Statistics

Use the stats action to get comprehensive system information:

```json
{
    "action": "stats"
}
```

Returns:
- Total documents and chunks count
- Embedding service health status
- Configuration parameters
- Performance metrics

### Logging

All components use structured logging:
- Embedding service operations
- Document ingestion progress
- Query processing times
- Error handling and debugging information

## 🚨 Error Handling

The system includes comprehensive error handling:

- **Embedding failures**: Graceful fallback and retry mechanisms
- **Database connection issues**: Connection pooling and reconnection
- **Invalid input**: Validation and user-friendly error messages
- **Resource limitations**: Memory management and batch processing

## 📈 Performance Considerations

### Embedding Model Loading
- Models are lazy-loaded on first use
- GPU acceleration when available
- Memory-efficient batch processing

### Database Optimization
- Vector indexing for fast similarity search
- Batch operations for bulk data insertion
- Connection pooling for concurrent requests

### Memory Management
- Configurable batch sizes
- Streaming for large document processing
- Efficient numpy array handling

## 🔮 Future Enhancements

Potential improvements for the RAG system:

1. **Advanced Retrieval Strategies**
   - Hybrid search (vector + keyword)
   - Re-ranking models
   - Query expansion

2. **Document Processing**
   - PDF and document parsing
   - Image and multimodal content
   - Automatic language detection

3. **Performance Optimization**
   - Caching mechanisms
   - Distributed processing
   - Real-time updates

4. **User Interface**
   - Web-based document management
   - Visual similarity exploration
   - Analytics dashboard

## 🆘 Troubleshooting

### Common Issues

1. **Embedding Model Loading Errors**
   - Ensure sufficient memory (8GB+ recommended)
   - Check internet connection for model download
   - Verify GPU compatibility if using CUDA

2. **Database Connection Issues**
   - Verify Supabase credentials
   - Check pgvector extension is enabled
   - Ensure database URL is correct

3. **Performance Issues**
   - Adjust batch sizes for available memory
   - Monitor database connection limits
   - Consider GPU acceleration for embeddings

### Debug Mode

Enable debug logging by setting log level to DEBUG in your environment or code:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will provide detailed information about:
- Embedding generation times
- Database query execution
- Chunk processing details
- Vector search results

---

## 📝 API Reference

For detailed API documentation, refer to the docstrings in each module:

- `app/rag/embedding_service.py` - Embedding operations
- `app/rag/text_chunker.py` - Text processing
- `app/rag/vector_store.py` - Database operations
- `app/rag/rag_service.py` - Main orchestration
- `app/rag_tool.py` - LangChain integration

The RAG system is now fully integrated with your MCP server backend and ready for use! 