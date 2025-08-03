#!/bin/bash

# CSV 데이터 임베딩 스크립트
# 이 스크립트는 서울시 지진대피소 현황 CSV 파일을 임베딩 서버에 임베딩합니다.

echo "=== Stubichat CSV 데이터 임베딩 시작 ==="

# 환경 변수 확인
if [ -z "$OPENAI_API_KEY" ]; then
    echo "오류: OPENAI_API_KEY 환경 변수가 설정되지 않았습니다."
    echo "export OPENAI_API_KEY=your_api_key_here 를 실행하세요."
    exit 1
fi

# CSV 파일 경로
CSV_FILE="data/서울시 지진대피소 현황.csv"

# 파일 존재 확인
if [ ! -f "$CSV_FILE" ]; then
    echo "오류: CSV 파일을 찾을 수 없습니다: $CSV_FILE"
    exit 1
fi

echo "CSV 파일 확인됨: $CSV_FILE"

# 임베딩 서버 컨테이너가 실행 중인지 확인
echo "임베딩 서버 상태 확인 중..."
if ! docker ps | grep -q "stubichat-embedding-server"; then
    echo "오류: 임베딩 서버가 실행되지 않고 있습니다."
    echo "docker-compose up -d embedding-server 를 먼저 실행하세요."
    exit 1
fi

echo "임베딩 서버가 실행 중입니다."

# 임베딩 스크립트 실행
echo "CSV 데이터 임베딩을 시작합니다..."
docker exec -it stubichat-embedding-server python -m app.scripts.embed_csv_data "/app/data/서울시 지진대피소 현황.csv"

if [ $? -eq 0 ]; then
    echo "=== CSV 데이터 임베딩 완료 ==="
    echo "임베딩된 데이터는 벡터 데이터베이스에 저장되었습니다."
    echo "MCP 서버의 RAG 도구를 통해 검색할 수 있습니다."
else
    echo "오류: CSV 데이터 임베딩 중 문제가 발생했습니다."
    exit 1
fi 