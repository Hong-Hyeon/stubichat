#!/usr/bin/env python3
"""
Centralized Logging System Demo

This script demonstrates how to use the centralized logging system
across different components of the RAG backend system.
"""

import asyncio
import time
import logging
from typing import List, Dict, Any

# Import the centralized logging system
from app.logger import (
    get_logger, 
    set_logging_level, 
    get_performance_logger, 
    log_exception,
    get_logging_stats,
    LoggingConfig
)

# Create loggers for different modules
main_logger = get_logger(__name__)
embedding_logger = get_logger("demo.embedding")
vector_store_logger = get_logger("demo.vector_store")
rag_service_logger = get_logger("demo.rag_service")


def demo_basic_logging():
    """Demonstrate basic logging functionality."""
    main_logger.info("=== Basic Logging Demo ===")
    
    # Different log levels
    main_logger.debug("This is a debug message")
    main_logger.info("This is an info message")
    main_logger.warning("This is a warning message")
    main_logger.error("This is an error message")
    main_logger.critical("This is a critical message")
    
    # Logging with module-specific loggers
    embedding_logger.info("Embedding service initialized")
    vector_store_logger.info("Vector store connection established")
    rag_service_logger.info("RAG service ready for requests")


def demo_structured_logging():
    """Demonstrate structured logging with metadata."""
    main_logger.info("=== Structured Logging Demo ===")
    
    # Simulate document processing
    doc_id = "doc_123"
    doc_title = "AI Introduction"
    chunk_count = 5
    
    embedding_logger.info(f"Processing document '{doc_title}' (ID: {doc_id})")
    embedding_logger.debug(f"Document chunked into {chunk_count} parts")
    
    for i in range(chunk_count):
        embedding_logger.debug(f"Embedding chunk {i+1}/{chunk_count}")
        time.sleep(0.1)  # Simulate processing
    
    embedding_logger.info(f"Successfully embedded {chunk_count} chunks for document {doc_id}")


async def demo_performance_logging():
    """Demonstrate performance logging with context managers."""
    main_logger.info("=== Performance Logging Demo ===")
    
    # Example 1: Document embedding timing
    with get_performance_logger(embedding_logger, "document_embedding"):
        embedding_logger.debug("Starting document embedding process")
        await asyncio.sleep(0.5)  # Simulate embedding generation
        embedding_logger.debug("Document embedding completed")
    
    # Example 2: Vector search timing
    with get_performance_logger(vector_store_logger, "similarity_search"):
        vector_store_logger.debug("Executing similarity search query")
        await asyncio.sleep(0.3)  # Simulate database query
        vector_store_logger.info("Retrieved 5 similar chunks")
    
    # Example 3: Slow operation warning
    with get_performance_logger(rag_service_logger, "slow_operation"):
        rag_service_logger.debug("Starting potentially slow operation")
        await asyncio.sleep(1.5)  # This will trigger slow operation warning
        rag_service_logger.debug("Slow operation completed")


def demo_error_handling():
    """Demonstrate error logging with full tracebacks."""
    main_logger.info("=== Error Handling Demo ===")
    
    # Example 1: Simple error logging
    try:
        _ = 10 / 0  # This will raise ZeroDivisionError
    except ZeroDivisionError as e:
        log_exception(main_logger, "Division by zero occurred in calculation", e)
    
    # Example 2: Nested function error
    def risky_embedding_operation():
        """Simulate an embedding operation that might fail."""
        raise ValueError("Invalid input format for embedding model")
    
    try:
        risky_embedding_operation()
    except ValueError as e:
        log_exception(embedding_logger, "Failed to generate embeddings", e)
    
    # Example 3: Network/Database error simulation
    def simulate_database_error():
        """Simulate a database connection error."""
        raise ConnectionError("Could not connect to PostgreSQL database")
    
    try:
        simulate_database_error()
    except ConnectionError as e:
        log_exception(vector_store_logger, "Database connection failed", e)


def demo_different_log_levels():
    """Demonstrate dynamic log level changes."""
    main_logger.info("=== Dynamic Log Level Demo ===")
    
    # Show current level
    main_logger.info("Current logging level: INFO")
    main_logger.debug("This debug message won't appear")
    main_logger.info("This info message will appear")
    
    # Change to DEBUG level
    main_logger.info("Changing logging level to DEBUG")
    set_logging_level(logging.DEBUG)
    
    main_logger.debug("Now this debug message will appear!")
    main_logger.info("Info messages still appear")
    
    # Change back to INFO level
    main_logger.info("Changing logging level back to INFO")
    set_logging_level(logging.INFO)
    
    main_logger.debug("This debug message is hidden again")
    main_logger.info("Back to normal INFO level logging")


def demo_batch_operations():
    """Demonstrate logging for batch operations."""
    main_logger.info("=== Batch Operations Demo ===")
    
    # Simulate batch document ingestion
    documents = [
        {"title": "AI Basics", "content": "Introduction to AI..."},
        {"title": "ML Fundamentals", "content": "Machine learning concepts..."},
        {"title": "Deep Learning", "content": "Neural networks and..."},
        {"title": "NLP Guide", "content": "Natural language processing..."},
    ]
    
    rag_service_logger.info(f"Starting batch ingestion of {len(documents)} documents")
    
    successful = 0
    for i, doc in enumerate(documents):
        try:
            rag_service_logger.debug(f"Processing document {i+1}/{len(documents)}: {doc['title']}")
            
            # Simulate random failures
            if i == 2:  # Simulate failure on third document
                raise ValueError("Invalid document format")
            
            # Simulate processing time
            time.sleep(0.1)
            successful += 1
            rag_service_logger.debug(f"Successfully processed: {doc['title']}")
            
            # Log progress for large batches
            if len(documents) > 3:
                progress = ((i + 1) / len(documents)) * 100
                rag_service_logger.info(f"Batch progress: {i+1}/{len(documents)} ({progress:.1f}%)")
            
        except Exception as e:
            log_exception(rag_service_logger, f"Failed to process document: {doc['title']}", e)
    
    rag_service_logger.info(f"Batch ingestion completed: {successful}/{len(documents)} successful")


