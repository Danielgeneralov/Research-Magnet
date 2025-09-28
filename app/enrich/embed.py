"""
Text embeddings using sentence-transformers for enrichment pipeline.
"""

from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from app.utils.logging import log_processing_step, log_model_loading, log_batch_processing

# Global model instance for lazy loading
_model: Optional[SentenceTransformer] = None


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
    
    # Prepare texts for embedding
    texts = []
    for item in items:
        title = item.get('title', '')
        body = item.get('body', '')
        combined_text = f"{title} {body}".strip()
        
        if combined_text:
            texts.append(combined_text)
        else:
            texts.append("")  # Empty text for items without content
    
    # Process in batches
    total_items = len(texts)
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
            from app.utils.logging import get_enrichment_logger
            logger = get_enrichment_logger("embeddings")
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
    
    # Add embeddings to items
    for i, item in enumerate(items):
        if i < len(all_embeddings):
            item['embedding'] = all_embeddings[i]
        else:
            # Fallback: create zero embedding
            embedding_dim = model.get_sentence_embedding_dimension()
            item['embedding'] = [0.0] * embedding_dim
    
    return items
