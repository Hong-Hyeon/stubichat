# 엑사원은 head_size가 80이라 vllm에서 지원하지 않음.
import os
os.environ["VLLM_USE_V1"] = "0"

from vllm import LLM, SamplingParams
from typing import List, Optional, Dict, AsyncGenerator
import json
import asyncio
import time

from app.logger import (
    get_logger,
    get_request_logger,
    get_model_performance_logger,
    log_exception,
    request_id_var
)

# Initialize logger for LLM service
logger = get_logger(__name__)


class LLMService:
    """
    LLM Service with comprehensive logging for model inference operations.
    
    This service handles both streaming and non-streaming text generation
    with detailed performance monitoring and error tracking.
    """
    
    def __init__(self, model: LLM):
        """
        Initialize the LLM service with a VLLM model.
        
        Args:
            model: The VLLM model instance
        """
        self.model = model
        logger.info("LLM Service initialized successfully")
        logger.info(f"Model: {model.llm_engine.model_config.model}")
        logger.info(f"Max model length: {model.llm_engine.model_config.max_model_len}")

    async def generate_stream(self, prompt: str, sampling_params: SamplingParams) -> AsyncGenerator[str, None]:
        """
        Generate text using streaming mode with comprehensive logging.
        
        Args:
            prompt: Input prompt for generation
            sampling_params: VLLM sampling parameters
            
        Yields:
            Streaming response chunks as JSON strings
        """
        request_id = request_id_var.get() or 'no-req'
        stream_logger = get_request_logger(request_id)
        
        # Log request details
        prompt_length = len(prompt)
        stream_logger.info(f"Starting streaming generation (prompt_length: {prompt_length})")
        stream_logger.debug(f"Prompt preview: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}")
        stream_logger.debug(f"Sampling params: max_tokens={sampling_params.max_tokens}, "
                            f"temperature={sampling_params.temperature}, "
                            f"top_p={sampling_params.top_p}")
        
        try:
            # Estimate prompt tokens (rough approximation)
            prompt_tokens = len(prompt.split())
            
            # Use performance logger for the generation
            with get_model_performance_logger(stream_logger, "streaming_generation", prompt_tokens) as perf_logger:
                stream_logger.debug("Calling VLLM generate method...")
                
                # Call VLLM generate method
                outputs = self.model.generate(prompts=[prompt], sampling_params=sampling_params)
                
                stream_logger.info("VLLM generation completed, starting streaming response")
                
                # Process outputs for streaming
                total_chunks = 0
                total_chars = 0
                
                for output in outputs[0].outputs:
                    text = output.text
                    if text and text.strip():  # Filter empty texts
                        stream_logger.debug(f"Processing output text (length: {len(text)})")
                        
                        try:
                            # Check if the output is already JSON
                            json.loads(text)
                            # If it's valid JSON, send as-is
                            response_json = json.dumps({'text': text})
                            stream_logger.debug("Sending JSON response chunk")
                            yield f"data: {response_json}\n\n"
                            total_chunks += 1
                            total_chars += len(text)
                            
                        except json.JSONDecodeError:
                            # If not JSON, split into sentence chunks for streaming
                            sentences = [s.strip() for s in text.split('.') if s.strip()]
                            stream_logger.debug(f"Split text into {len(sentences)} sentence chunks")
                            
                            for sentence in sentences:
                                if sentence:
                                    chunk_text = sentence + '.'
                                    response_json = json.dumps({'text': chunk_text})
                                    stream_logger.debug(f"Sending sentence chunk: {chunk_text[:50]}...")
                                    yield f"data: {response_json}\n\n"
                                    total_chunks += 1
                                    total_chars += len(chunk_text)
                                    
                                    # Small delay for realistic streaming
                                    await asyncio.sleep(0.05)
                
                # Set completion tokens for performance logging
                completion_tokens = len(text.split()) if 'text' in locals() else 0
                perf_logger.set_completion_tokens(completion_tokens)
                
                # Send completion signal
                yield "data: [DONE]\n\n"
                
                # Log final statistics
                stream_logger.info(f"Streaming completed: {total_chunks} chunks, "
                                    f"{total_chars} chars, {completion_tokens} completion_tokens")
                
        except Exception as e:
            log_exception(stream_logger, "Streaming generation failed", e)
            
            # Send error response
            error_response = json.dumps({
                'error': str(e),
                'request_id': request_id,
                'timestamp': time.time()
            })
            yield f"data: {error_response}\n\n"
            yield "data: [DONE]\n\n"

    def generate(self, prompt: str, sampling_params: SamplingParams) -> Dict:
        """
        Generate text in standard (non-streaming) mode with comprehensive logging.
        
        Args:
            prompt: Input prompt for generation
            sampling_params: VLLM sampling parameters
            
        Returns:
            Dictionary containing generated text and usage statistics
        """
        request_id = request_id_var.get() or 'no-req'
        gen_logger = get_request_logger(request_id)
        
        # Log request details
        prompt_length = len(prompt)
        gen_logger.info(f"Starting standard generation (prompt_length: {prompt_length})")
        gen_logger.debug(f"Prompt preview: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}")
        gen_logger.debug(f"Sampling params: max_tokens={sampling_params.max_tokens}, "
                         f"temperature={sampling_params.temperature}, "
                         f"top_p={sampling_params.top_p}")
        
        try:
            # Estimate prompt tokens (rough approximation)
            prompt_tokens = len(prompt.split())
            
            # Use performance logger for the generation
            with get_model_performance_logger(gen_logger, "standard_generation", prompt_tokens) as perf_logger:
                gen_logger.debug("Calling VLLM generate method...")
                
                # Call VLLM generate method
                outputs = self.model.generate(prompts=[prompt], sampling_params=sampling_params)
                
                # Extract generated text
                generated_text = outputs[0].outputs[0].text
                gen_logger.info(f"Generation completed (output_length: {len(generated_text)})")
                gen_logger.debug(f"Generated text preview: {generated_text[:100]}..." 
                                 if len(generated_text) > 100 else f"Generated text: {generated_text}")
                
                # Calculate usage statistics
                completion_tokens = len(generated_text.split())
                total_tokens = prompt_tokens + completion_tokens
                
                # Set completion tokens for performance logging
                perf_logger.set_completion_tokens(completion_tokens)
                
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
                
                # Log usage statistics
                gen_logger.info(f"Usage: {usage}")
                
                result = {
                    "text": generated_text,
                    "usage": usage
                }
                
                gen_logger.info("Standard generation completed successfully")
                return result
                
        except Exception as e:
            log_exception(gen_logger, "Standard generation failed", e)
            
            # Return error response
            return {
                "text": "",
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                "error": str(e),
                "request_id": request_id
            }
    
    def get_model_info(self) -> Dict:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary containing model information
        """
        info_logger = get_logger("model_info")
        
        try:
            info_logger.debug("Retrieving model information")
            
            model_config = self.model.llm_engine.model_config
            parallel_config = self.model.llm_engine.parallel_config
            cache_config = self.model.llm_engine.cache_config
            
            info = {
                "model_name": model_config.model,
                "max_model_length": model_config.max_model_len,
                "vocab_size": getattr(model_config, 'vocab_size', None),
                "tensor_parallel_size": parallel_config.tensor_parallel_size,
                "pipeline_parallel_size": parallel_config.pipeline_parallel_size,
                "block_size": cache_config.block_size,
                "gpu_memory_utilization": cache_config.gpu_memory_utilization,
                "status": "loaded",
                "timestamp": time.time()
            }
            
            info_logger.debug("Model information retrieved successfully")
            return info
            
        except Exception as e:
            log_exception(info_logger, "Failed to get model information", e)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def health_check(self) -> Dict:
        """
        Perform a health check on the LLM service.
        
        Returns:
            Dictionary containing health status
        """
        health_logger = get_logger("health_check")
        
        try:
            health_logger.debug("Performing LLM service health check")
            
            # Basic health checks
            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "service": "llm_service"
            }
            
            # Check if model is accessible
            if self.model and hasattr(self.model, 'llm_engine'):
                health_status["model_loaded"] = True
                health_status["model_name"] = self.model.llm_engine.model_config.model
                health_logger.debug("Model is accessible and loaded")
            else:
                health_status["model_loaded"] = False
                health_status["status"] = "unhealthy"
                health_logger.error("Model is not accessible")
            
            # Optional: Perform a quick generation test (commented out for performance)
            # try:
            #     test_result = self.generate("Hello", SamplingParams(max_tokens=1, temperature=0.0))
            #     if test_result and "text" in test_result:
            #         health_status["generation_test"] = "passed"
            #         health_logger.debug("Generation test passed")
            #     else:
            #         health_status["generation_test"] = "failed"
            #         health_logger.warning("Generation test failed")
            # except Exception as e:
            #     health_status["generation_test"] = "error"
            #     health_logger.warning(f"Generation test error: {e}")
            
            health_logger.debug(f"Health check completed: {health_status['status']}")
            return health_status
            
        except Exception as e:
            log_exception(health_logger, "Health check failed", e)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time(),
                "service": "llm_service"
            } 