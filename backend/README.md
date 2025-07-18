# Stubichat Backend - Microservice Architecture

A modern, scalable backend system built with FastAPI and LangGraph, designed for macOS without GPU dependencies.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Nginx         │    │  OpenAI API     │
│   (Next.js)     │◄──►│  (Reverse Proxy) │◄──►│                │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                       ┌────────┴────────┐
                       │                 │
               ┌───────▼───────┐ ┌──────▼──────┐
               │ Main Backend  │ │ LLM Agent   │
               │ (Port 8000)   │ │ (Port 8001) │
               │ FastAPI +     │ │ OpenAI API  │
               │ LangGraph     │ │ Integration │
               └───────────────┘ └─────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. **Docker and Docker Compose** installed
2. **OpenAI API Key** (required for LLM functionality)
3. **Environment Configuration** (see setup below)

### Setup

1. **Clone and navigate to backend directory:**
```bash
cd backend
```

2. **Create environment file:**
```bash
cp env.example .env
# Edit .env with your OpenAI API key and other settings
```

3. **Start all services:**
```bash
docker-compose up -d
```

4. **Check service status:**
```bash
docker-compose ps
```

## 📋 Services

### 1. Main Backend Service (`localhost:8000`)

**Purpose:** FastAPI application with LangGraph orchestration
- **Technology:** FastAPI + LangGraph + LangChain
- **Port:** 8000
- **Features:**
  - Conversation management with LangGraph workflows
  - HTTP client communication with LLM Agent
  - Health monitoring and logging
  - CORS support for frontend integration

**Endpoints:**
- `GET /` - Service status
- `GET /health` - Health check
- `POST /chat/` - Process chat request
- `POST /chat/stream` - Stream chat response
- `GET /docs` - API documentation (debug mode)

### 2. LLM Agent Service (`localhost:8001`)

**Purpose:** OpenAI API integration service
- **Technology:** FastAPI + OpenAI SDK
- **Port:** 8001
- **Features:**
  - Direct OpenAI API integration
  - Streaming text generation
  - Model parameter management
  - Health monitoring

**Endpoints:**
- `GET /` - Service status
- `GET /health` - Health check
- `POST /generate/` - Generate text
- `POST /generate/stream` - Stream text generation
- `GET /docs` - API documentation (debug mode)

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_ORGANIZATION=your-org-id-optional

# Main Backend Configuration
DEBUG=true
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-change-in-production

# LLM Agent Configuration
LLM_AGENT_URL=http://localhost:8001
LLM_AGENT_TIMEOUT=30

# CORS Settings
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001"]

# Model Settings
DEFAULT_MODEL=gpt-4
MAX_TOKENS=4000
TEMPERATURE=0.7
```

### Service Configuration

Each service has its own configuration in `app/core/config.py`:
- **Main Backend:** `main-backend/app/core/config.py`
- **LLM Agent:** `llm-agent/app/core/config.py`

## 🧪 Testing

### Health Checks

```bash
# Check main backend
curl http://localhost:8000/health

# Check LLM agent
curl http://localhost:8001/health
```

### API Testing

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "stream": false,
    "temperature": 0.7,
    "model": "gpt-4"
  }'

# Test streaming
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Tell me a story"}
    ],
    "stream": true
  }'
```

## 📊 Monitoring

### Logs

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f main-backend
docker-compose logs -f llm-agent
```

### Health Monitoring

All services include comprehensive health checks:
- **Main Backend:** `http://localhost:8000/health`
- **LLM Agent:** `http://localhost:8001/health`

### Performance Metrics

Services log performance metrics including:
- Request/response times
- OpenAI API usage
- Error rates and types
- Service dependencies status

## 🔄 Development Workflow

### Local Development

1. **Start services in development mode:**
```bash
docker-compose up -d
```

2. **View logs in real-time:**
```bash
docker-compose logs -f
```

3. **Make code changes** - Services auto-reload with volume mounts

4. **Test changes** - Use the health endpoints and API documentation

### Adding New Features

1. **Main Backend:** Add new endpoints in `main-backend/app/api/`
2. **LLM Agent:** Add new OpenAI integrations in `llm-agent/app/services/`
3. **LangGraph Workflows:** Extend workflows in `main-backend/app/core/graph.py`

## 🏗️ Project Structure

```
backend/
├── docker-compose.yml          # Service orchestration
├── env.example                 # Environment template
├── README.md                   # This file
├── logs/                       # Shared logs directory
├── main-backend/              # Main backend service
│   ├── Dockerfile             # Multi-stage build
│   ├── .dockerignore          # Build optimization
│   ├── requirements.txt       # Python dependencies
│   └── app/                   # Application code
│       ├── main.py            # FastAPI application
│       ├── core/              # Core functionality
│       │   ├── config.py      # Configuration
│       │   └── graph.py       # LangGraph workflows
│       ├── api/               # API endpoints
│       │   └── chat.py        # Chat endpoints
│       ├── models/            # Pydantic models
│       │   └── chat.py        # Chat models
│       ├── services/          # Business logic
│       │   └── llm_client.py  # LLM Agent client
│       └── utils/             # Utilities
│           └── logger.py      # Logging configuration
└── llm-agent/                 # LLM agent service
    ├── Dockerfile             # Multi-stage build
    ├── .dockerignore          # Build optimization
    ├── requirements.txt       # Python dependencies
    └── app/                   # Application code
        ├── main.py            # FastAPI application
        ├── core/              # Core functionality
        │   └── config.py      # Configuration
        ├── api/               # API endpoints
        │   └── generate.py    # Generate endpoints
        ├── models/            # Pydantic models
        │   └── requests.py    # Request/response models
        ├── services/          # Business logic
        │   └── openai_service.py # OpenAI integration
        └── utils/             # Utilities
            └── logger.py      # Logging configuration
```

## 🚀 Production Deployment

### Security Considerations

1. **Environment Variables:** Use secure secrets management
2. **API Keys:** Rotate OpenAI API keys regularly
3. **Network Security:** Use proper firewall rules
4. **HTTPS:** Enable SSL/TLS termination

### Scaling

```bash
# Scale individual services
docker-compose up -d --scale llm-agent=3

# Using Docker Swarm
docker stack deploy -c docker-compose.yml stubichat
```

### Monitoring

- **Health Checks:** All services include health endpoints
- **Logging:** Structured logging with loguru
- **Metrics:** Performance monitoring built-in
- **Error Handling:** Comprehensive error handling and reporting

## 🐛 Troubleshooting

### Common Issues

1. **OpenAI API Key Missing:**
```bash
# Check environment variable
echo $OPENAI_API_KEY

# Verify in .env file
cat .env | grep OPENAI_API_KEY
```

2. **Service Communication Issues:**
```bash
# Check network connectivity
docker-compose exec main-backend curl http://llm-agent:8001/health
```

3. **Port Conflicts:**
```bash
# Check port usage
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :8001
```

4. **Build Issues:**
```bash
# Rebuild services
docker-compose build --no-cache
docker-compose up -d
```

### Debug Mode

Enable debug logging:
```bash
# Set environment variables
export DEBUG=true
export LOG_LEVEL=DEBUG
docker-compose up -d
```

## 🤝 Contributing

1. **Development guidelines:**
   - Follow the established code structure
   - Add proper logging and error handling
   - Include health checks for new services
   - Test with realistic workloads

2. **Adding new services:**
   - Follow the established Docker patterns
   - Include health checks and proper logging
   - Update this README with new service information

3. **Performance testing:**
   - Monitor resource usage during development
   - Test with realistic workloads
   - Validate health check responsiveness 