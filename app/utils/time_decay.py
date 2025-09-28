"""
Time decay utilities for freshness scoring.
"""

import math
import time
from typing import List, Dict, Any, Optional
from app.utils.logging import log_processing_step


def time_decay_weight(created_utc: Optional[float], half_life_hours: int = 72) -> float:
    """
    Calculate time decay weight based on creation time.
    
    Args:
        created_utc: Unix timestamp of creation, or None if unknown
        half_life_hours: Half-life in hours (default 72h)
    
    Returns:
        Weight between 0 and 1, where 1 is most recent and 0 is very old
    """
    if created_utc is None:
        return 0.5  # Default weight for unknown timestamps
    
    current_time = time.time()
    age_hours = (current_time - created_utc) / 3600  # Convert to hours
    
    # Calculate decay using exponential decay formula
    # weight = 2^(-age / half_life)
    weight = math.pow(2, -age_hours / half_life_hours)
    
    # Clamp to [0, 1] range
    return max(0.0, min(1.0, weight))


@log_processing_step("time_decay")
def add_time_decay(items: List[Dict[str, Any]], half_life_hours: int = 72) -> List[Dict[str, Any]]:
    """
    Add time decay weights to items.
    
    Args:
        items: List of items with 'created_utc' field
        half_life_hours: Half-life in hours for decay calculation
    
    Returns:
        Items with added 'time_decay_weight' field
    """
    if not items:
        return items
    
    for item in items:
        created_utc = item.get('created_utc')
        item['time_decay_weight'] = time_decay_weight(created_utc, half_life_hours)
    
    return items
