#!/usr/bin/env python3
"""
VLLM Server Logging System Demonstration

This script demonstrates the comprehensive logging system implemented for the VLLM server.
It showcases all major logging features including:
- Centralized logging configuration
- Request ID tracking
- Model performance monitoring
- Error handling with full tracebacks
- Different logging levels and outputs
- Integration with VLLM components

Run this script to see the logging system in action:
    python logging_demo.py
"""

import asyncio
import time
import logging
import random
from typing import Dict, Any
from vllm import SamplingParams

# Import the logging system
from app.logger import (
    get_logger,
    get_request_logger,
    get_model_performance_logger,
    log_exception,
    log_request_info,
    get_logging_stats,
    set_logging_level,
    request_id_var,
    LoggingConfig
)


def demo_basic_logging():
    """Demonstrate basic logging functionality."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Logging Functionality")
    print("="*60)
    
    # Get different loggers
    main_logger = get_logger("demo_main")
    service_logger = get_logger("demo_service")
    router_logger = get_logger("demo_router")
    
    # Demonstrate different log levels
    main_logger.debug("This is a DEBUG message - detailed information")
    main_logger.info("This is an INFO message - general information")
    main_logger.warning("This is a WARNING message - something might be wrong")
    main_logger.error("This is an ERROR message - something went wrong")
    main_logger.critical("This is a CRITICAL message - serious error")
    
    # Show module-specific logging
    service_logger.info("Service module: Model loading completed")
    router_logger.info("Router module: API endpoint registered")
    
    print("\n✓ Basic logging demo completed - check console and log files")


def demo_request_tracking():
    """Demonstrate request ID tracking functionality."""
    print("\n" + "="*60)
    print("DEMO 2: Request ID Tracking")
    print("="*60)
    
    # Simulate different requests with request IDs
    for i in range(3):
        request_id = f"req_{i+1:03d}"
        
        # Set request context
        request_id_var.set(request_id)
        
        # Get request logger
        request_logger = get_request_logger(request_id)
        
        # Simulate request processing
        request_logger.info(f"Processing request {i+1}")
        request_logger.debug(f"Request parameters: max_tokens=150, temperature=0.7")
        
        # Simulate some processing
        time.sleep(0.1)
        
        request_logger.info(f"Request {i+1} completed successfully")
    
    print("\n✓ Request tracking demo completed - notice request IDs in logs")


def demo_model_performance_logging():
    """Demonstrate model performance monitoring."""
    print("\n" + "="*60)
    print("DEMO 3: Model Performance Monitoring")
    print("="*60)
    
    perf_logger = get_logger("demo_performance")
    
    # Simulate different model operations
    operations = [
        ("model_loading", None, 2.5),
        ("text_generation", 50, 1.2),
        ("embedding_creation", 100, 0.8),
        ("batch_processing", 200, 3.1)
    ]
    
    for operation_name, prompt_tokens, duration in operations:
        with get_model_performance_logger(perf_logger, operation_name, prompt_tokens) as perf:
            perf_logger.info(f"Starting {operation_name}...")
            
            # Simulate processing time
            time.sleep(duration)
            
            # For text generation, set completion tokens
            if operation_name == "text_generation":
                perf.set_completion_tokens(75)
            elif operation_name == "batch_processing":
                perf.set_completion_tokens(300)
            
            perf_logger.info(f"{operation_name} processing completed")
    
    print("\n✓ Performance monitoring demo completed - check timing information")


def demo_error_handling():
    """Demonstrate error handling and exception logging."""
    print("\n" + "="*60)
    print("DEMO 4: Error Handling and Exception Logging")
    print("="*60)
    
    error_logger = get_logger("demo_errors")
    
    # Simulate different types of errors
    error_scenarios = [
        ("validation_error", "Invalid prompt: empty string"),
        ("model_error", "CUDA out of memory"),
        ("network_error", "Connection timeout to remote service"),
        ("parsing_error", "Failed to parse JSON response")
    ]
    
    for error_type, error_msg in error_scenarios:
        try:
            # Simulate error conditions
            if error_type == "validation_error":
                raise ValueError(error_msg)
            elif error_type == "model_error":
                raise RuntimeError(error_msg)
            elif error_type == "network_error":
                raise ConnectionError(error_msg)
            elif error_type == "parsing_error":
                raise json.JSONDecodeError(error_msg, "", 0)
                
        except Exception as e:
            log_exception(error_logger, f"Simulated {error_type}", e)
    
    print("\n✓ Error handling demo completed - check exception tracebacks")


def demo_request_logging():
    """Demonstrate API request logging."""
    print("\n" + "="*60)
    print("DEMO 5: API Request Logging")
    print("="*60)
    
    # Simulate different API requests
    requests = [
        ("POST", "/generate", "192.168.1.100", 250, '{"prompt": "Hello world", "max_tokens": 100}'),
        ("GET", "/health", "192.168.1.101", None, None),
        ("POST", "/generate", "192.168.1.102", 500, '{"prompt": "Write a story about...", "stream": true}'),
        ("GET", "/model/info", "192.168.1.103", None, None),
        ("POST", "/generate", "192.168.1.104", 1200, '{"prompt": "Very long prompt...", "temperature": 0.8}')
    ]
    
    for method, endpoint, client_ip, body_size, body_preview in requests:
        # Generate request ID
        request_id = f"req_{random.randint(1000, 9999)}"
        request_id_var.set(request_id)
        
        # Get request logger
        api_logger = get_request_logger(request_id)
        
        # Log request information
        log_request_info(api_logger, method, endpoint, client_ip, body_size, body_preview)
        
        # Simulate request processing
        processing_time = random.uniform(0.1, 2.0)
        time.sleep(processing_time)
        
        # Log response
        status_code = random.choice([200, 200, 200, 400, 500])  # Mostly successful
        api_logger.info(f"Request completed: {status_code} | duration: {processing_time:.3f}s")
    
    print("\n✓ API request logging demo completed")


async def demo_streaming_logging():
    """Demonstrate streaming operation logging."""
    print("\n" + "="*60)
    print("DEMO 6: Streaming Operation Logging")
    print("="*60)
    
    stream_logger = get_logger("demo_streaming")
    
    # Simulate streaming text generation
    request_id = "stream_req_001"
    request_id_var.set(request_id)
    
    stream_logger.info("Starting streaming text generation")
    
    # Simulate streaming chunks
    chunks = [
        "Hello,", " this", " is", " a", " streaming", " text", " generation", 
        " demo", " showing", " how", " logging", " works", " with", " async", 
        " operations", " and", " streaming", " responses."
    ]
    
    total_chars = 0
    for i, chunk in enumerate(chunks):
        stream_logger.debug(f"Sending chunk {i+1}/{len(chunks)}: '{chunk}'")
        total_chars += len(chunk)
        
        # Simulate streaming delay
        await asyncio.sleep(0.1)
    
    stream_logger.info(f"Streaming completed: {len(chunks)} chunks, {total_chars} characters")
    print("\n✓ Streaming operation logging demo completed")


def demo_vllm_integration():
    """Demonstrate VLLM-specific logging integration."""
    print("\n" + "="*60)
    print("DEMO 7: VLLM Integration Logging")
    print("="*60)
    
    vllm_logger = get_logger("vllm_integration")
    
    # Simulate VLLM model operations
    vllm_logger.info("=== VLLM Model Operations Demo ===")
    
    # Simulate model loading
    vllm_logger.info("Loading VLLM model...")
    with get_model_performance_logger(vllm_logger, "model_loading") as perf:
        time.sleep(1.5)  # Simulate model loading time
        vllm_logger.info("Model loaded successfully")
    
    # Simulate text generation
    vllm_logger.info("Performing text generation...")
    sampling_params = {
        "max_tokens": 150,
        "temperature": 0.7,
        "top_p": 0.95
    }
    
    vllm_logger.debug(f"Sampling parameters: {sampling_params}")
    
    with get_model_performance_logger(vllm_logger, "text_generation", 25) as perf:
        time.sleep(0.8)  # Simulate generation time
        perf.set_completion_tokens(45)
        vllm_logger.info("Text generation completed")
    
    # Simulate batch processing
    vllm_logger.info("Processing batch of 5 requests...")
    for i in range(5):
        request_id = f"batch_req_{i+1}"
        request_id_var.set(request_id)
        
        batch_logger = get_request_logger(request_id)
        with get_model_performance_logger(batch_logger, "batch_item_processing", 30) as perf:
            time.sleep(0.3)  # Simulate individual request processing
            perf.set_completion_tokens(20)
            batch_logger.info(f"Batch item {i+1} processed")
    
    vllm_logger.info("Batch processing completed")
    print("\n✓ VLLM integration logging demo completed")


def demo_logging_configuration():
    """Demonstrate logging configuration options."""
    print("\n" + "="*60)
    print("DEMO 8: Logging Configuration")
    print("="*60)
    
    config_logger = get_logger("demo_config")
    
    # Show current configuration
    stats = get_logging_stats()
    config_logger.info("=== Current Logging Configuration ===")
    config_logger.info(f"Server name: {stats['server_name']}")
    config_logger.info(f"Log directory: {stats['log_directory']}")
    config_logger.info(f"Current level: {stats['current_level']}")
    config_logger.info(f"Total loggers: {stats['total_loggers']}")
    config_logger.info(f"Console output: {stats['console_output_enabled']}")
    config_logger.info(f"Performance logging: {stats['performance_logging_enabled']}")
    config_logger.info(f"Request tracking: {stats['request_tracking_enabled']}")
    
    # Demonstrate log level changes
    config_logger.info("Changing log level to DEBUG for detailed output...")
    set_logging_level(logging.DEBUG)
    
    config_logger.debug("This DEBUG message is now visible")
    config_logger.info("Log level changed successfully")
    
    # Change back to INFO
    set_logging_level(logging.INFO)
    config_logger.info("Log level changed back to INFO")
    config_logger.debug("This DEBUG message should not appear")
    
    print("\n✓ Logging configuration demo completed")


def demo_production_scenarios():
    """Demonstrate production-like logging scenarios."""
    print("\n" + "="*60)
    print("DEMO 9: Production Scenarios")
    print("="*60)
    
    prod_logger = get_logger("production_demo")
    
    # Simulate production scenarios
    scenarios = [
        {
            "name": "High Load Processing",
            "requests": 10,
            "description": "Simulating high concurrent request load"
        },
        {
            "name": "Error Recovery",
            "requests": 3,
            "description": "Simulating error conditions and recovery"
        },
        {
            "name": "Model Switching",
            "requests": 1,
            "description": "Simulating model reload operations"
        }
    ]
    
    for scenario in scenarios:
        prod_logger.info(f"=== {scenario['name']} ===")
        prod_logger.info(f"Description: {scenario['description']}")
        
        for i in range(scenario['requests']):
            request_id = f"{scenario['name'].lower().replace(' ', '_')}_req_{i+1}"
            request_id_var.set(request_id)
            
            scenario_logger = get_request_logger(request_id)
            
            try:
                if scenario['name'] == "High Load Processing":
                    # Simulate normal processing
                    with get_model_performance_logger(scenario_logger, "high_load_generation", 40) as perf:
                        time.sleep(random.uniform(0.2, 0.8))
                        perf.set_completion_tokens(60)
                        scenario_logger.info("High load request processed successfully")
                
                elif scenario['name'] == "Error Recovery":
                    # Simulate errors
                    if i == 1:  # Second request fails
                        raise RuntimeError("Simulated processing error")
                    else:
                        scenario_logger.info("Error recovery request processed successfully")
                
                elif scenario['name'] == "Model Switching":
                    # Simulate model operations
                    scenario_logger.info("Unloading current model...")
                    time.sleep(0.5)
                    scenario_logger.info("Loading new model...")
                    with get_model_performance_logger(scenario_logger, "model_reload") as perf:
                        time.sleep(2.0)
                        scenario_logger.info("Model reload completed successfully")
                
            except Exception as e:
                log_exception(scenario_logger, f"Error in {scenario['name']}", e)
                scenario_logger.info("Attempting error recovery...")
                time.sleep(0.2)
                scenario_logger.info("Error recovery completed")
    
    print("\n✓ Production scenarios demo completed")


def demo_system_monitoring():
    """Demonstrate system monitoring and statistics."""
    print("\n" + "="*60)
    print("DEMO 10: System Monitoring")
    print("="*60)
    
    monitor_logger = get_logger("system_monitor")
    
    # Simulate system monitoring
    monitor_logger.info("=== System Monitoring Demo ===")
    
    # Get logging statistics
    stats = get_logging_stats()
    monitor_logger.info(f"Active loggers: {stats['total_loggers']}")
    monitor_logger.info(f"Logger names: {', '.join(stats['logger_names'][:5])}...")
    
    # Simulate resource monitoring
    monitor_logger.info("Checking system resources...")
    
    # Simulate memory usage
    memory_usage = random.uniform(60, 85)
    if memory_usage > 80:
        monitor_logger.warning(f"High memory usage detected: {memory_usage:.1f}%")
    else:
        monitor_logger.info(f"Memory usage normal: {memory_usage:.1f}%")
    
    # Simulate GPU usage
    gpu_usage = random.uniform(70, 95)
    if gpu_usage > 90:
        monitor_logger.warning(f"High GPU usage detected: {gpu_usage:.1f}%")
    else:
        monitor_logger.info(f"GPU usage: {gpu_usage:.1f}%")
    
    # Simulate performance metrics
    avg_response_time = random.uniform(0.5, 2.0)
    if avg_response_time > 1.5:
        monitor_logger.warning(f"Slow response time: {avg_response_time:.2f}s")
    else:
        monitor_logger.info(f"Average response time: {avg_response_time:.2f}s")
    
    monitor_logger.info("System monitoring check completed")
    print("\n✓ System monitoring demo completed")


async def main():
    """Main demonstration function."""
    print("VLLM Server Logging System Demonstration")
    print("="*60)
    print(f"Log files will be created in: {LoggingConfig.LOG_DIR}/")
    print(f"Log file pattern: {LoggingConfig.LOG_FILE_PREFIX}_{LoggingConfig.SERVER_NAME}_YYYY-MM-DD.txt")
    print("="*60)
    
    # Run all demonstrations
    demo_basic_logging()
    demo_request_tracking()
    demo_model_performance_logging()
    demo_error_handling()
    demo_request_logging()
    await demo_streaming_logging()
    demo_vllm_integration()
    demo_logging_configuration()
    demo_production_scenarios()
    demo_system_monitoring()
    
    # Final summary
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETED")
    print("="*60)
    
    # Show final statistics
    final_stats = get_logging_stats()
    print(f"✓ Total loggers created: {final_stats['total_loggers']}")
    print(f"✓ Log directory: {final_stats['log_directory']}")
    print(f"✓ Current log level: {final_stats['current_level']}")
    print(f"✓ Check log files for detailed output")
    print(f"✓ All logging features demonstrated successfully")
    
    print("\nKey Features Demonstrated:")
    print("- Centralized logging with daily rotation")
    print("- Request ID tracking for distributed tracing")
    print("- Model performance monitoring with timing")
    print("- Comprehensive error handling and tracebacks")
    print("- API request logging with client information")
    print("- Streaming operation logging")
    print("- VLLM-specific integration logging")
    print("- Dynamic configuration changes")
    print("- Production scenario simulation")
    print("- System monitoring and statistics")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main()) 