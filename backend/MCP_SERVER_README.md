# MCP Server Integration

This document describes the integration of a new MCP (Model Context Protocol) server into the existing Stubichat backend architecture.

## Overview

The MCP server is a new service that provides MCP-compatible tools and endpoints, built using the `fastapi-mcp` library. It follows the same factory pattern architecture as the other services and integrates seamlessly with the existing Docker Compose setup.

## Architecture

### Service Structure

```
backend/
├── mcp-server/                    # New MCP server service
│   ├── app/
│   │   ├── api/
│   │   │   └── tools.py          # MCP tools API endpoints
│   │   ├── core/
│   │   │   └── config.py         # Configuration management
│   │   ├── factory/
│   │   │   └── app_factory.py    # FastAPI app factory
│   │   ├── utils/
│   │   │   └── logger.py         # Logging utilities
│   │   └── main.py               # Application entry point
│   ├── Dockerfile                # Multi-stage Docker build
│   ├── .dockerignore             # Docker ignore rules
│   └── requirements.txt          # Python dependencies
├── docker-compose.yml            # Updated with MCP server
└── nginx/conf/nginx.conf         # Updated with MCP routing
```

### Service Ports

- **Main Backend**: `8000` (FastAPI + LangGraph)
- **LLM Agent**: `8001` (OpenAI-based)
- **MCP Server**: `8002` (FastAPI-MCP)
- **Nginx**: `80` (Reverse proxy)

## Features

### MCP Tools

#### Echo Tool
- **Endpoint**: `POST /tools/echo`
- **Description**: Simple echo tool that returns input with optional prefix
- **Request**:
  ```json
  {
    "message": "Hello World",
    "prefix": "Echo: "
  }
  ```
- **Response**:
  ```json
  {
    "result": "Echo: Hello World",
    "original_message": "Hello World",
    "prefix": "Echo: "
  }
  ```

#### Tools List
- **Endpoint**: `GET /tools/list`
- **Description**: Lists all available MCP tools
- **Response**:
  ```json
  {
    "tools": [
      {
        "name": "echo",
        "description": "Echo tool that returns the input message with an optional prefix",
        "endpoint": "/tools/echo",
        "method": "POST",
        "request_model": "EchoRequest",
        "response_model": "EchoResponse"
      }
    ],
    "count": 1,
    "server": "stubichat-mcp"
  }
  ```

### Health Endpoints

- **Service Health**: `GET /health`
- **Root Info**: `GET /`

## Factory Pattern Implementation

The MCP server follows the same factory pattern as other services:

### App Factory
- **Location**: `app/factory/app_factory.py`
- **Features**:
  - Lifespan management (startup/shutdown)
  - Middleware configuration (CORS, logging, trusted hosts)
  - Exception handlers
  - Route registration
  - Health checks

### Configuration
- **Location**: `app/core/config.py`
- **Features**:
  - Environment variable loading with `python-dotenv`
  - Pydantic settings validation
  - MCP server-specific configuration

## Docker Integration

### Dockerfile Features
- Multi-stage build for optimization
- Non-root user for security
- Health checks
- Proper layer caching
- Minimal base image (Python 3.12 slim)

### Docker Compose
The MCP server is integrated into the existing `docker-compose.yml`:

```yaml
mcp-server:
  build:
    context: ./mcp-server
    dockerfile: Dockerfile
  ports:
    - "8002:8002"
  volumes:
    - ./mcp-server/app:/app/app
    - ./logs:/app/logs
  environment:
    - PYTHONPATH=/app
    - DEBUG=true
  networks:
    - stubichat_network
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

### Nginx Integration
The MCP server is accessible through the nginx reverse proxy:

- **Direct Access**: `http://localhost:8002`
- **Through Nginx**: `http://localhost/mcp/`

Nginx configuration includes:
- Rate limiting
- Proxy headers
- Timeout settings
- Load balancing (if multiple instances)

