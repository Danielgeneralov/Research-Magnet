"""
Text embeddings using sentence-transformers for enrichment pipeline.
"""

from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from app.utils.logging import log_processing_step, log_model_loading, log_batch_processing, get_enrichment_logger
import hashlib

logger = get_enrichment_logger("embeddings")

# Global model instance for lazy loading
_model: Optional[SentenceTransformer] = None

# Simple in-memory cache for embeddings
_embedding_cache: Dict[str, List[float]] = {}


def _get_model() -> SentenceTransformer:
    """Get or create sentence transformer model (singleton)."""
    global _model
    if _model is None:
        try:
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            log_model_loading("sentence-transformers all-MiniLM-L6-v2", True)
        except Exception as e:
            log_model_loading("sentence-transformers all-MiniLM-L6-v2", False)
            raise RuntimeError(f"Failed to load sentence transformer model: {e}")
    return _model


@log_processing_step("embeddings")
def add_embeddings(items: List[Dict[str, Any]], batch_size: int = 64) -> List[Dict[str, Any]]:
    """
    Add text embeddings to items using sentence transformers.
    
    Args:
        items: List of items with 'title' and 'body' fields
        batch_size: Batch size for embedding generation
    
    Returns:
        Items with added 'embedding' field (list of floats)
    """
    if not items:
        return items
    
    model = _get_model()
    
    # Prepare texts for embedding with caching
    texts_to_process = []
    cache_hits = 0
    cache_misses = 0
    
    for i, item in enumerate(items):
        title = item.get('title', '')
        body = item.get('body', '')
        combined_text = f"{title} {body}".strip()
        
        if combined_text:
            # Create cache key from text hash
            text_hash = hashlib.md5(combined_text.encode()).hexdigest()
            
            if text_hash in _embedding_cache:
                # Use cached embedding
                item['embedding'] = _embedding_cache[text_hash]
                cache_hits += 1
            else:
                texts_to_process.append((i, combined_text, text_hash))
                cache_misses += 1
        else:
            # Empty text - create zero embedding
            embedding_dim = model.get_sentence_embedding_dimension()
            item['embedding'] = [0.0] * embedding_dim
    
    if cache_hits > 0:
        logger.info(f"Embedding cache hits: {cache_hits}, misses: {cache_misses}")
    
    # Process only texts that weren't cached
    if texts_to_process:
        texts = [text for _, text, _ in texts_to_process]
        total_items = len(texts)
    else:
        total_items = 0
    log_batch_processing("embeddings", batch_size, total_items)
    
    all_embeddings = []
    
    for i in range(0, total_items, batch_size):
        batch_texts = texts[i:i + batch_size]
        
        try:
            # Generate embeddings for batch
            batch_embeddings = model.encode(batch_texts, convert_to_tensor=False)
            all_embeddings.extend(batch_embeddings.tolist())
        except Exception as e:
            # If batch fails, try individual items
            logger.warning(f"Batch embedding failed, processing individually: {e}")
            
            for text in batch_texts:
                try:
                    if text.strip():
                        embedding = model.encode([text], convert_to_tensor=False)
                        all_embeddings.append(embedding[0].tolist())
                    else:
                        # Create zero embedding for empty text
                        embedding_dim = model.get_sentence_embedding_dimension()
                        all_embeddings.append([0.0] * embedding_dim)
                except Exception as item_error:
                    logger.warning(f"Failed to embed individual text: {item_error}")
                    # Create zero embedding as fallback
                    embedding_dim = model.get_sentence_embedding_dimension()
                    all_embeddings.append([0.0] * embedding_dim)
    
    # Add embeddings to items and cache them
    if texts_to_process:
        for i, (original_index, text, text_hash) in enumerate(texts_to_process):
            embedding = all_embeddings[i]
            items[original_index]['embedding'] = embedding
            # Cache the embedding
            _embedding_cache[text_hash] = embedding
    
    return items