def demo_multilingual_logging():
    """Demonstrate logging with multilingual content."""
    main_logger.info("=== Multilingual Logging Demo ===")
    
    # Different language examples
    languages = [
        ("Korean", "한국어 문서를 처리하고 있습니다"),
        ("Japanese", "日本語のドキュメントを処理しています"),
        ("English", "Processing English document"),
        ("Chinese", "正在处理中文文档"),
    ]
    
    for lang, message in languages:
        embedding_logger.info(f"Processing {lang} content: {message}")
        embedding_logger.debug(f"Text length: {len(message)} characters")


def demo_system_monitoring():
    """Demonstrate system monitoring and statistics."""
    main_logger.info("=== System Monitoring Demo ===")
    
    # Get and display logging statistics
    stats = get_logging_stats()
    main_logger.info("Current logging system statistics:")
    main_logger.info(f"  - Total loggers: {stats['total_loggers']}")
    main_logger.info(f"  - Log directory: {stats['log_directory']}")
    main_logger.info(f"  - Server name: {stats['server_name']}")
    main_logger.info(f"  - Current level: {stats['current_level']}")
    main_logger.info(f"  - Console output: {stats['console_output_enabled']}")
    
    # Display logger names
    main_logger.debug(f"Active loggers: {', '.join(stats['logger_names'])}")


async def demo_comprehensive_rag_workflow():
    """Demonstrate logging throughout a complete RAG workflow."""
    main_logger.info("=== Comprehensive RAG Workflow Demo ===")
    
    workflow_logger = get_logger("demo.workflow")
    
    try:
        # Step 1: Document ingestion
        workflow_logger.info("Step 1: Starting document ingestion")
        with get_performance_logger(workflow_logger, "document_ingestion"):
            embedding_logger.info("Chunking document into segments")
            await asyncio.sleep(0.2)
            
            embedding_logger.info("Generating embeddings for 3 chunks")
            await asyncio.sleep(0.3)
            
            vector_store_logger.info("Storing embeddings in vector database")
            await asyncio.sleep(0.1)
        
        # Step 2: Query processing
        workflow_logger.info("Step 2: Processing user query")
        query = "What is machine learning?"
        workflow_logger.debug(f"Query: '{query}'")
        
        with get_performance_logger(workflow_logger, "query_processing"):
            embedding_logger.info("Embedding user query")
            await asyncio.sleep(0.1)
            
            vector_store_logger.info("Performing similarity search")
            await asyncio.sleep(0.2)
            
            workflow_logger.info("Retrieved 3 relevant chunks")
            workflow_logger.debug("Similarity scores: [0.95, 0.87, 0.82]")
        
        # Step 3: Response generation
        workflow_logger.info("Step 3: Constructing response prompt")
        with get_performance_logger(workflow_logger, "prompt_construction"):
            workflow_logger.debug("Building context from retrieved chunks")
            await asyncio.sleep(0.1)
            workflow_logger.info("Prompt constructed successfully")
        
        workflow_logger.info("RAG workflow completed successfully")
        
    except Exception as e:
        log_exception(workflow_logger, "RAG workflow failed", e)


def display_logging_configuration():
    """Display current logging configuration."""
    main_logger.info("=== Logging Configuration ===")
    main_logger.info(f"Server Name: {LoggingConfig.SERVER_NAME}")
    main_logger.info(f"Log Directory: {LoggingConfig.LOG_DIR}")
    main_logger.info(f"Log File Pattern: {LoggingConfig.LOG_FILE_PREFIX}_<server>_<date>{LoggingConfig.LOG_FILE_EXTENSION}")
    main_logger.info(f"Rotation: {LoggingConfig.ROTATION_WHEN} (keep {LoggingConfig.BACKUP_COUNT} days)")
    main_logger.info(f"Default Level: {logging.getLevelName(LoggingConfig.DEFAULT_LEVEL)}")
    main_logger.info(f"Console Output: {LoggingConfig.CONSOLE_OUTPUT}")
    main_logger.info(f"Performance Threshold: {LoggingConfig.SLOW_OPERATION_THRESHOLD}s")


async def main():
    """Run all logging demonstrations."""
    main_logger.info("🚀 Starting Centralized Logging System Demo")
    main_logger.info("=" * 80)
    
    # Display configuration
    display_logging_configuration()
    
    # Run all demos
    demo_basic_logging()
    demo_structured_logging()
    await demo_performance_logging()
    demo_error_handling()
    demo_different_log_levels()
    demo_batch_operations()
    demo_multilingual_logging()
    demo_system_monitoring()
    await demo_comprehensive_rag_workflow()
    
    main_logger.info("=" * 80)
    main_logger.info("🎉 Centralized Logging System Demo Completed!")
    main_logger.info("Check the logs directory for the generated log files")
    
    # Final statistics
    final_stats = get_logging_stats()
    main_logger.info(f"Demo generated logs using {final_stats['total_loggers']} loggers")


if __name__ == "__main__":
    # Run the comprehensive demo
    asyncio.run(main()) 