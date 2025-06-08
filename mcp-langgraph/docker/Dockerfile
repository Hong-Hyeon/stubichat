FROM python:3.12-slim

# 언어 및 TimeZone 설정
ENV LANG=ko_KR.UTF-8 \
    LANGUAGE=ko_KR.UTF-8 \
    PYTHONIOENCODING=utf-8 \
    TZ=Asia/Seoul

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgirepository1.0-dev \
    gcc \
    pkg-config \
    python3-dev \
    gir1.2-gtk-3.0 \
    libmariadb-dev \
    locales \
    wget \
    # sentencepiece 추가 패키지
    #git \
    #cmake \
    #make \
    #g++ \
    #pkg-config \
    #libsentencepiece-dev \
    #########################################################
    nano && \
    localedef -f UTF-8 -i ko_KR ko_KR.UTF-8 && \
    update-locale LANG=ko_KR.UTF-8 && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# pip 업그레이드 및 uv 설치
RUN pip install --upgrade pip setuptools wheel uv

# 애플리케이션 소스 복사 및 의존성 설치
# 예시
CMD mkdir /STUBI-CHAT-MCP
COPY ~/projects/stubichat-backend/mcp_system/mcp-langgraph/requirements.txt /STUBI-CHAT-MCP/requirements.txt
COPY ~/projects/stubichat-backend/mcp_system/mcp-langgraph/.env /STUBI-CHAT-MCP/.env

RUN uv pip install -r /STUBI-CHAT-MCP/requirements.txt --system

# entrypoint 복사 및 권한 설정
COPY ~/projects/stubichat-backend/mcp_system/mcp-langgraph/docker/entrypoint.sh /STUBI-CHAT-MCP/
RUN chmod 777 /STUBI-CHAT-MCP/entrypoint.sh

WORKDIR /STUBI-CHAT-MCP

ENTRYPOINT ["/STUBI-CHAT-MCP/entrypoint.sh"]
