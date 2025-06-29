"""
Text Chunking Service for RAG System

This module handles text chunking for document ingestion, supporting various
chunking strategies optimized for multilingual content and embedding models.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import tiktoken
from app.config.base import rag_config
from app.logger import get_logger, get_performance_logger, log_exception

# Use centralized logging
logger = get_logger(__name__)


@dataclass
class TextChunk:
    """
    Represents a text chunk with metadata.
    
    Attributes:
        text: The chunk text content
        start_index: Start position in original document
        end_index: End position in original document
        chunk_index: Index of this chunk in the document
        token_count: Number of tokens in the chunk
        metadata: Additional metadata for the chunk
    """
    text: str
    start_index: int
    end_index: int
    chunk_index: int
    token_count: int
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TextChunker:
    """
    Service for chunking text documents into embedding-suitable segments.
    
    Supports multiple chunking strategies:
    - Sentence-based chunking (recommended for multilingual content)
    - Token-based chunking with overlap
    - Paragraph-based chunking
    - Custom delimiter-based chunking
    """
    
    def __init__(self, 
                 chunk_size: int = None, 
                 chunk_overlap: int = None,
                 encoding_name: str = "cl100k_base"):
        """
        Initialize the text chunker.
        
        Args:
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Overlap between chunks in tokens
            encoding_name: Tokenizer encoding to use
        """
        self.chunk_size = chunk_size or rag_config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or rag_config.CHUNK_OVERLAP
        self.encoding_name = encoding_name
        
        try:
            self.tokenizer = tiktoken.get_encoding(encoding_name)
            logger.debug(f"Successfully loaded tokenizer: {encoding_name}")
        except Exception as e:
            logger.warning(f"Failed to load tokenizer {encoding_name}: {e}")
            # Fallback to a simpler token counting method
            self.tokenizer = None
        
        logger.info(f"Initialized TextChunker - chunk_size: {self.chunk_size}, overlap: {self.chunk_overlap}")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Input text
            
        Returns:
            Number of tokens
        """
        if self.tokenizer:
            token_count = len(self.tokenizer.encode(text))
            logger.debug(f"Token count (tiktoken): {token_count} for text length {len(text)}")
            return token_count
        else:
            # Fallback: approximate token count (1 token ≈ 4 characters for many languages)
            token_count = len(text) // 4
            logger.debug(f"Token count (fallback): {token_count} for text length {len(text)}")
            return token_count
    
    def split_by_sentences(self, text: str, metadata: Dict[str, Any] = None) -> List[TextChunk]:
        """
        Split text by sentences, grouping into chunks that fit token limits.
        This method works well for multilingual content.
        
        Args:
            text: Input text to chunk
            metadata: Additional metadata to attach to chunks
            
        Returns:
            List of text chunks
        """
        if not text.strip():
            logger.warning("Empty text provided for sentence splitting")
            return []
        
        logger.debug(f"Starting sentence-based chunking for text of length {len(text)}")
        
        # Split into sentences using multilingual sentence boundaries
        sentence_endings = r'[.!?。！？]+\s+'
        sentences = re.split(sentence_endings, text)
        
        # Remove empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        logger.debug(f"Split into {len(sentences)} sentences")
        
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        
        for i, sentence in enumerate(sentences):
            # Calculate token count for current chunk + new sentence
            potential_chunk = current_chunk + (" " if current_chunk else "") + sentence
            token_count = self.count_tokens(potential_chunk)
            
            if token_count <= self.chunk_size or not current_chunk:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                    current_start = text.find(sentence)
            else:
                # Current chunk is full, create a chunk and start a new one
                if current_chunk:
                    chunk_end = current_start + len(current_chunk)
                    chunk_metadata = metadata.copy() if metadata else {}
                    chunk_metadata.update({
                        "chunk_method": "sentence",
                        "sentence_count": current_chunk.count('.') + current_chunk.count('!') + current_chunk.count('?')
                    })
                    
                    chunk = TextChunk(
                        text=current_chunk,
                        start_index=current_start,
                        end_index=chunk_end,
                        chunk_index=chunk_index,
                        token_count=self.count_tokens(current_chunk),
                        metadata=chunk_metadata
                    )
                    chunks.append(chunk)
                    logger.debug(f"Created chunk {chunk_index} with {chunk.token_count} tokens")
                    
                    chunk_index += 1
                
                # Start new chunk with current sentence
                current_chunk = sentence
                current_start = text.find(sentence, current_start)
        
        # Add the last chunk if it exists
        if current_chunk:
            chunk_end = current_start + len(current_chunk)
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                "chunk_method": "sentence",
                "sentence_count": current_chunk.count('.') + current_chunk.count('!') + current_chunk.count('?')
            })
            
            chunk = TextChunk(
                text=current_chunk,
                start_index=current_start,
                end_index=chunk_end,
                chunk_index=chunk_index,
                token_count=self.count_tokens(current_chunk),
                metadata=chunk_metadata
            )
            chunks.append(chunk)
            logger.debug(f"Created final chunk {chunk_index} with {chunk.token_count} tokens")
        
        logger.info(f"Split text into {len(chunks)} sentence-based chunks")
        return chunks
    
    def split_by_tokens(self, text: str, metadata: Dict[str, Any] = None) -> List[TextChunk]:
        """
        Split text by token count with overlap.
        
        Args:
            text: Input text to chunk
            metadata: Additional metadata to attach to chunks
            
        Returns:
            List of text chunks
        """
        if not text.strip():
            logger.warning("Empty text provided for token splitting")
            return []
        
        logger.debug(f"Starting token-based chunking for text of length {len(text)}")
        
        if not self.tokenizer:
            # Fallback to character-based splitting
            logger.warning("No tokenizer available, falling back to character-based splitting")
            return self._split_by_characters(text, metadata)
        
        # Tokenize the entire text
        tokens = self.tokenizer.encode(text)
        logger.debug(f"Text tokenized into {len(tokens)} tokens")
        
        if len(tokens) <= self.chunk_size:
            # Text fits in one chunk
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({"chunk_method": "token", "token_count": len(tokens)})
            
            chunk = TextChunk(
                text=text,
                start_index=0,
                end_index=len(text),
                chunk_index=0,
                token_count=len(tokens),
                metadata=chunk_metadata
            )
            
            logger.info("Text fits in single token-based chunk")
            return [chunk]
        
        chunks = []
        chunk_index = 0
        start_token = 0
        
        while start_token < len(tokens):
            # Calculate end token for this chunk
            end_token = min(start_token + self.chunk_size, len(tokens))
            
            # Extract tokens for this chunk
            chunk_tokens = tokens[start_token:end_token]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            # Find start and end positions in original text
            start_text = self.tokenizer.decode(tokens[:start_token]) if start_token > 0 else ""
            start_index = len(start_text)
            end_index = start_index + len(chunk_text)
            
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                "chunk_method": "token",
                "token_start": start_token,
                "token_end": end_token
            })
            
            chunk = TextChunk(
                text=chunk_text,
                start_index=start_index,
                end_index=end_index,
                chunk_index=chunk_index,
                token_count=len(chunk_tokens),
                metadata=chunk_metadata
            )
            chunks.append(chunk)
            
            logger.debug(f"Created token chunk {chunk_index}: tokens {start_token}-{end_token}")
            
            # Move to next chunk with overlap
            start_token = end_token - self.chunk_overlap
            chunk_index += 1
            
            # Prevent infinite loop
            if start_token >= end_token:
                break
        
        logger.info(f"Split text into {len(chunks)} token-based chunks")
        return chunks
    
    def split_by_paragraphs(self, text: str, metadata: Dict[str, Any] = None) -> List[TextChunk]:
        """
        Split text by paragraphs, combining paragraphs that fit within token limits.
        
        Args:
            text: Input text to chunk
            metadata: Additional metadata to attach to chunks
            
        Returns:
            List of text chunks
        """
        if not text.strip():
            logger.warning("Empty text provided for paragraph splitting")
            return []
        
        logger.debug(f"Starting paragraph-based chunking for text of length {len(text)}")
        
        # Split by paragraphs (double newlines or single newlines for some formats)
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        logger.debug(f"Split into {len(paragraphs)} paragraphs")
        
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        
        for paragraph in paragraphs:
            potential_chunk = current_chunk + ("\n\n" if current_chunk else "") + paragraph
            token_count = self.count_tokens(potential_chunk)
            
            if token_count <= self.chunk_size or not current_chunk:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                    current_start = text.find(paragraph)
            else:
                # Create chunk with current content
                if current_chunk:
                    chunk_end = current_start + len(current_chunk)
                    chunk_metadata = metadata.copy() if metadata else {}
                    chunk_metadata.update({
                        "chunk_method": "paragraph",
                        "paragraph_count": current_chunk.count('\n\n') + 1
                    })
                    
                    chunk = TextChunk(
                        text=current_chunk,
                        start_index=current_start,
                        end_index=chunk_end,
                        chunk_index=chunk_index,
                        token_count=self.count_tokens(current_chunk),
                        metadata=chunk_metadata
                    )
                    chunks.append(chunk)
                    logger.debug(f"Created paragraph chunk {chunk_index} with {chunk.token_count} tokens")
                    
                    chunk_index += 1
                
                # Start new chunk
                current_chunk = paragraph
                current_start = text.find(paragraph, current_start)
        
        # Add last chunk
        if current_chunk:
            chunk_end = current_start + len(current_chunk)
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                "chunk_method": "paragraph",
                "paragraph_count": current_chunk.count('\n\n') + 1
            })
            
            chunk = TextChunk(
                text=current_chunk,
                start_index=current_start,
                end_index=chunk_end,
                chunk_index=chunk_index,
                token_count=self.count_tokens(current_chunk),
                metadata=chunk_metadata
            )
            chunks.append(chunk)
            logger.debug(f"Created final paragraph chunk {chunk_index} with {chunk.token_count} tokens")
        
        logger.info(f"Split text into {len(chunks)} paragraph-based chunks")
        return chunks
    
    def _split_by_characters(self, text: str, metadata: Dict[str, Any] = None) -> List[TextChunk]:
        """
        Fallback method to split by characters when tokenizer is not available.
        
        Args:
            text: Input text to chunk
            metadata: Additional metadata to attach to chunks
            
        Returns:
            List of text chunks
        """
        logger.debug("Using character-based fallback chunking method")
        
        # Approximate: 1 token ≈ 4 characters
        char_chunk_size = self.chunk_size * 4
        char_overlap = self.chunk_overlap * 4
        
        chunks = []
        chunk_index = 0
        start = 0
        
        while start < len(text):
            end = min(start + char_chunk_size, len(text))
            
            # Try to break at word boundaries
            if end < len(text):
                # Look for word boundary within last 20% of chunk
                boundary_start = int(end * 0.8)
                last_space = text.rfind(' ', boundary_start, end)
                if last_space > start:
                    end = last_space
            
            chunk_text = text[start:end]
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({"chunk_method": "character", "char_count": len(chunk_text)})
            
            chunk = TextChunk(
                text=chunk_text,
                start_index=start,
                end_index=end,
                chunk_index=chunk_index,
                token_count=self.count_tokens(chunk_text),
                metadata=chunk_metadata
            )
            chunks.append(chunk)
            
            logger.debug(f"Created character chunk {chunk_index}: chars {start}-{end}")
            
            start = end - char_overlap
            chunk_index += 1
            
            if start >= end:
                break
        
        logger.info(f"Split text into {len(chunks)} character-based chunks")
        return chunks
    
    def chunk_document(self,
                       text: str,
                       metadata: Dict[str, Any] = None,
                       method: str = "sentence") -> List[TextChunk]:
        """
        Chunk a document using the specified method.
        
        Args:
            text: Document text to chunk
            metadata: Document metadata
            method: Chunking method ("sentence", "token", "paragraph")
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            logger.warning("Empty or whitespace-only text provided for chunking")
            return []
        
        logger.info(f"Chunking document using '{method}' method (length: {len(text)})")
        
        # Add basic document metadata
        doc_metadata = metadata.copy() if metadata else {}
        doc_metadata.update({
            "document_length": len(text),
            "document_token_count": self.count_tokens(text)
        })
        
        try:
            with get_performance_logger(logger, f"text_chunking_{method}"):
                if method == "sentence":
                    chunks = self.split_by_sentences(text, doc_metadata)
                elif method == "token":
                    chunks = self.split_by_tokens(text, doc_metadata)
                elif method == "paragraph":
                    chunks = self.split_by_paragraphs(text, doc_metadata)
                else:
                    logger.warning(f"Unknown chunking method: {method}, falling back to sentence-based")
                    chunks = self.split_by_sentences(text, doc_metadata)
                
                if chunks:
                    avg_tokens = sum(chunk.token_count for chunk in chunks) / len(chunks)
                    logger.info(f"Created {len(chunks)} chunks, avg tokens per chunk: {avg_tokens:.1f}")
                else:
                    logger.warning("No chunks created from document")
                
                return chunks
                
        except Exception as e:
            log_exception(logger, f"Failed to chunk document using method '{method}'", e)
            raise RuntimeError(f"Document chunking failed: {e}")


# Global text chunker instance
text_chunker = TextChunker()
logger.info("Global text chunker instance created") 