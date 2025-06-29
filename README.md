# StubiChat

다국어 지원 RAG 시스템을 기반으로 한 지능형 채팅 서비스

## Overview

StubiChat은 MCP(Model Context Protocol) 서버와 VLLM 서버에 RAG(Retrieval-Augmented Generation) 시스템을 적용한 다국어 지원 AI 채팅 플랫폼입니다. 문서 임베딩, 검색, 그리고 컨텍스트 기반 응답 생성을 통해 정확하고 관련성 높은 답변을 제공합니다.

## Features

**다국어 RAG 시스템**: Hugging Face의 intfloat/multilingual-e5-large 모델을 사용한 다국어 문서 임베딩 및 검색

**벡터 데이터베이스**: Supabase PostgreSQL과 pgvector 확장을 활용한 고성능 유사도 검색

**모듈형 아키텍처**: 문서 처리, 임베딩, 검색, 프롬프트 구성 컴포넌트의 독립적 관리

**통합 로깅 시스템**: MCP 서버와 VLLM 서버 전반에 걸친 중앙화된 로깅 및 성능 모니터링

**실시간 스트리밍**: VLLM을 통한 고성능 텍스트 생성 및 스트리밍 응답

## Getting Started

프로젝트를 시작하기 위해 먼저 필요한 의존성을 설치하고 환경 변수를 설정합니다. Supabase 데이터베이스에 pgvector 확장을 활성화한 후, 각 서버의 requirements.txt를 통해 패키지를 설치합니다.

MCP 서버는 RAG 도구와 함께 LangGraph 기반으로 실행되며, VLLM 서버는 모델 추론을 위한 별도의 서비스로 동작합니다. 각 서버는 독립적으로 실행 가능하며, 필요에 따라 함께 사용할 수 있습니다.

환경 설정이 완료되면 데모 스크립트를 통해 RAG 시스템과 로깅 기능을 확인할 수 있습니다.

## Logging

모든 서버 컴포넌트에서 통합된 로깅 시스템을 사용합니다. 로그 파일은 `logging_<server_name>_<YYYY-MM-DD>.txt` 형식으로 매일 자동 생성되며, 요청 추적을 위한 고유 ID와 성능 메트릭이 포함됩니다.

로깅 시스템은 모델 추론 시간, 토큰 처리량, 오류 추적, 그리고 시스템 리소스 사용량을 실시간으로 모니터링합니다. 콘솔과 파일 출력을 동시에 지원하며, 운영 환경에서의 디버깅과 성능 분석을 위한 구조화된 로그 형식을 제공합니다.

## Directory Structure

```
stubichat/
├── backend/
│   ├── mcp-langgraph/          # MCP 서버 (RAG 시스템 포함)
│   │   ├── app/
│   │   │   ├── core/           # LangGraph 핵심 로직
│   │   │   ├── rag/           # RAG 컴포넌트 (임베딩, 벡터스토어, 검색)
│   │   │   └── logger.py       # 중앙화 로깅 시스템
│   │   └── requirements.txt
│   └── vllm_server/           # VLLM 추론 서버
│       ├── app/
│       │   ├── factory/        # 모델 팩토리
│       │   ├── service/        # LLM 서비스
│       │   ├── routers/        # API 라우터
│       │   └── logger.py       # 통합 로깅 시스템
│       └── requirements.txt
└── README.md
```

## Future Work

향후 개선 계획으로는 다국어 성능 최적화, 실시간 문서 인덱싱 자동화, 그리고 분산 환경에서의 확장성 향상이 포함됩니다. 또한 사용자 인터페이스 개발과 더 정교한 검색 알고리즘 적용을 통해 사용자 경험을 개선할 예정입니다.

클라우드 네이티브 배포 지원과 더불어 다양한 언어 모델과의 호환성 확대, 그리고 고급 RAG 기법 적용을 통한 답변 품질 향상도 계획하고 있습니다. 