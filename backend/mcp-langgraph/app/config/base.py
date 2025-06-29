import os
from typing import Optional

# VLLM Server Configuration
vllm_server_url = "http://localhost:8003"

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "your-supabase-url")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-supabase-anon-key")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "your-service-role-key")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres")


# RAG Configuration
class RAGConfig:
    # Embedding Model Configuration
    EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
    EMBEDDING_DIMENSION = 1024  # multilingual-e5-large embedding dimension
    
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


# RAG system configuration instance
rag_config = RAGConfig()