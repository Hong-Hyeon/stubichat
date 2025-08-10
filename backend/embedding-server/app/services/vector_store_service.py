import asyncpg
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.utils.logger import get_logger
import json
import uuid
import re


class VectorStoreService:
    """Service for storing and retrieving vectors using pgvector."""

    def __init__(self):
        self.logger = get_logger("vector_store_service")
        self.db_url = settings.embedding_database_url
        self.pool = None

    async def _get_pool(self):
        """Get database connection pool."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=5,
                max_size=20
            )
        return self.pool

    async def initialize_database(self):
        """Initialize database tables and extensions with optimized indexes."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Enable pgvector extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                # Enable PostGIS
                await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")

                # Create embeddings table with optimized structure
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id SERIAL PRIMARY KEY,
                        document_id VARCHAR(255) UNIQUE NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector(1536),
                        metadata JSONB,
                        geom GEOGRAPHY(Point, 4326),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)

                # Create optimized indexes for better performance
                # 1. HNSW index for fast approximate nearest neighbor search
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_embedding_hnsw_idx
                    ON embeddings
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """)

                # 2. IVFFlat index as fallback for exact search
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_embedding_ivfflat_idx
                    ON embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)

                # 3. B-tree index on document_id for fast lookups
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_document_id_idx
                    ON embeddings (document_id)
                """)

                # 4. GIN index on metadata for fast JSONB queries
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_metadata_gin_idx
                    ON embeddings USING GIN (metadata)
                """)

                # 6. GiST index on geography for spatial queries
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_geom_gist_idx
                    ON embeddings USING GIST (geom)
                """)

                # 5. B-tree index on created_at for time-based queries
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_created_at_idx
                    ON embeddings (created_at)
                """)

                # Create table metadata table for managing multiple embedding tables
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS table_metadata (
                        id SERIAL PRIMARY KEY,
                        table_id VARCHAR(255) UNIQUE NOT NULL,
                        table_name VARCHAR(255) UNIQUE NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)

                # Insert default embeddings table metadata if not exists
                await conn.execute("""
                    INSERT INTO table_metadata (table_id, table_name, description, created_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (table_name) DO NOTHING
                """, str(uuid.uuid4()), "embeddings", "Default embeddings table")

                self.logger.info("Database initialized successfully with optimized indexes and table metadata")

        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise

    async def store_embedding(
        self,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store an embedding in the database."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # 중복 체크 (content 기준)
                existing = await conn.fetchval("""
                    SELECT document_id FROM embeddings WHERE content = $1
                """, content)
                
                if existing:
                    self.logger.warning(f"중복된 content 발견, 건너뜀: {content[:50]}...")
                    return False
                
                # Convert metadata to JSON string if not None
                metadata_json = json.dumps(metadata) if metadata is not None else None
                
                # Convert embedding list to string for pgvector
                embedding_str = f"[{','.join(map(str, embedding))}]"
                
                # Compute geom from metadata lat/lon if present
                lat = None
                lon = None
                try:
                    if metadata and 'lat' in metadata and 'lon' in metadata:
                        lat = float(metadata['lat'])
                        lon = float(metadata['lon'])
                except Exception:
                    lat = None
                    lon = None

                if lat is not None and lon is not None:
                    await conn.execute("""
                        INSERT INTO embeddings (document_id, content, embedding, metadata, geom)
                        VALUES ($1, $2, $3::vector, $4::jsonb, ST_SetSRID(ST_MakePoint($5, $6), 4326)::geography)
                        ON CONFLICT (document_id)
                        DO UPDATE SET
                            content = $2,
                            embedding = $3::vector,
                            metadata = $4::jsonb,
                            geom = ST_SetSRID(ST_MakePoint($5, $6), 4326)::geography,
                            updated_at = NOW()
                    """, document_id, content, embedding_str, metadata_json, lon, lat)
                else:
                    await conn.execute("""
                        INSERT INTO embeddings (document_id, content, embedding, metadata)
                        VALUES ($1, $2, $3::vector, $4::jsonb)
                        ON CONFLICT (document_id)
                        DO UPDATE SET
                            content = $2,
                            embedding = $3::vector,
                            metadata = $4::jsonb,
                            updated_at = NOW()
                    """, document_id, content, embedding_str, metadata_json)

                self.logger.info(f"Embedding stored for document: {document_id}")
                return True

        except Exception as e:
            self.logger.error(f"Error storing embedding: {str(e)}")
            raise

    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings using optimized cosine similarity."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Convert query embedding to string for pgvector
                query_embedding_str = f"[{','.join(map(str, query_embedding))}]"
                
                # Build filter conditions
                filter_conditions = []
                filter_params = [query_embedding_str, similarity_threshold, top_k]
                param_count = 3

                if filters:
                    for key, value in filters.items():
                        # Support numeric range filters for capacity via suffixes
                        if key.endswith('_min'):
                            base = key[:-4]
                            param_count += 1
                            filter_conditions.append(
                                f"(metadata->>'{base}')::double precision >= ${param_count}"
                            )
                            filter_params.append(float(value))
                        elif key.endswith('_max'):
                            base = key[:-4]
                            param_count += 1
                            filter_conditions.append(
                                f"(metadata->>'{base}')::double precision <= ${param_count}"
                            )
                            filter_params.append(float(value))
                        else:
                            param_count += 1
                            filter_conditions.append(f"metadata->>'{key}' = ${param_count}")
                            filter_params.append(value)

                filter_sql = " AND " + " AND ".join(filter_conditions) if filter_conditions else ""

                # Use HNSW index for fast approximate search
                query = f"""
                    SELECT
                        document_id,
                        content,
                        metadata,
                        1 - (embedding <=> $1::vector) as similarity_score
                    FROM embeddings
                    WHERE 1 - (embedding <=> $1::vector) > $2{filter_sql}
                    ORDER BY embedding <=> $1::vector
                    LIMIT $3
                """

                rows = await conn.fetch(query, *filter_params)

                results = []
                for row in rows:
                    # Handle metadata - it might be a string from JSONB
                    metadata = row["metadata"]
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except (json.JSONDecodeError, TypeError):
                            metadata = None
                    
                    results.append({
                        "document_id": row["document_id"],
                        "content": row["content"],
                        "metadata": metadata,
                        "similarity_score": float(row["similarity_score"])
                    })

                self.logger.info(f"Found {len(results)} similar documents")
                return results

        except Exception as e:
            self.logger.error(f"Error searching similar embeddings: {str(e)}")
            raise

    async def batch_store_embeddings(
        self,
        embeddings_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Store multiple embeddings in batch for better performance."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                stored_count = 0
                skipped_count = 0
                # Use transaction for batch operations
                async with conn.transaction():
                    for data in embeddings_data:
                        document_id = data["document_id"]
                        content = data["content"]
                        embedding = data["embedding"]
                        metadata = data.get("metadata")

                        existing = await conn.fetchval("""
                            SELECT document_id FROM embeddings WHERE content = $1
                        """, content)
                        if existing:
                            self.logger.warning(f"중복된 content 발견, 건너뜀: {content[:50]}...")
                            skipped_count += 1
                            continue

                        metadata_json = json.dumps(metadata) if metadata is not None else None
                        embedding_str = f"[{','.join(map(str, embedding))}]"

                        lat = None
                        lon = None
                        try:
                            if metadata and 'lat' in metadata and 'lon' in metadata:
                                lat = float(metadata['lat'])
                                lon = float(metadata['lon'])
                        except Exception:
                            lat = None
                            lon = None

                        if lat is not None and lon is not None:
                            await conn.execute("""
                                INSERT INTO embeddings (document_id, content, embedding, metadata, geom)
                                VALUES ($1, $2, $3::vector, $4::jsonb, ST_SetSRID(ST_MakePoint($5, $6), 4326)::geography)
                                ON CONFLICT (document_id)
                                DO UPDATE SET
                                    content = $2,
                                    embedding = $3::vector,
                                    metadata = $4::jsonb,
                                    geom = ST_SetSRID(ST_MakePoint($5, $6), 4326)::geography,
                                    updated_at = NOW()
                            """, document_id, content, embedding_str, metadata_json, lon, lat)
                        else:
                            await conn.execute("""
                                INSERT INTO embeddings (document_id, content, embedding, metadata)
                                VALUES ($1, $2, $3::vector, $4::jsonb)
                                ON CONFLICT (document_id)
                                DO UPDATE SET
                                    content = $2,
                                    embedding = $3::vector,
                                    metadata = $4::jsonb,
                                    updated_at = NOW()
                            """, document_id, content, embedding_str, metadata_json)

                self.logger.info(f"Batch stored {stored_count} embeddings, skipped {skipped_count} duplicates")
                return {
                    "success": True,
                    "stored_count": stored_count,
                    "skipped_count": skipped_count,
                    "total_processed": len(embeddings_data)
                }

        except Exception as e:
            self.logger.error(f"Error in batch store: {str(e)}")
            raise

    async def search_similar_within_radius(
        self,
        query_embedding: List[float],
        center_lat: float,
        center_lon: float,
        radius_m: int = 1000,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = 'hybrid',
        alpha: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search similar embeddings constrained within a radius using PostGIS geography and HNSW for vectors."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                query_embedding_str = f"[{','.join(map(str, query_embedding))}]"

                filter_conditions = [
                    "geom IS NOT NULL",
                    "ST_DWithin(geom, ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography, $4)"
                ]
                filter_params: List[Any] = []
                # Base placeholders used in SQL before metadata filters:
                # $1 embedding, $2 lon, $3 lat, $4 radius, $5 similarity_threshold, $6 top_k
                # If hybrid: $7 alpha is used in SELECT; metadata filters must start AFTER these
                base_count = 7 if order_by == 'hybrid' else 6
                param_count = base_count

                if filters:
                    for key, value in filters.items():
                        param_count += 1
                        placeholder = f"${param_count}"
                        # Support numeric range via *_min/*_max and numeric equality when value is number
                        if key.endswith('_min'):
                            base = key[:-4]
                            filter_conditions.append(f"(metadata->>'{base}')::double precision >= {placeholder}")
                            filter_params.append(float(value))
                        elif key.endswith('_max'):
                            base = key[:-4]
                            filter_conditions.append(f"(metadata->>'{base}')::double precision <= {placeholder}")
                            filter_params.append(float(value))
                        else:
                            if isinstance(value, (int, float)):
                                filter_conditions.append(f"(metadata->>'{key}')::double precision = {placeholder}")
                                filter_params.append(float(value))
                            else:
                                filter_conditions.append(f"metadata->>'{key}' = {placeholder}")
                                filter_params.append(str(value))

                filter_sql = " AND " + " AND ".join(filter_conditions) if filter_conditions else ""

                # Compute hybrid score when requested
                # Normalize distance by radius for bounded [0,1], inverted so closer is higher
                if order_by == 'hybrid':
                    order_sql = "ORDER BY hybrid_score DESC"
                    select_extra = ", ( ($7 * (1 - (embedding <=> $1::vector))) + ((1 - $7) * (1 - LEAST(ST_Distance(geom, ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography) / NULLIF($4,0), 1))) ) AS hybrid_score"
                elif order_by == 'distance':
                    order_sql = "ORDER BY distance_m ASC"
                    select_extra = ""
                else:
                    order_sql = "ORDER BY embedding <=> $1::vector"
                    select_extra = ""

                sql = f"""
                    SELECT document_id, content, metadata,
                           1 - (embedding <=> $1::vector) AS similarity_score,
                           ST_Distance(geom, ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography) AS distance_m
                           {select_extra}
                    FROM embeddings
                    WHERE 1 - (embedding <=> $1::vector) > $5{filter_sql}
                    {order_sql}
                    LIMIT $6
                """

                if order_by == 'hybrid':
                    rows = await conn.fetch(
                        sql,
                        query_embedding_str,
                        center_lon,
                        center_lat,
                        radius_m,
                        similarity_threshold,
                        top_k,
                        alpha,
                        *filter_params
                    )
                else:
                    rows = await conn.fetch(
                        sql,
                        query_embedding_str,
                        center_lon,
                        center_lat,
                        radius_m,
                        similarity_threshold,
                        top_k,
                        *filter_params
                    )

                results: List[Dict[str, Any]] = []
                for row in rows:
                    metadata = row["metadata"]
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except Exception:
                            metadata = None
                    item = {
                        "document_id": row["document_id"],
                        "content": row["content"],
                        "metadata": metadata,
                        "similarity_score": float(row["similarity_score"]),
                        "distance_m": float(row["distance_m"]) if row["distance_m"] is not None else None
                    }
                    if order_by == 'hybrid' and 'hybrid_score' in row:
                        try:
                            item["hybrid_score"] = float(row["hybrid_score"])  # type: ignore
                        except Exception:
                            pass
                    results.append(item)

                return results

        except Exception as e:
            self.logger.error(f"Error in geo search: {str(e)}")
            raise

    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics for monitoring."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Get total count
                total_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
                
                # Get average embedding dimension (using vector_dims function for pgvector)
                avg_dimension = await conn.fetchval("""
                    SELECT AVG(vector_dims(embedding)) 
                    FROM embeddings 
                    WHERE embedding IS NOT NULL
                """)
                
                # Get metadata statistics
                metadata_stats = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM embeddings 
                    WHERE metadata IS NOT NULL AND metadata != '{}'::jsonb
                """)
                
                # Get recent activity
                recent_count = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM embeddings 
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)

                return {
                    "total_documents": total_count,
                    "avg_embedding_dimension": avg_dimension,
                    "documents_with_metadata": metadata_stats,
                    "recent_documents_24h": recent_count
                }

        except Exception as e:
            self.logger.error(f"Error getting statistics: {str(e)}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check database health with detailed information."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Test connection
                await conn.fetchval("SELECT 1")

                # Get basic statistics
                stats = await self.get_statistics()
                
                # Check index usage
                index_info = await conn.fetch("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    WHERE tablename = 'embeddings'
                """)

                return {
                    "status": "healthy",
                    "connection": "ok",
                    "statistics": stats,
                    "index_usage": [dict(row) for row in index_info]
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed"
            } 