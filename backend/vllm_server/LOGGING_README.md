# VLLM Server Centralized Logging System

A comprehensive, production-ready logging system for the VLLM server with daily log rotation, request tracking, performance monitoring, and extensive error handling.

## 🎯 Features

### Core Logging Features
- **Daily Log Rotation**: Automatic daily log file rotation with configurable retention
- **Console & File Output**: Simultaneous logging to console and files
- **Structured Format**: Consistent log format with timestamps, levels, modules, and request IDs
- **Color-Coded Console**: Enhanced readability with color-coded log levels
- **Request Tracking**: Distributed tracing with unique request IDs
- **Performance Monitoring**: Built-in timing and throughput measurement
- **Exception Handling**: Comprehensive error logging with full tracebacks

### VLLM-Specific Features
- **Model Inference Logging**: Detailed logging for text generation operations
- **Streaming Support**: Specialized logging for streaming responses
- **Token Throughput Tracking**: Performance metrics for token generation
- **Model Loading Monitoring**: Comprehensive model initialization logging
- **Resource Usage Tracking**: Memory and GPU utilization monitoring

### Production Features
- **Thread-Safe Operations**: Safe for concurrent request processing
- **Configurable Log Levels**: Runtime log level adjustment
- **Extensible Design**: Easy integration of remote logging destinations
- **Health Monitoring**: Built-in system health checks and statistics
- **Batch Operation Support**: Efficient logging for batch processing

## 📁 Log File Structure

```
logs/
├── logging_vllmserver_2025-01-19.txt    # Current day logs
├── logging_vllmserver_2025-01-18.txt    # Previous day logs
├── logging_vllmserver_2025-01-17.txt    # Older logs (up to 30 days)
└── ...
```

### Log Format
```
YYYY-MM-DD HH:MM:SS | LEVEL    | module_name           | function_name        | request_id | message
2025-01-19 14:30:15 | INFO     | app.main              | create_app          | no-req     | VLLM Server starting up
2025-01-19 14:30:16 | INFO     | app.factory.model     | create_model        | no-req     | Model loading completed
2025-01-19 14:30:20 | INFO     | app.routers.generate  | generate_text       | req_a1b2c3 | Processing generation request
```

## 🚀 Quick Start

### Basic Usage

```python
from app.logger import get_logger

# Get a logger for your module
logger = get_logger(__name__)

# Basic logging
logger.info("Service started successfully")
logger.warning("High memory usage detected")
logger.error("Failed to process request")
```

### Request Tracking

```python
from app.logger import get_request_logger, request_id_var

# Set request context (usually done by middleware)
request_id_var.set("req_12345")

# Get request-aware logger
request_logger = get_request_logger("req_12345")
request_logger.info("Processing user request")
```

### Performance Monitoring

```python
from app.logger import get_logger, get_model_performance_logger

logger = get_logger(__name__)

# Monitor model inference performance
with get_model_performance_logger(logger, "text_generation", prompt_tokens=100) as perf:
    # Your model inference code here
    result = model.generate(prompt)
    
    # Set completion tokens for throughput calculation
    perf.set_completion_tokens(150)
# Automatically logs timing and throughput metrics
```

### Error Handling

```python
from app.logger import get_logger, log_exception

logger = get_logger(__name__)

try:
    # Your code that might fail
    result = risky_operation()
except Exception as e:
    log_exception(logger, "Operation failed", e)
    # Logs full traceback with request context
```

## 📊 Integration Examples

### FastAPI Middleware Integration

The logging system is automatically integrated into the VLLM server through middleware:

```python
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Generate unique request ID
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    request_id_var.set(request_id)
    
    # Log incoming request
    request_logger = get_request_logger(request_id)
    log_request_info(request_logger, request.method, str(request.url.path))
    
    # Process request with timing
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Log response
    request_logger.info(f"Request completed: {response.status_code} | duration: {duration:.3f}s")
    return response
```

### Model Factory Integration

```python
class ModelFactory:
    @staticmethod
    def create_model() -> LLM:
        logger = get_logger(__name__)
        logger.info("Starting VLLM model creation")
        
        with get_model_performance_logger(logger, "model_creation") as perf:
            model = LLM(
                model=settings.MODEL_PATH,
                tensor_parallel_size=settings.TENSOR_PARALLEL_SIZE,
                # ... other parameters
            )
            logger.info("Model created successfully")
        
        return model
```

### LLM Service Integration

