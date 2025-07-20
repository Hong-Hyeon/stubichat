# StubiChat

LangGraph, MCP(Model Context Protocol), LLM 에이전트를 통합한 지능형 채팅 시스템

## 개요

StubiChat은 FastAPI 기반 메인 백엔드, LangGraph 워크플로우, MCP 서버, LLM 에이전트, 그리고 Next.js 프론트엔드로 구성된 완전한 AI 채팅 플랫폼입니다. 모듈형 아키텍처를 통해 확장 가능하고 유지보수가 용이한 시스템을 제공합니다.

## 주요 기능

- **LangGraph 워크플로우**: 대화 상태 관리 및 조건부 라우팅
- **MCP(Model Context Protocol) 통합**: 확장 가능한 도구 시스템
- **LLM 에이전트**: OpenAI API 기반 텍스트 생성
- **Next.js 프론트엔드**: 현대적이고 반응형 사용자 인터페이스
- **Docker Compose**: 전체 스택을 한 번에 실행
- **실시간 스트리밍**: 고성능 텍스트 스트리밍 지원

## 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │  Main Backend   │    │   LLM Agent     │
│   (Next.js)     │◄──►│  (FastAPI +     │◄──►│  (OpenAI API)   │
│   Port: 3000    │    │   LangGraph)    │    │   Port: 8001    │
│                 │    │   Port: 8000    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   MCP Server    │
                       │   (Tools)       │
                       │   Port: 8002    │
                       └─────────────────┘
```

## 빠른 시작 (Docker Compose)

### 1. 사전 요구사항

- Docker 및 Docker Compose 설치
- OpenAI API 키 (LLM 에이전트용)

### 2. 프로젝트 클론 및 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd stubichat

# 환경 변수 파일 생성
cp backend/env.example backend/.env
```

### 3. 환경 변수 설정

`backend/.env` 파일을 편집하여 OpenAI API 키를 설정합니다:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_ORGANIZATION=your-organization-id-optional

# Model Configuration
DEFAULT_MODEL=gpt-3.5-turbo
MAX_TOKENS=4000
TEMPERATURE=0.7
```

### 4. 전체 시스템 실행

```bash
# 백엔드 디렉토리로 이동
cd backend

# 모든 서비스 빌드 및 실행
docker-compose up -d --build

# 서비스 상태 확인
docker-compose ps
```

### 5. 서비스 접속

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **LLM 에이전트**: http://localhost:8001
- **MCP 서버**: http://localhost:8002

## 상세 설정 가이드

### 백엔드 서비스 (Main Backend)

**포트**: 8000

**주요 구성 요소**:
- FastAPI 기반 REST API
- LangGraph 워크플로우 엔진
- MCP 클라이언트 통합
- LLM 에이전트 클라이언트

**환경 변수**:
```bash
MAIN_BACKEND_HOST=0.0.0.0
MAIN_BACKEND_PORT=8000
MAIN_BACKEND_DEBUG=false
LLM_AGENT_URL=http://llm-agent:8001
MCP_SERVER_URL=http://mcp-server:8002
```

### LLM 에이전트 서비스

**포트**: 8001

**주요 구성 요소**:
- OpenAI API 클라이언트
- 텍스트 생성 및 스트리밍
- 모델 관리 및 설정

**환경 변수**:
```bash
LLM_AGENT_HOST=0.0.0.0
LLM_AGENT_PORT=8001
OPENAI_API_KEY=your-api-key
DEFAULT_MODEL=gpt-3.5-turbo
```

### MCP 서버

**포트**: 8002

**주요 구성 요소**:
- MCP 도구 등록 및 관리
- Echo 도구 (예시)
- 확장 가능한 도구 시스템

**기본 도구**:
- `echo`: 입력 메시지를 반복하는 간단한 도구

### 프론트엔드 (Next.js)

**포트**: 3000

**주요 구성 요소**:
- Next.js 15 기반 React 애플리케이션
- AI SDK 통합
- 실시간 채팅 인터페이스
- 반응형 디자인

**환경 변수**:
```bash
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000
```

## 시스템 테스트

### 1. 서비스 상태 확인

```bash
# 모든 서비스 상태 확인
docker-compose ps

# 개별 서비스 헬스체크
curl http://localhost:8000/health    # 백엔드
curl http://localhost:8001/health    # LLM 에이전트
curl http://localhost:8002/health    # MCP 서버
curl http://localhost:3000           # 프론트엔드
```

### 2. API 테스트

**기본 채팅 테스트**:
```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "request": {
      "id": "test-chat-1",
      "message": {
        "id": "msg-1",
        "role": "user",
        "parts": [{"text": "Hello, how are you?"}]
      },
      "selectedChatModel": "chat-model",
      "selectedVisibilityType": "private",
      "user": {"id": "test-user", "type": "guest"}
    }
  }'
