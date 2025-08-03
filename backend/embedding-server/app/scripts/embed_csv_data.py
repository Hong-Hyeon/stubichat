#!/usr/bin/env python3
"""
Script to embed CSV data into the vector database.
"""

import asyncio
import pandas as pd
import json
import uuid
from typing import List, Dict, Any
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.gpt_embedding_service import GPTEmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.core.config import settings
from app.utils.logger import get_logger


class CSVEmbedder:
    """Class to handle CSV data embedding."""
    
    def __init__(self):
        self.logger = get_logger("csv_embedder")
        self.embedding_service = GPTEmbeddingService()
        self.vector_store_service = VectorStoreService()
    
    async def initialize(self):
        """Initialize services and database."""
        try:
            await self.vector_store_service.initialize_database()
            self.logger.info("Services initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing services: {str(e)}")
            raise
    
    def load_csv_data(self, csv_path: str) -> pd.DataFrame:
        """Load CSV data from file."""
        try:
            # Try different encodings
            encodings = ['utf-8', 'cp949', 'euc-kr']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_path, encoding=encoding)
                    self.logger.info(f"Successfully loaded CSV with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError("Could not read CSV file with any encoding")
            
            return df
        except Exception as e:
            self.logger.error(f"Error loading CSV data: {str(e)}")
            raise
    
    def prepare_documents(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare documents for embedding from DataFrame."""
        documents = []
        
        for index, row in df.iterrows():
            # Create a meaningful text representation of the row
            text_parts = []
            
            for column, value in row.items():
                if pd.notna(value) and str(value).strip():
                    text_parts.append(f"{column}: {value}")
            
            if text_parts:
                content = " | ".join(text_parts)
                
                # Create metadata
                metadata = {
                    "row_index": int(index),
                    "columns": list(row.index),
                    "source": "csv_import"
                }
                
                # Add non-null values to metadata
                for column, value in row.items():
                    if pd.notna(value) and str(value).strip():
                        metadata[column] = str(value)
                
                documents.append({
                    "document_id": str(uuid.uuid4()),
                    "content": content,
                    "metadata": metadata
                })
        
        return documents
    
    async def embed_documents(self, documents: List[Dict[str, Any]], batch_size: int = 10) -> Dict[str, Any]:
        """Embed documents in batches."""
        try:
            total_documents = len(documents)
            processed = 0
            failed = 0
            errors = []
            
            self.logger.info(f"Starting to embed {total_documents} documents in batches of {batch_size}")
            
            for i in range(0, total_documents, batch_size):
                batch = documents[i:i + batch_size]
                
                try:
                    # Extract texts for batch embedding
                    texts = [doc["content"] for doc in batch]
                    
                    # Create embeddings
                    embeddings = await self.embedding_service.create_embeddings_batch(texts)
                    
                    # Prepare data for vector store
                    embeddings_data = []
                    for doc, embedding in zip(batch, embeddings):
                        embeddings_data.append({
                            "document_id": doc["document_id"],
                            "content": doc["content"],
                            "embedding": embedding,
                            "metadata": doc["metadata"]
                        })
                    
                    # Store in vector database
                    await self.vector_store_service.batch_store_embeddings(embeddings_data)
                    
                    processed += len(batch)
                    self.logger.info(f"Processed batch {i//batch_size + 1}: {processed}/{total_documents} documents")
                    
                except Exception as e:
                    failed += len(batch)
                    error_msg = f"Error processing batch {i//batch_size + 1}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
            
            return {
                "total_documents": total_documents,
                "processed": processed,
                "failed": failed,
                "errors": errors
            }
            
        except Exception as e:
            self.logger.error(f"Error in embed_documents: {str(e)}")
            raise
    
    async def embed_csv_file(self, csv_path: str, batch_size: int = 10) -> Dict[str, Any]:
        """Main method to embed a CSV file."""
        try:
            self.logger.info(f"Starting CSV embedding process for: {csv_path}")
            
            # Load CSV data
            df = self.load_csv_data(csv_path)
            self.logger.info(f"Loaded {len(df)} rows from CSV")
            
            # Prepare documents
            documents = self.prepare_documents(df)
            self.logger.info(f"Prepared {len(documents)} documents for embedding")
            
            # Embed documents
            result = await self.embed_documents(documents, batch_size)
            
            self.logger.info(f"Embedding completed: {result['processed']} processed, {result['failed']} failed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error embedding CSV file: {str(e)}")
            raise


async def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python embed_csv_data.py <csv_file_path>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
    
    embedder = CSVEmbedder()
    
    try:
        await embedder.initialize()
        result = await embedder.embed_csv_file(csv_path)
        
        print("\n=== Embedding Results ===")
        print(f"Total documents: {result['total_documents']}")
        print(f"Processed: {result['processed']}")
        print(f"Failed: {result['failed']}")
        
        if result['errors']:
            print(f"\nErrors: {len(result['errors'])}")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
        
        print("\nEmbedding process completed!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 