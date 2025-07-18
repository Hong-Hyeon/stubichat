# Stubichat Backend

A production-ready microservice backend for conversational AI applications, built with FastAPI, LangGraph, and OpenAI API.

## 🏗️ Architecture

The backend follows a **microservice architecture** with two main services:

### 1. Main Backend Service (`main-backend`)
- **Port**: 8000
- **Purpose**: Orchestration and conversation management
- **Technologies**: FastAPI, LangGraph, LangChain
- **Features**:
  - Conversation state management
  - LangGraph workflow orchestration
  - Chat history and context management
  - Multi-modal input processing
  - Streaming responses

### 2. LLM Agent Service (`llm-agent`)
- **Port**: 8001
- **Purpose**: Direct LLM interactions
- **Technologies**: FastAPI, OpenAI API
- **Features**:
  - OpenAI API integration
  - Text generation and streaming
  - Model selection and configuration
  - Rate limiting and error handling

## 🏭 Factory Pattern Implementation

Both services implement the **Factory Pattern** for improved maintainability, testability, and dependency injection:

### App Factory
- **Location**: `app/factory/app_factory.py`
- **Purpose**: Creates and configures FastAPI applications
- **Features**:
  - Centralized application creation
  - Middleware configuration
  - Route registration
  - Exception handling
  - Health checks
  - CORS configuration

### Service Factory
- **Location**: `app/factory/service_factory.py`
- **Purpose**: Manages service dependencies
- **Features**:
  - Dependency injection
  - Service lifecycle management
  - Testing support
  - Resource cleanup

### Benefits
- ✅ **Testability**: Easy to mock dependencies
- ✅ **Maintainability**: Centralized configuration
- ✅ **Flexibility**: Easy to swap implementations
- ✅ **Production Ready**: Proper error handling and logging

## 🔧 Configuration Management

### Environment Variables
The services use `python-dotenv` for loading configuration from `.env` files:

```bash
# Copy the example configuration
cp env.example .env

# Edit .env with your settings
nano .env
```

### Key Configuration
```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_ORGANIZATION=your-organization-id-optional

# Model Configuration
DEFAULT_MODEL=gpt-4
MAX_TOKENS=4000
TEMPERATURE=0.7

# Service Configuration
MAIN_BACKEND_HOST=0.0.0.0
MAIN_BACKEND_PORT=8000
LLM_AGENT_HOST=0.0.0.0
LLM_AGENT_PORT=8001

# Security
SECRET_KEY=your-secret-key-change-in-production
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- OpenAI API key

### 1. Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd stubichat/backend

# Copy environment configuration
cp env.example .env

# Edit .env with your OpenAI API key
nano .env
```

### 2. Start Services
```bash
# Start all services with Docker Compose
docker-compose up -d

# Or start services individually
docker-compose up main-backend
docker-compose up llm-agent
```

### 3. Verify Installation
```bash
# Test factory pattern implementation
python test_factory_structure.py

# Test service health
curl http://localhost:8000/health
curl http://localhost:8001/health

# Test chat functionality
python test_setup.py
```

## 📁 Project Structure

```
backend/
├── main-backend/                 # Main backend service
│   ├── app/
│   │   ├── api/                 # API routes
│   │   ├── core/                # Core functionality
│   │   ├── factory/             # Factory pattern
│   │   ├── models/              # Pydantic models
│   │   ├── services/            # Business logic
│   │   └── utils/               # Utilities
│   ├── Dockerfile
│   └── requirements.txt
├── llm-agent/                   # LLM agent service
│   ├── app/
│   │   ├── api/                 # API routes
│   │   ├── core/                # Core functionality
│   │   ├── factory/             # Factory pattern
│   │   ├── models/              # Pydantic models
│   │   ├── services/            # Business logic
│   │   └── utils/               # Utilities
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml           # Service orchestration
├── env.example                  # Environment template
├── .env                         # Environment configuration
└── README.md                    # This file
```

## 🔌 API Endpoints

### Main Backend (Port 8000)

#### Chat Endpoints
- `POST /chat/` - Process chat request
- `POST /chat/stream` - Stream chat response
- `GET /chat/health` - Health check

#### General Endpoints
- `GET /` - Service information
- `GET /health` - Health check
- `GET /docs` - API documentation (debug mode)

### LLM Agent (Port 8001)

#### Generation Endpoints
- `POST /generate/` - Generate text
- `POST /generate/stream` - Stream text generation
- `GET /generate/health` - Health check

#### General Endpoints
- `GET /` - Service information
- `GET /health` - Health check
- `GET /docs` - API documentation (debug mode)

## 🧪 Testing

### Factory Pattern Tests
```bash
# Test factory pattern implementation
python test_factory_structure.py
```

### Service Tests
```bash
# Test service functionality
python test_setup.py
```

### Manual Testing
```bash
# Test chat endpoint
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "gpt-4",
    "temperature": 0.7
  }'

# Test streaming
curl -X POST http://localhost:8001/generate/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "gpt-4"
  }'
```

## 🔧 Development

### Local Development
```bash
# Install dependencies
pip install -r main-backend/requirements.txt
pip install -r llm-agent/requirements.txt

# Start services locally
cd main-backend && python -m uvicorn app.main:app --reload --port 8000
cd llm-agent && python -m uvicorn app.main:app --reload --port 8001
```

### Adding New Features

#### 1. Add New Service
```python
# Create service factory
class NewServiceFactory:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._new_service = None
    
    @property
    def new_service(self):
        if self._new_service is None:
            self._new_service = NewService()
        return self._new_service
```

#### 2. Add New API Endpoint
```python
# Create router
router = APIRouter(prefix="/new", tags=["new"])

@router.post("/")
async def new_endpoint(
    request: NewRequest,
    new_service=Depends(get_new_service)
):
    return await new_service.process(request)
```

#### 3. Update App Factory
```python
# Add to create_routes method
app.include_router(new_router)
```

## 🐳 Docker

### Build Images
```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build main-backend
docker-compose build llm-agent
```

### Run Services
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📊 Monitoring

### Health Checks
- Main Backend: `http://localhost:8000/health`
- LLM Agent: `http://localhost:8001/health`

### Logging
- Structured logging with Loguru
- Request/response logging
- Performance metrics
- Error tracking

### Metrics
- Request duration
- Error rates
- Service health status
- OpenAI API usage

## 🔒 Security

### Environment Variables
- Sensitive data stored in `.env` files
- `.env` files excluded from version control
- Production secrets managed securely

### API Security
- CORS configuration
- Input validation with Pydantic
- Rate limiting
- Error handling without information leakage

## 🚀 Production Deployment

### Environment Setup
1. Configure production environment variables
2. Set up proper logging and monitoring
3. Configure reverse proxy (nginx)
4. Set up SSL certificates

### Scaling
- Horizontal scaling with load balancers
- Database connection pooling
- Redis for caching (optional)
- Message queues for async processing

## 🤝 Contributing

1. Follow the factory pattern for new features
2. Add tests for new functionality
3. Update documentation
4. Use conventional commit messages

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 