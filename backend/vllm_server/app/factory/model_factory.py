from vllm import LLM
from app.config.base import settings
import huggingface_hub
import os
import time
from typing import Optional

from app.logger import (
    get_logger,
    get_model_performance_logger,
    log_exception
)

# Initialize logger for model factory
logger = get_logger(__name__)


class ModelFactory:
    """Factory class for creating and managing VLLM models with comprehensive logging."""
    
    @staticmethod
    def create_model() -> LLM:
        """
        Create and configure a VLLM model with detailed logging.
        
        Returns:
            Configured VLLM model instance
            
        Raises:
            Exception: If model creation fails
        """
        logger.info("=== Starting VLLM Model Creation ===")
        
        # Log configuration details
        ModelFactory._log_model_config()
        
        try:
            # Authenticate with Hugging Face if token is provided
            ModelFactory._setup_huggingface_auth()
            
            # Create model with performance logging
            with get_model_performance_logger(logger, "model_creation"):
                logger.info("Creating VLLM model instance...")
                
                model = LLM(
                    model=settings.MODEL_PATH,
                    tensor_parallel_size=settings.TENSOR_PARALLEL_SIZE,
                    gpu_memory_utilization=settings.GPU_MEMORY_UTILIZATION,
                    max_num_seqs=128,
                    trust_remote_code=True,
                    download_dir="/tmp/model_cache",
                    max_model_len=settings.MAX_MODEL_LENGTH
                )
                
                logger.info("VLLM model created successfully")
            
            # Log model details after creation
            ModelFactory._log_model_details(model)
            
            logger.info("=== VLLM Model Creation Completed Successfully ===")
            return model
            
        except Exception as e:
            log_exception(logger, "Failed to create VLLM model", e)
            raise
    
    @staticmethod
    def _log_model_config():
        """Log detailed model configuration information."""
        logger.info("=== Model Configuration ===")
        logger.info(f"Model Path: {settings.MODEL_PATH}")
        logger.info(f"Max Tokens: {settings.MAX_TOKENS}")
        logger.info(f"Temperature: {settings.TEMPERATURE}")
        logger.info(f"Top P: {settings.TOP_P}")
        logger.info(f"Tensor Parallel Size: {settings.TENSOR_PARALLEL_SIZE}")
        logger.info(f"GPU Memory Utilization: {settings.GPU_MEMORY_UTILIZATION}")
        logger.info(f"Max Model Length: {settings.MAX_MODEL_LENGTH}")
        logger.info("Download Directory: /tmp/model_cache")
        logger.info("Max Num Sequences: 128")
        logger.info("Trust Remote Code: True")
        
        # Log Hugging Face authentication status
        if settings.HUGGING_FACE_TOKEN:
            logger.info("Hugging Face authentication: Token provided")
        else:
            logger.warning("Hugging Face authentication: No token provided")
    
    @staticmethod
    def _setup_huggingface_auth():
        """Setup Hugging Face authentication with logging."""
        if settings.HUGGING_FACE_TOKEN:
            logger.info("Setting up Hugging Face authentication...")
            
            try:
                # Login to Hugging Face
                huggingface_hub.login(token=settings.HUGGING_FACE_TOKEN)
                
                # Set environment variable for VLLM
                os.environ["HUGGING_FACE_TOKEN"] = settings.HUGGING_FACE_TOKEN
                
                logger.info("Hugging Face authentication configured successfully")
                
            except Exception as e:
                log_exception(logger, "Failed to setup Hugging Face authentication", e)
                logger.warning("Continuing without Hugging Face authentication")
        else:
            logger.info("Skipping Hugging Face authentication (no token provided)")
    
    @staticmethod
    def _log_model_details(model: LLM):
        """
        Log detailed information about the created model.
        
        Args:
            model: The created VLLM model instance
        """
        logger.info("=== Model Details ===")
        
        try:
            # Log model engine configuration
            model_config = model.llm_engine.model_config
            logger.info(f"Model Name: {model_config.model}")
            logger.info(f"Model Revision: {getattr(model_config, 'revision', 'N/A')}")
            logger.info(f"Max Model Length: {model_config.max_model_len}")
            logger.info(f"Vocab Size: {getattr(model_config, 'vocab_size', 'N/A')}")
            
            # Log parallel configuration
            parallel_config = model.llm_engine.parallel_config
            logger.info(f"Tensor Parallel Size: {parallel_config.tensor_parallel_size}")
            logger.info(f"Pipeline Parallel Size: {parallel_config.pipeline_parallel_size}")
            
            # Log cache configuration
            cache_config = model.llm_engine.cache_config
            logger.info(f"Block Size: {cache_config.block_size}")
            logger.info(f"GPU Memory Utilization: {cache_config.gpu_memory_utilization}")
            
            # Log scheduler configuration if available
            try:
                scheduler_config = model.llm_engine.scheduler_config
                logger.info(f"Max Num Sequences: {scheduler_config.max_num_seqs}")
                logger.info(f"Max Num Batched Tokens: {scheduler_config.max_num_batched_tokens}")
            except AttributeError:
                logger.debug("Scheduler configuration not available")
            
        except Exception as e:
            logger.warning(f"Could not log detailed model information: {e}")
    
    @staticmethod
    def validate_model_health(model: LLM) -> bool:
        """
        Validate that the model is properly loaded and functional.
        
        Args:
            model: The VLLM model instance to validate
            
        Returns:
            True if model is healthy, False otherwise
        """
        logger.info("Validating model health...")
        
        try:
            # Simple health check - try to get model info
            if hasattr(model, 'llm_engine') and model.llm_engine:
                logger.info("Model engine is accessible")
                
                # Check if model config is available
                if hasattr(model.llm_engine, 'model_config'):
                    model_name = model.llm_engine.model_config.model
                    logger.info(f"Model configuration accessible: {model_name}")
                    
                    # Optional: Perform a simple generation test
                    # This is commented out as it might be expensive for large models
                    # test_result = model.generate(["Hello"], SamplingParams(max_tokens=1))
                    # if test_result:
                    #     logger.info("Model generation test passed")
                    
                    logger.info("Model health validation passed")
                    return True
                else:
                    logger.error("Model configuration not accessible")
                    return False
            else:
                logger.error("Model engine not accessible")
                return False
                
        except Exception as e:
            log_exception(logger, "Model health validation failed", e)
            return False
    
    @staticmethod
    def get_model_info(model: LLM) -> dict:
        """
        Get comprehensive model information for monitoring and debugging.
        
        Args:
            model: The VLLM model instance
            
        Returns:
            Dictionary containing model information
        """
        info_logger = get_logger("model_info")
        
        try:
            info = {
                "status": "loaded",
                "timestamp": time.time()
            }
            
            if hasattr(model, 'llm_engine') and model.llm_engine:
                model_config = model.llm_engine.model_config
                info.update({
                    "model_name": model_config.model,
                    "max_model_length": model_config.max_model_len,
                    "vocab_size": getattr(model_config, 'vocab_size', None)
                })
                
                parallel_config = model.llm_engine.parallel_config
                info.update({
                    "tensor_parallel_size": parallel_config.tensor_parallel_size,
                    "pipeline_parallel_size": parallel_config.pipeline_parallel_size
                })
                
                cache_config = model.llm_engine.cache_config
                info.update({
                    "block_size": cache_config.block_size,
                    "gpu_memory_utilization": cache_config.gpu_memory_utilization
                })
            
            info_logger.debug("Model information retrieved successfully")
            return info
            
        except Exception as e:
            log_exception(info_logger, "Failed to get model information", e)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            } 