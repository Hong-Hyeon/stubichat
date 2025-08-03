# Stubichat 임베딩 기능 설정 가이드

이 문서는 Stubichat 프로젝트에 추가된 임베딩 기능의 설정과 사용법을 설명합니다.

## 개요

Stubichat 프로젝트에 다음과 같은 임베딩 기능이 추가되었습니다:

- **임베딩 서버**: OpenAI GPT 모델을 사용한 텍스트 임베딩 생성
- **벡터 데이터베이스**: pgvector를 사용한 벡터 저장 및 검색
- **RAG 도구**: MCP 서버를 통한 벡터 검색 기능
- **CSV 데이터 임베딩**: 기존 CSV 데이터의 자동 임베딩

## 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Server    │    │ Embedding Server │    │ Vector Database │
│   (Port 8002)   │◄──►│   (Port 8003)    │◄──►│  (pgvector)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│   CSV Data      │    │   OpenAI API     │
│   (지진대피소)    │    │   (Embeddings)   │
└─────────────────┘    └──────────────────┘
```

## 설정 단계

### 1. 환경 변수 설정

`.env` 파일에 다음 환경 변수를 추가하세요:

```bash
# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1  # 선택사항

# 임베딩 데이터베이스 설정
EMBEDDING_DATABASE_URL=postgresql://embedding_user:embedding_password@embedding_postgres:5432/embeddings

# Redis 설정
REDIS_URL=redis://redis:6379/1
```

### 2. 서비스 시작

```bash
# 모든 서비스 시작
docker-compose up -d

# 또는 특정 서비스만 시작
docker-compose up -d embedding_postgres redis embedding-server
```

### 3. CSV 데이터 임베딩

기존 CSV 데이터를 벡터 데이터베이스에 임베딩합니다:

```bash
# 스크립트 실행
./embed_csv_data.sh
```

또는 수동으로 실행:

```bash
# 임베딩 서버 컨테이너에 접속
docker exec -it stubichat-embedding-server bash

# 임베딩 스크립트 실행
python -m app.scripts.embed_csv_data "/app/data/서울시 지진대피소 현황.csv"
```

## API 엔드포인트

### 임베딩 서버 (Port 8003)

#### 임베딩 생성
```http
POST /embed/
Content-Type: application/json

{
  "text": "임베딩할 텍스트",
  "metadata": {"source": "manual"}
}
```

#### 벡터 검색
```http
POST /embed/search
Content-Type: application/json

{
  "query": "검색할 쿼리",
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

#### 통계 조회
```http
GET /embed/statistics
```

#### 헬스 체크
```http
GET /health
```

### MCP 서버 (Port 8002)

#### RAG 검색
```http
POST /rag/search?query=검색할_쿼리&top_k=5
```

#### 임베딩 생성
```http
POST /rag/embed
Content-Type: application/json

{
  "text": "임베딩할 텍스트",
  "metadata": {"source": "mcp"}
}
```

#### 통계 조회
```http
GET /rag/stats
```

## 사용 예시

### 1. 지진대피소 정보 검색

```python
import httpx

# MCP 서버를 통한 검색
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8002/rag/search",
        params={"query": "강남구 지진대피소", "top_k": 3}
    )
    
    results = response.json()
    for result in results["results"]:
        print(f"내용: {result['content']}")
        print(f"유사도: {result['similarity_score']}")
        print("---")
```

### 2. 새로운 문서 임베딩

```python
import httpx

# 임베딩 서버에 직접 임베딩
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8003/embed/",
        json={
            "text": "새로운 지진대피소 정보",
            "metadata": {"location": "서울시", "type": "school"}
        }
    )
    
    result = response.json()
    print(f"임베딩 생성됨: {result['document_id']}")
```

## 모니터링

### 데이터베이스 통계 확인

```bash
# 임베딩 서버 통계
curl http://localhost:8003/embed/statistics

# MCP 서버 통계
curl http://localhost:8002/rag/stats
```

### 로그 확인

```bash
# 임베딩 서버 로그
docker logs stubichat-embedding-server

# MCP 서버 로그
docker logs stubichat-mcp-server
```

## 문제 해결

### 1. 임베딩 서버 연결 오류

```bash
# 서비스 상태 확인
docker-compose ps

# 임베딩 서버 재시작
docker-compose restart embedding-server
```

### 2. OpenAI API 오류

```bash
# API 키 확인
echo $OPENAI_API_KEY

# 환경 변수 재설정
export OPENAI_API_KEY=your_new_api_key
docker-compose restart embedding-server
```

### 3. 데이터베이스 연결 오류

```bash
# PostgreSQL 컨테이너 상태 확인
docker logs stubichat-embedding-postgres

# 데이터베이스 재시작
docker-compose restart embedding_postgres
```

## 성능 최적화

### 1. 배치 크기 조정

CSV 임베딩 시 배치 크기를 조정하여 성능을 최적화할 수 있습니다:

```python
# embed_csv_data.py에서 batch_size 조정
result = await embedder.embed_csv_file(csv_path, batch_size=50)
```

### 2. 인덱스 최적화

pgvector 인덱스는 자동으로 생성되지만, 필요에 따라 조정할 수 있습니다:

```sql
-- HNSW 인덱스 재생성
DROP INDEX IF EXISTS embeddings_embedding_hnsw_idx;
CREATE INDEX embeddings_embedding_hnsw_idx
ON embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 128);
```

## 다음 단계

임베딩 기능이 성공적으로 설정되면 다음 단계를 진행할 수 있습니다:

1. **더 많은 데이터 소스 추가**: 다른 CSV 파일이나 문서 추가
2. **검색 기능 개선**: 필터링, 정렬 기능 추가
3. **웹 인터페이스**: 임베딩 검색을 위한 웹 UI 개발
4. **실시간 업데이트**: 새로운 데이터의 자동 임베딩

## 지원

문제가 발생하거나 추가 도움이 필요한 경우:

1. 로그 파일 확인
2. API 응답 상태 코드 확인
3. 데이터베이스 연결 상태 확인
4. 환경 변수 설정 확인 