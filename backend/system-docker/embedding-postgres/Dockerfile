FROM pgvector/pgvector:pg15

# Install PostGIS for PostgreSQL 15
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      postgresql-15-postgis-3 \
      postgresql-15-postgis-3-scripts && \
    rm -rf /var/lib/apt/lists/*

# Extensions available: vector, postgis
