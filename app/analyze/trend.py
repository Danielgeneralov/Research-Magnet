"""
Trend detection for Research Magnet Phase 4.
Detects trending clusters using time-bucketed frequency curves and moving averages.
"""

import time
from collections import defaultdict, deque
from typing import List, Dict, Any, Optional, Tuple
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def _bucket_timestamp(ts: float, bucket_hours: int) -> int:
    """Convert timestamp to bucket ID."""
    return int(ts // (bucket_hours * 3600))


def _simple_moving_average(series: List[Tuple[int, int]], window_hours: int, bucket_hours: int) -> float:
    """
    Calculate simple moving average for a time series.
    
    Args:
        series: List of (bucket_id, count) tuples sorted by bucket_id
        window_hours: Window size in hours
        bucket_hours: Bucket size in hours
    
    Returns:
        Moving average value
    """
    if not series:
        return 0.0
    
    # Calculate how many buckets to include in the window
    window_size = max(1, window_hours // bucket_hours)
    
    # Take the last window_size buckets
    recent_buckets = series[-window_size:]
    
    if not recent_buckets:
        return 0.0
    
    total_count = sum(count for _, count in recent_buckets)
    return float(total_count) / len(recent_buckets)


def cluster_trends(
    items: List[Dict[str, Any]], 
    clusters: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Detect trending clusters using time-bucketed frequency analysis.
    
    Args:
        items: List of items with cluster_id and created_utc
        clusters: Optional cluster metadata for additional info
    
    Returns:
        List of cluster trend summaries
    """
    if not items:
        return []
    
    logger.info(f"Analyzing trends for {len(items)} items")
    
    # Build time series per cluster_id
    by_cluster_id: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
    current_time = time.time()
    
    for item in items:
        cluster_id = int(item.get("cluster_id", -1))
        if cluster_id < 0:  # Skip unclustered items
            continue
            
        created_utc = float(item.get("created_utc", current_time))
        bucket_id = _bucket_timestamp(created_utc, settings.trend_bucket_hours)
        by_cluster_id[cluster_id][bucket_id] += 1
    
    # Process each cluster
    trend_summaries = []
    
    for cluster_id, bucket_counts in by_cluster_id.items():
        # Convert to sorted series
        series = sorted(bucket_counts.items(), key=lambda x: x[0])  # (bucket_id, count)
        
        if not series:
            continue
        
        # Calculate moving averages
        sma_short = _simple_moving_average(
            series, 
            settings.trend_window_short_h, 
            settings.trend_bucket_hours
        )
        sma_long = _simple_moving_average(
            series, 
            settings.trend_window_long_h, 
            settings.trend_bucket_hours
        )
        
        # Get last bucket count
        last_count = series[-1][1] if series else 0
        
        # Determine trend
        trend = "flat"
        if last_count >= settings.min_support:
            if sma_long <= 0 and sma_short > 0:
                trend = "rising"
            else:
                up_threshold = (1.0 + settings.trend_delta) * sma_long
                down_threshold = (1.0 - settings.trend_delta) * sma_long
                
                if sma_short > up_threshold:
                    trend = "rising"
                elif sma_short < down_threshold:
                    trend = "falling"
                else:
                    trend = "flat"
        
        # Create trend summary
        summary = {
            "cluster_id": cluster_id,
            "trend": trend,
            "last_count": int(last_count),
            "sma_short": round(sma_short, 3),
            "sma_long": round(sma_long, 3),
            "series_tail": series[-10:],  # Show last 10 buckets
        }
        
        # Add cluster metadata if available
        if clusters:
            cluster_meta = next(
                (c for c in clusters if c.get("cluster_id") == cluster_id), 
                None
            )
            if cluster_meta:
                summary.update({
                    "top_keywords": cluster_meta.get("top_keywords", []),
                    "representatives": cluster_meta.get("representatives", []),
                    "size": cluster_meta.get("size", 0)
                })
        
        trend_summaries.append(summary)
    
    # Sort by trend priority (rising first) and then by last_count
    trend_summaries.sort(
        key=lambda x: (x["trend"] == "rising", x.get("last_count", 0)), 
        reverse=True
    )
    
    logger.info(f"Analyzed trends for {len(trend_summaries)} clusters")
    return trend_summaries
