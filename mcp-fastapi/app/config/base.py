from pathlib import Path

# ExaOne 모델 설정
EXAONE_MODEL_PATH = Path("LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct")  # 실제 모델 경로로 수정 필요

# MCP 서버 설정
MCP_SERVER_URL = "http://localhost:8002"

# 데이터베이스 설정
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",  # 실제 사용시 환경변수로 관리 권장
    "password": "root",  # 실제 사용시 환경변수로 관리 권장
    "database": "mcp_db",
    "charset": "utf8mb4"
}