```

**MCP 도구 테스트**:
```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "request": {
      "id": "test-chat-2",
      "message": {
        "id": "msg-2",
        "role": "user",
        "parts": [{"text": "echo Hello World"}]
      },
      "selectedChatModel": "chat-model",
      "selectedVisibilityType": "private",
      "user": {"id": "test-user", "type": "guest"}
    }
  }'
```

### 3. 프론트엔드 테스트

1. 브라우저에서 http://localhost:3000 접속
2. 게스트 로그인 또는 계정 생성
3. 채팅 인터페이스에서 메시지 전송
4. 일반 대화 및 MCP 도구 사용 테스트

## 개발 환경 설정

### 로컬 개발 (Docker 없이)

**백엔드 개발**:
```bash
cd backend/main-backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**LLM 에이전트 개발**:
```bash
cd backend/llm-agent
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**MCP 서버 개발**:
```bash
cd backend/mcp-server
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

**프론트엔드 개발**:
```bash
cd frontend
npm install
npm run dev
```

## 로그 및 모니터링

### 로그 확인

```bash
# 전체 시스템 로그
docker-compose logs

# 특정 서비스 로그
docker-compose logs main-backend
docker-compose logs llm-agent
docker-compose logs mcp-server
docker-compose logs frontend

# 실시간 로그 모니터링
docker-compose logs -f main-backend
```

### 로그 파일 위치

- 백엔드 로그: `backend/logs/`
- Nginx 로그: `logs/nginx/`

## 문제 해결

### 일반적인 문제들

**1. 포트 충돌**
```bash
# 사용 중인 포트 확인
lsof -i :3000
lsof -i :8000
lsof -i :8001
lsof -i :8002

# 서비스 재시작
docker-compose restart
```

**2. OpenAI API 키 오류**
```bash
# 환경 변수 확인
docker-compose exec llm-agent env | grep OPENAI

# .env 파일 재로드
docker-compose down
docker-compose up -d
```

**3. 빌드 오류**
```bash
# 캐시 없이 재빌드
docker-compose build --no-cache
docker-compose up -d
```

### 디버깅

**서비스 상태 확인**:
```bash
# 컨테이너 상태
docker-compose ps

# 컨테이너 내부 접속
docker-compose exec main-backend bash
docker-compose exec llm-agent bash
```

## 프로젝트 구조

```
stubichat/
├── backend/
│   ├── main-backend/           # 메인 백엔드 (FastAPI + LangGraph)
│   │   ├── app/
│   │   │   ├── api/           # API 엔드포인트
│   │   │   ├── core/          # LangGraph 워크플로우
│   │   │   ├── models/        # Pydantic 모델
│   │   │   ├── services/      # 비즈니스 로직
│   │   │   └── utils/         # 유틸리티
│   │   └── requirements.txt
│   ├── llm-agent/             # LLM 에이전트 (OpenAI API)
│   │   ├── app/
│   │   │   ├── api/           # API 엔드포인트
│   │   │   ├── services/      # OpenAI 서비스
│   │   │   └── models/        # 요청/응답 모델
│   │   └── requirements.txt
│   ├── mcp-server/            # MCP 서버 (도구 시스템)
│   │   ├── app/
│   │   │   ├── api/           # MCP API
│   │   │   └── tools/         # MCP 도구들
│   │   └── requirements.txt
│   ├── nginx/                 # Nginx 설정
│   ├── docker-compose.yml     # Docker Compose 설정
│   └── .env                   # 환경 변수
├── frontend/                  # Next.js 프론트엔드
│   ├── app/                   # Next.js 앱 라우터
│   ├── components/            # React 컴포넌트
│   ├── lib/                   # 유틸리티 라이브러리
│   ├── Dockerfile             # 프론트엔드 Docker 설정
│   └── package.json
├── logs/                      # 로그 파일들
└── README.md
```

## 향후 개발 계획

- **추가 MCP 도구**: 웹 검색, 파일 처리, 데이터베이스 연동
- **사용자 인증**: JWT 기반 인증 시스템
- **대화 히스토리**: 영구 저장 및 관리
- **성능 최적화**: 캐싱 및 비동기 처리 개선
- **모니터링**: Prometheus/Grafana 대시보드
- **배포**: Kubernetes 및 클라우드 배포 지원

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해 주세요. 