## Testing

### Integration Test
A comprehensive test script (`test_mcp_integration.py`) verifies:

1. **Health Endpoints**: All services respond to health checks
2. **MCP Echo Tool**: Echo functionality works correctly
3. **MCP Tools List**: Tools listing endpoint works
4. **LLM Agent**: Direct LLM agent communication
5. **Main Backend Chat**: LangGraph workflow integration
6. **Service Integration**: Cross-service communication

### Test Results
```
============================================================
📊 TEST SUMMARY
============================================================
Total Tests: 8
Passed: 8 ✅
Failed: 0 ❌
Success Rate: 100.0%
============================================================
🎉 All tests passed! All services are working correctly.
```

## Usage Examples

### Direct Service Access

```bash
# Health check
curl http://localhost:8002/health

# Echo tool
curl -X POST http://localhost:8002/tools/echo \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello MCP", "prefix": "MCP: "}'

# Tools list
curl http://localhost:8002/tools/list
```

### Through Nginx Proxy

```bash
# Health check
curl http://localhost/mcp/health

# Echo tool
curl -X POST http://localhost/mcp/tools/echo \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello MCP", "prefix": "MCP: "}'
```

## Dependencies

### Python Packages
- `fastapi>=0.115.0` - Web framework
- `uvicorn[standard]>=0.27.0` - ASGI server
- `pydantic>=2.7.0` - Data validation
- `pydantic-settings>=2.5.2` - Settings management
- `python-dotenv==1.0.0` - Environment variable loading
- `fastapi-mcp==0.3.7` - MCP integration
- `httpx>=0.26.0` - HTTP client

### System Dependencies
- `curl` - For health checks
- Python 3.12

## Development

### Adding New MCP Tools

1. **Create Tool Endpoint** in `app/api/tools.py`:
   ```python
   @router.post("/new-tool")
   async def new_tool(request: NewToolRequest) -> NewToolResponse:
       # Tool implementation
       pass
   ```

2. **Update Tools List** in the `list_tools()` function

3. **Add Request/Response Models** as needed

4. **Test Integration** using the test script

### Environment Variables

Create a `.env` file in the backend directory:
```env
# MCP Server specific
DEBUG=true
LOG_LEVEL=INFO

# Other services
OPENAI_API_KEY=your_openai_api_key
```

## Monitoring and Logging

### Health Checks
- **Endpoint**: `/health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3

### Logging
- **Format**: Structured JSON logging
- **Level**: Configurable via `LOG_LEVEL`
- **Output**: Console and log files

### Metrics
- Request/response logging
- Performance timing
- Error tracking
- Service health status

## Security Considerations

- **Non-root User**: Services run as non-root user
- **Trusted Hosts**: Production middleware for host validation
- **CORS**: Configurable CORS settings
- **Rate Limiting**: Nginx-level rate limiting
- **Health Checks**: Regular service health monitoring

## Future Enhancements

1. **Additional MCP Tools**: File operations, database queries, etc.
2. **Authentication**: JWT-based authentication
3. **Metrics**: Prometheus metrics integration
4. **Caching**: Redis-based response caching
5. **Load Balancing**: Multiple MCP server instances
6. **Plugin System**: Dynamic tool loading

## Troubleshooting

### Common Issues

1. **Dependency Conflicts**: Ensure compatible package versions
2. **Port Conflicts**: Verify no other services use port 8002
3. **Health Check Failures**: Check service logs for errors
4. **Nginx Routing**: Verify nginx configuration

### Debug Commands

```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs mcp-server

# Test health endpoint
curl http://localhost:8002/health

# Run integration tests
python3 test_mcp_integration.py
```

## Conclusion

The MCP server integration provides a solid foundation for adding MCP-compatible tools to the Stubichat backend. The factory pattern ensures maintainability, while Docker integration provides scalability and ease of deployment. The comprehensive testing ensures reliability and proper integration with existing services. 