```python
class LLMService:
    def generate(self, prompt: str, sampling_params: SamplingParams) -> Dict:
        request_logger = get_request_logger()
        request_logger.info(f"Starting text generation (prompt_length: {len(prompt)})")
        
        try:
            with get_model_performance_logger(request_logger, "text_generation", len(prompt.split())) as perf:
                outputs = self.model.generate(prompts=[prompt], sampling_params=sampling_params)
                generated_text = outputs[0].outputs[0].text
                perf.set_completion_tokens(len(generated_text.split()))
                
            request_logger.info("Text generation completed successfully")
            return {"text": generated_text, "usage": {...}}
            
        except Exception as e:
            log_exception(request_logger, "Text generation failed", e)
            raise
```

## ⚙️ Configuration

### Environment Variables

```bash
# Log level configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
CONSOLE_LOG_LEVEL=INFO           # Console output level

# Performance monitoring
SLOW_OPERATION_THRESHOLD=2.0     # Seconds threshold for slow operation warnings

# Request logging
LOG_REQUEST_BODY=true            # Whether to log request body previews
MAX_BODY_SIZE_LOG=1000          # Maximum characters to log from request body
```

### Runtime Configuration

```python
from app.logger import set_logging_level, get_logging_stats
import logging

# Change log level at runtime
set_logging_level(logging.DEBUG)

# Get logging system statistics
stats = get_logging_stats()
print(f"Total loggers: {stats['total_loggers']}")
print(f"Current level: {stats['current_level']}")
```

## 📈 Monitoring and Statistics

### Health Check Integration

```python
@app.get("/health")
async def health_check():
    health_logger = get_logger("health")
    
    # Get logging system stats
    log_stats = get_logging_stats()
    
    return {
        "status": "healthy",
        "logging": {
            "total_loggers": log_stats["total_loggers"],
            "log_level": log_stats["current_level"],
            "log_directory": log_stats["log_directory"]
        }
    }
```

### Performance Metrics

The logging system automatically tracks:
- **Request Processing Time**: End-to-end request duration
- **Model Inference Time**: Time spent in model.generate()
- **Token Throughput**: Tokens per second for generation
- **Error Rates**: Frequency and types of errors
- **Resource Usage**: Memory and GPU utilization patterns

### Log Analysis Examples

```bash
# Find slow operations
grep "Slow.*generation" logs/logging_vllmserver_*.txt

# Track error patterns
grep "ERROR" logs/logging_vllmserver_*.txt | head -20

# Monitor specific request
grep "req_abc123" logs/logging_vllmserver_*.txt

# Performance analysis
grep "tokens_per_second" logs/logging_vllmserver_*.txt
```

## 🔧 Advanced Features

### Custom Log Destinations

```python
from app.logger import add_remote_logging_handler
import logging.handlers

# Add HTTP logging for centralized log collection
http_handler = logging.handlers.HTTPHandler(
    'log-collector.example.com', 
    '/api/logs', 
    method='POST'
)
add_remote_logging_handler(http_handler)

# Add Syslog for system integration
syslog_handler = logging.handlers.SysLogHandler(address=('localhost', 514))
add_remote_logging_handler(syslog_handler)
```

### Batch Operation Logging

```python
def process_batch_requests(requests):
    batch_logger = get_logger("batch_processor")
    batch_logger.info(f"Starting batch processing: {len(requests)} requests")
    
    for i, request in enumerate(requests):
        request_id = f"batch_req_{i+1}"
        request_id_var.set(request_id)
        
        item_logger = get_request_logger(request_id)
        with get_model_performance_logger(item_logger, "batch_item", request.prompt_tokens) as perf:
            result = process_single_request(request)
            perf.set_completion_tokens(result.completion_tokens)
            item_logger.info(f"Batch item {i+1} completed")
    
    batch_logger.info("Batch processing completed")
```

### Error Recovery Logging

```python
def robust_generation(prompt, max_retries=3):
    logger = get_logger(__name__)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Generation attempt {attempt + 1}/{max_retries}")
            return model.generate(prompt)
            
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                log_exception(logger, "All generation attempts failed", e)
                raise
```

## 🧪 Testing and Demonstration

### Run the Demo

```bash
cd stubichat/backend/vllm_server
python vllm_logging_demo.py
```

The demo showcases:
- Basic logging functionality across different modules
- Request ID tracking for distributed tracing
- Model performance monitoring with timing
- Error handling and exception logging
- API request logging simulation
- Streaming operation logging
- VLLM-specific integration examples
- Dynamic configuration changes
- Production scenario simulation
- System monitoring and statistics

