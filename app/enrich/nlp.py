"""
Named Entity Recognition using spaCy for enrichment pipeline.
"""

import spacy
from typing import List, Dict, Any, Optional
from app.utils.logging import log_processing_step, log_model_loading

# Global spaCy model instance for lazy loading
_nlp: Optional[spacy.Language] = None

# Simplified entity labels mapping
ENTITY_LABEL_MAP = {
    'PERSON': 'PERSON',
    'NORP': 'ORG',  # Nationalities, religious or political groups
    'FAC': 'LOC',   # Buildings, airports, highways, bridges, etc.
    'ORG': 'ORG',   # Companies, agencies, institutions, etc.
    'GPE': 'LOC',   # Countries, cities, states
    'LOC': 'LOC',   # Non-GPE locations, mountain ranges, bodies of water
    'PRODUCT': 'PRODUCT',
    'EVENT': 'EVENT',
    'WORK_OF_ART': 'PRODUCT',
    'LAW': 'LAW',
    'LANGUAGE': 'LANGUAGE',
    'DATE': 'TIME',
    'TIME': 'TIME',
    'PERCENT': 'MONEY',
    'MONEY': 'MONEY',
    'QUANTITY': 'MONEY',
    'ORDINAL': 'TIME',
    'CARDINAL': 'TIME'
}


def _get_nlp() -> spacy.Language:
    """Get or create spaCy model (singleton)."""
    global _nlp
    if _nlp is None:
        try:
            # Load model with only NER for speed
            _nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
            log_model_loading("spaCy en_core_web_sm", True)
        except OSError:
            # Fallback: try to load without disabling components
            try:
                _nlp = spacy.load("en_core_web_sm")
                log_model_loading("spaCy en_core_web_sm (fallback)", True)
            except OSError as e:
                log_model_loading("spaCy en_core_web_sm", False)
                raise RuntimeError(f"spaCy model 'en_core_web_sm' not found. Please install it with: python -m spacy download en_core_web_sm. Error: {e}")
        except Exception as e:
            log_model_loading("spaCy en_core_web_sm", False)
            raise RuntimeError(f"Failed to load spaCy model: {e}")
    return _nlp


def extract_entities(text: str) -> List[Dict[str, str]]:
    """
    Extract named entities from text using spaCy.
    
    Args:
        text: Text to extract entities from
    
    Returns:
        List of entities with 'text' and 'label' fields
    """
    if not text or not text.strip():
        return []
    
    nlp = _get_nlp()
    
    # Truncate to 3000 characters to prevent memory issues
    if len(text) > 3000:
        text = text[:3000]
    
    try:
        doc = nlp(text)
        entities = []
        
        for ent in doc.ents:
            # Map to simplified labels
            label = ENTITY_LABEL_MAP.get(ent.label_, ent.label_)
            
            # Only include entities with meaningful labels
            if label in ['PERSON', 'ORG', 'LOC', 'PRODUCT', 'TIME', 'MONEY', 'EVENT']:
                entities.append({
                    'text': ent.text.strip(),
                    'label': label
                })
        
        return entities
    
    except Exception as e:
        # Log error but don't fail the entire process
        from app.utils.logging import get_enrichment_logger
        logger = get_enrichment_logger("nlp")
        logger.warning(f"Failed to extract entities from text: {e}")
        return []


@log_processing_step("entities")
def add_entities(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add extracted entities to items.
    
    Args:
        items: List of items with 'title' and 'body' fields
    
    Returns:
        Items with added 'entities' field
    """
    if not items:
        return items
    
    for item in items:
        # Combine title and body for entity extraction
        title = item.get('title', '')
        body = item.get('body', '')
        combined_text = f"{title} {body}".strip()
        
        if combined_text:
            entities = extract_entities(combined_text)
            item['entities'] = entities
        else:
            item['entities'] = []
    
    return items
