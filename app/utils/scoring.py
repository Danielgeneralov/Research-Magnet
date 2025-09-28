"""
Problem scoring utilities for Research Magnet Phase 4.
Computes interpretable Problem Score per item with breakdown.
"""

import time
from typing import List, Dict, Any, Optional
from statistics import mean, pstdev
import logging

from app.config import settings
from app.utils.time_decay import time_decay_weight

logger = logging.getLogger(__name__)


def _zscore(val: float, arr: List[float]) -> float:
    """Calculate z-score for a value against an array."""
    if not arr:
        return 0.0
    m = mean(arr)
    sd = pstdev(arr) or 1.0
    return (val - m) / sd


def _cluster_density(items: List[Dict[str, Any]], cluster_id: int) -> float:
    """Calculate cluster density for a given cluster ID."""
    size = sum(1 for item in items if int(item.get("cluster_id", -1)) == int(cluster_id))
    return min(1.0, float(size) / settings.density_norm)


def rank_items(clustered: Dict[str, Any], top: int = 50) -> List[Dict[str, Any]]:
    """
    Rank items by Problem Score with interpretable breakdown.
    
    Args:
        clustered: Dictionary with 'items' and 'clusters' keys
        top: Maximum number of items to return
    
    Returns:
        List of ranked items with problem_score and why breakdown
    """
    items: List[Dict[str, Any]] = clustered.get("items", [])
    if not items:
        return []

    logger.info(f"Ranking {len(items)} items with top={top}")

    # Calculate engagement scores (score + num_comments)
    engagements = []
    for item in items:
        score = int(item.get("score", 0))
        comments = int(item.get("num_comments", 0))
        engagements.append(score + comments)
    
    # Calculate z-scores for engagement
    engagement_zscores = [_zscore(e, engagements) for e in engagements]

    ranked_items = []
    
    for item, engagement_z in zip(items, engagement_zscores):
        # Extract values with defaults
        sentiment = float(item.get("sentiment", 0.0))
        signals = item.get("signals", {}) if isinstance(item.get("signals", {}), dict) else {}
        cluster_id = int(item.get("cluster_id", 0))
        created_utc = item.get("created_utc")
        
        # Calculate components
        neg_sentiment = max(0.0, -sentiment)
        is_question = int(signals.get("is_question", 0) or 0)
        pain_markers = int(signals.get("pain_markers", 0) or 0)
        density = _cluster_density(items, cluster_id)
        time_decay = time_decay_weight(created_utc, settings.half_life_hours)
        
        # Calculate Problem Score
        problem_score = (
            settings.w_e * engagement_z +
            settings.w_n * neg_sentiment +
            settings.w_q * is_question +
            settings.w_p * pain_markers +
            settings.w_d * density +
            settings.w_t * time_decay
        )
        
        # Add scoring information to item
        item["problem_score"] = round(problem_score, 6)
        item["why"] = {
            "engagement_z": round(engagement_z, 3),
            "neg_sentiment": round(neg_sentiment, 3),
            "is_question": is_question,
            "pain_markers": pain_markers,
            "cluster_density": round(density, 3),
            "time_decay": round(time_decay, 3),
            "weights": {
                "W_E": settings.w_e,
                "W_N": settings.w_n,
                "W_Q": settings.w_q,
                "W_P": settings.w_p,
                "W_D": settings.w_d,
                "W_T": settings.w_t
            }
        }
        
        ranked_items.append(item)

    # Sort by problem score (descending)
    ranked_items.sort(key=lambda x: x.get("problem_score", 0.0), reverse=True)
    
    logger.info(f"Ranked {len(ranked_items)} items, returning top {min(top, len(ranked_items))}")
    return ranked_items[:top]
