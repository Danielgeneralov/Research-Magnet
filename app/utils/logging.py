"""
Logging utilities for enrichment pipeline.
"""

import logging
import time
from typing import Any, Dict, List
from functools import wraps


def get_enrichment_logger(name: str) -> logging.Logger:
    """Get a logger configured for enrichment operations."""
    logger = logging.getLogger(f"enrichment.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_processing_step(step_name: str):
    """Decorator to log processing step timing and item counts."""
    def decorator(func):
        @wraps(func)
        def wrapper(items: List[Dict[str, Any]], *args, **kwargs) -> List[Dict[str, Any]]:
            logger = get_enrichment_logger(step_name)
            start_time = time.time()
            item_count = len(items) if items else 0
            
            logger.info(f"Starting {step_name} for {item_count} items")
            
            try:
                result = func(items, *args, **kwargs)
                processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                result_count = len(result) if result else 0
                
                logger.info(
                    f"Completed {step_name}: {result_count} items processed in {processing_time:.2f}ms"
                )
                return result
            except Exception as e:
                processing_time = (time.time() - start_time) * 1000
                logger.error(f"Failed {step_name} after {processing_time:.2f}ms: {str(e)}")
                raise
        return wrapper
    return decorator


def log_batch_processing(step_name: str, batch_size: int, total_items: int):
    """Log batch processing progress."""
    logger = get_enrichment_logger(step_name)
    batches = (total_items + batch_size - 1) // batch_size
    logger.info(f"Processing {total_items} items in {batches} batches of {batch_size}")


def log_model_loading(model_name: str, success: bool, load_time: float = None):
    """Log model loading status."""
    logger = get_enrichment_logger("model_loading")
    if success:
        time_str = f" in {load_time:.2f}s" if load_time else ""
        logger.info(f"Successfully loaded {model_name}{time_str}")
    else:
        logger.error(f"Failed to load {model_name}")


def log_error_with_context(step_name: str, error: Exception, context: Dict[str, Any] = None):
    """Log error with additional context."""
    logger = get_enrichment_logger(step_name)
    context_str = f" Context: {context}" if context else ""
    logger.error(f"Error in {step_name}: {str(error)}{context_str}", exc_info=True)
