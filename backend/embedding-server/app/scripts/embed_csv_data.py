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
        seen_addresses = set()  # 중복 체크를 위한 set
        
        for index, row in df.iterrows():
            try:
                # 상세주소와 시설명 추출
                detailed_address = str(row.get('상세주소', '')).strip()
                facility_name = str(row.get('시설명', '')).strip()
                
                # 상세주소가 비어있으면 건너뛰기
                if not detailed_address or detailed_address == 'nan':
                    self.logger.warning(f"Row {index}: 상세주소가 비어있어 건너뜀")
                    continue
                
                # 중복 체크 (상세주소 기준)
                if detailed_address in seen_addresses:
                    self.logger.warning(f"Row {index}: 중복된 상세주소 발견, 건너뜀 - {detailed_address}")
                    continue
                
                seen_addresses.add(detailed_address)
                
                # 주요 필드 추출/정규화
                gu = str(row.get('자치구', '')).strip()
                dong = str(row.get('행정동', '') or row.get('법정동', '')).strip()
                capacity_str = str(row.get('수용가능인원', row.get('대피가능인원', '')).strip())
                facility_type = str(row.get('시설유형', row.get('시설분류', '')).strip())
                paved = str(row.get('지면포장', '')).strip()
                lat = str(row.get('위도', '')).strip()
                lon = str(row.get('경도', '')).strip()

                # 임베딩 텍스트 강화: 검색 유도 키워드 포함
                parts = []
                if facility_name:
                    parts.append(f"시설명: {facility_name}")
                loc_str = " ".join(filter(None, [gu, dong, detailed_address]))
                if loc_str:
                    parts.append(f"위치: {loc_str}")
                if capacity_str:
                    parts.append(f"수용인원: {capacity_str}명")
                if facility_type:
                    parts.append(f"유형: {facility_type}")
                if lat and lon:
                    parts.append(f"좌표: {lat},{lon}")
                if paved:
                    parts.append(f"지면포장: {paved}")
                embedding_text = " | ".join(parts) or detailed_address
                
                # 메타데이터 생성 (모든 필드 포함)
                metadata = {
                    "row_index": int(index),
                    "source": "csv_import",
                    "data_type": "earthquake_shelter"
                }
                
                # 모든 컬럼을 메타데이터에 추가 + 표준 키 추가
                for column, value in row.items():
                    if pd.notna(value) and str(value).strip() and str(value).strip() != 'nan':
                        metadata[column] = str(value).strip()

                # 표준화 메타데이터 키
                if gu:
                    metadata['gu'] = gu
                if dong:
                    metadata['dong'] = dong
                if facility_type:
                    metadata['type'] = facility_type
                if paved:
                    metadata['paved'] = paved
                # 숫자형 변환 가능 시 수행
                try:
                    if capacity_str:
                        metadata['capacity'] = int(float(capacity_str.replace(',', '')))
                except Exception:
                    pass
                try:
                    if lat:
                        metadata['lat'] = float(lat)
                    if lon:
                        metadata['lon'] = float(lon)
                except Exception:
                    pass
                
                # 고유한 document_id 생성 (상세주소 기반)
                document_id = f"shelter_{index}_{hash(detailed_address) % 1000000}"
                
                documents.append({
                    "document_id": document_id,
                    "content": embedding_text,
                    "metadata": metadata
                })
                
                self.logger.info(f"Row {index}: 문서 준비 완료 - {embedding_text[:50]}...")
                
            except Exception as e:
                self.logger.error(f"Row {index} 처리 중 오류: {str(e)}")
                continue
        
        self.logger.info(f"총 {len(documents)}개의 고유한 문서가 준비되었습니다.")
        return documents
    
    async def embed_documents(self, documents: List[Dict[str, Any]], batch_size: int = 10) -> Dict[str, Any]:
        """Embed documents in batches."""
        try:
            total_documents = len(documents)
            processed = 0
            failed = 0
            errors = []
            batch_results = []
            
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
                    batch_result = await self.vector_store_service.batch_store_embeddings(embeddings_data)
                    batch_results.append(batch_result)
                    
                    processed += batch_result.get("stored_count", len(batch))
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
                "errors": errors,
                "batch_results": batch_results
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
        
        # 배치 결과 요약
        total_stored = sum(batch.get('stored_count', 0) for batch in result.get('batch_results', []))
        total_skipped = sum(batch.get('skipped_count', 0) for batch in result.get('batch_results', []))
        print(f"Successfully stored: {total_stored}")
        print(f"Skipped duplicates: {total_skipped}")
        
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