### Example Output

```
VLLM Server Logging System Demonstration
============================================================
Log files will be created in: logs/
Log file pattern: logging_vllmserver_YYYY-MM-DD.txt
============================================================

DEMO 1: Basic Logging Functionality
============================================================
2025-01-19 14:30:15 | INFO     | demo_main             | demo_basic_logging  | no-req     | This is an INFO message
2025-01-19 14:30:15 | WARNING  | demo_main             | demo_basic_logging  | no-req     | This is a WARNING message
2025-01-19 14:30:15 | ERROR    | demo_main             | demo_basic_logging  | no-req     | This is an ERROR message

✓ Basic logging demo completed - check console and log files
```

## 📋 Best Practices

### 1. Use Appropriate Log Levels
```python
logger.debug("Detailed debugging information")      # Development only
logger.info("Normal operational messages")          # Production events
logger.warning("Something unexpected happened")     # Potential issues
logger.error("An error occurred")                  # Error conditions
logger.critical("System cannot continue")          # Critical failures
```

### 2. Include Context Information
```python
# Good: Include relevant context
logger.info(f"Processing request: prompt_length={len(prompt)}, model={model_name}")

# Better: Use structured logging
logger.info("Request processed", extra={
    "prompt_length": len(prompt),
    "model_name": model_name,
    "duration": processing_time
})
```

### 3. Handle Sensitive Information
```python
# Good: Avoid logging sensitive data
logger.info(f"User authentication successful: user_id={user_id}")

# Bad: Don't log passwords, tokens, or PII
logger.info(f"User login: {username}:{password}")  # Don't do this!
```

### 4. Use Performance Logging for Critical Operations
```python
# Always monitor model operations
with get_model_performance_logger(logger, "text_generation", prompt_tokens) as perf:
    result = model.generate(prompt)
    perf.set_completion_tokens(completion_tokens)
```

### 5. Implement Proper Error Handling
```python
try:
    result = risky_operation()
except SpecificException as e:
    logger.warning(f"Expected error occurred: {e}")
    # Handle gracefully
except Exception as e:
    log_exception(logger, "Unexpected error in operation", e)
    # Re-raise or handle as appropriate
    raise
```

## 🔍 Troubleshooting

### Common Issues

1. **Log files not created**
   - Check directory permissions for `logs/` folder
   - Verify disk space availability
   - Check LOG_DIR configuration

2. **Missing request IDs**
   - Ensure middleware is properly configured
   - Verify request_id_var.set() is called
   - Check FastAPI middleware order

3. **Performance logging not working**
   - Confirm get_model_performance_logger usage
   - Check if set_completion_tokens() is called
   - Verify context manager usage

4. **Console colors not showing**
   - Check terminal compatibility
   - Verify TERM environment variable
   - Test with different terminal emulators

### Debug Mode

```python
# Enable debug logging temporarily
from app.logger import set_logging_level
import logging

set_logging_level(logging.DEBUG)
# ... debug your issue ...
set_logging_level(logging.INFO)  # Restore normal level
```

## 📚 API Reference

### Core Functions

- `get_logger(name: str, level: Optional[int] = None) -> logging.Logger`
- `get_request_logger(request_id: str = None) -> logging.Logger`
- `set_logging_level(level: int)`
- `get_logging_stats() -> Dict[str, Any]`

### Performance Monitoring

- `get_model_performance_logger(logger, operation_name, prompt_tokens=None) -> ModelPerformanceLogger`
- `ModelPerformanceLogger.set_completion_tokens(count: int)`

### Error Handling

- `log_exception(logger, message: str, exc: Optional[Exception] = None)`
- `log_request_info(logger, method, endpoint, client_ip=None, body_size=None, body_preview=None)`

### Configuration

- `LoggingConfig` - Central configuration class
- `add_remote_logging_handler(handler: logging.Handler)`

## 🤝 Contributing

To extend or modify the logging system:

1. Add new log handlers in `VLLMLoggingManager`
2. Extend `ModelPerformanceLogger` for new metrics
3. Add configuration options to `LoggingConfig`
4. Update documentation and demo scripts

## 📄 License

This logging system is part of the VLLM server project and follows the same licensing terms.

---

**Ready to use!** The logging system is production-ready and integrated throughout the VLLM server codebase. Check the log files in the `logs/` directory and run the demo script to see it in action. 