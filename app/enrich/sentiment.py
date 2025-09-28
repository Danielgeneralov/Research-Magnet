"""
Sentiment analysis using VADER for enrichment pipeline.
"""

from typing import List, Dict, Any, Optional
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.utils.logging import log_processing_step, log_model_loading

# Global analyzer instance for lazy loading
_analyzer: Optional[SentimentIntensityAnalyzer] = None


def _get_analyzer() -> SentimentIntensityAnalyzer:
    """Get or create VADER sentiment analyzer (singleton)."""
    global _analyzer
    if _analyzer is None:
        try:
            _analyzer = SentimentIntensityAnalyzer()
            log_model_loading("VADER Sentiment Analyzer", True)
        except Exception as e:
            log_model_loading("VADER Sentiment Analyzer", False)
            raise RuntimeError(f"Failed to load VADER sentiment analyzer: {e}")
    return _analyzer


@log_processing_step("sentiment")
def add_sentiment(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add sentiment scores to items using VADER.
    
    Args:
        items: List of items with 'title' and 'body' fields
    
    Returns:
        Items with added 'sentiment' field (float between -1 and 1)
    """
    if not items:
        return items
    
    analyzer = _get_analyzer()
    
    for item in items:
        # Combine title and body for sentiment analysis
        title = item.get('title', '')
        body = item.get('body', '')
        combined_text = f"{title} {body}".strip()
        
        # Truncate to 4000 characters to prevent memory issues
        if len(combined_text) > 4000:
            combined_text = combined_text[:4000]
        
        if combined_text:
            # Get sentiment scores
            scores = analyzer.polarity_scores(combined_text)
            # Use compound score (-1 to 1)
            item['sentiment'] = scores['compound']
        else:
            item['sentiment'] = 0.0
    
    return items
