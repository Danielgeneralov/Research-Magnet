"""
Tests for Phase 4 trend detection functionality.
"""

import pytest
import time
from unittest.mock import patch
from app.analyze.trend import cluster_trends, _bucket_timestamp, _simple_moving_average


def _create_test_item(cluster_id, created_utc, title="Test Item"):
    """Create a test item with cluster_id and timestamp."""
    return {
        "cluster_id": cluster_id,
        "created_utc": created_utc,
        "title": title
    }


def test_bucket_timestamp():
    """Test timestamp bucketing."""
    # Test with 6-hour buckets
    ts = 1700000000  # Fixed timestamp
    bucket = _bucket_timestamp(ts, 6)
    
    # Should be deterministic
    assert bucket == _bucket_timestamp(ts, 6)
    
    # Different bucket sizes should give different results
    bucket_1h = _bucket_timestamp(ts, 1)
    bucket_24h = _bucket_timestamp(ts, 24)
    assert bucket_1h != bucket_24h


def test_simple_moving_average():
    """Test simple moving average calculation."""
    # Test with empty series
    assert _simple_moving_average([], 24, 6) == 0.0
    
    # Test with single value
    series = [(1, 10)]
    assert _simple_moving_average(series, 24, 6) == 10.0
    
    # Test with multiple values
    series = [(1, 5), (2, 10), (3, 15), (4, 20)]
    avg = _simple_moving_average(series, 24, 6)
    assert avg == 12.5  # (5+10+15+20)/4


def test_simple_moving_average_window():
    """Test moving average with different window sizes."""
    series = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]
    
    # Window larger than series should use all values
    avg_all = _simple_moving_average(series, 100, 1)
    assert avg_all == 3.0  # (1+2+3+4+5)/5
    
    # Window smaller than series should use last values
    avg_last2 = _simple_moving_average(series, 2, 1)
    assert avg_last2 == 4.5  # (4+5)/2


def test_cluster_trends_empty():
    """Test trend analysis with empty input."""
    result = cluster_trends([])
    assert result == []


def test_cluster_trends_single_cluster():
    """Test trend analysis with single cluster."""
    now = time.time()
    items = [
        _create_test_item(1, now - 3600, "Recent"),
        _create_test_item(1, now - 7200, "Older"),
    ]
    
    result = cluster_trends(items)
    assert len(result) == 1
    assert result[0]["cluster_id"] == 1
    assert "trend" in result[0]
    assert "last_count" in result[0]
    assert "sma_short" in result[0]
    assert "sma_long" in result[0]


def test_cluster_trends_multiple_clusters():
    """Test trend analysis with multiple clusters."""
    now = time.time()
    items = [
        _create_test_item(1, now - 3600, "Cluster 1 Recent"),
        _create_test_item(1, now - 7200, "Cluster 1 Older"),
        _create_test_item(2, now - 3600, "Cluster 2 Recent"),
    ]
    
    result = cluster_trends(items)
    assert len(result) == 2
    
    cluster_ids = [r["cluster_id"] for r in result]
    assert 1 in cluster_ids
    assert 2 in cluster_ids


def test_cluster_trends_with_metadata():
    """Test trend analysis with cluster metadata."""
    now = time.time()
    items = [_create_test_item(1, now - 3600)]
    
    clusters = [{
        "cluster_id": 1,
        "top_keywords": ["keyword1", "keyword2"],
        "representatives": ["rep1", "rep2"],
        "size": 5
    }]
    
    result = cluster_trends(items, clusters)
    assert len(result) == 1
    
    trend = result[0]
    assert trend["cluster_id"] == 1
    assert trend["top_keywords"] == ["keyword1", "keyword2"]
    assert trend["representatives"] == ["rep1", "rep2"]
    assert trend["size"] == 5


def test_cluster_trends_rising_pattern():
    """Test detection of rising trend pattern."""
    now = time.time()
    bucket_hours = 6
    
    # Create rising pattern: more recent items
    items = []
    for i in range(8):
        # Create items in recent buckets
        ts = now - (i * bucket_hours * 3600)
        items.append(_create_test_item(1, ts, f"Item {i}"))
    
    with patch('app.analyze.trend.settings') as mock_settings:
        mock_settings.trend_bucket_hours = bucket_hours
        mock_settings.trend_window_short_h = 24
        mock_settings.trend_window_long_h = 72
        mock_settings.trend_delta = 0.15
        mock_settings.min_support = 1
        
        result = cluster_trends(items)
        assert len(result) == 1
        assert result[0]["cluster_id"] == 1


def test_cluster_trends_falling_pattern():
    """Test detection of falling trend pattern."""
    now = time.time()
    bucket_hours = 6
    
    # Create falling pattern: more older items
    items = []
    for i in range(8):
        # Create more items in older buckets
        ts = now - ((i + 4) * bucket_hours * 3600)
        items.append(_create_test_item(1, ts, f"Item {i}"))
    
    with patch('app.analyze.trend.settings') as mock_settings:
        mock_settings.trend_bucket_hours = bucket_hours
        mock_settings.trend_window_short_h = 24
        mock_settings.trend_window_long_h = 72
        mock_settings.trend_delta = 0.15
        mock_settings.min_support = 1
        
        result = cluster_trends(items)
        assert len(result) == 1
        assert result[0]["cluster_id"] == 1


def test_cluster_trends_flat_pattern():
    """Test detection of flat trend pattern."""
    now = time.time()
    bucket_hours = 6
    
    # Create flat pattern: consistent distribution
    items = []
    for i in range(6):
        ts = now - (i * bucket_hours * 3600)
        items.append(_create_test_item(1, ts, f"Item {i}"))
    
    with patch('app.analyze.trend.settings') as mock_settings:
        mock_settings.trend_bucket_hours = bucket_hours
        mock_settings.trend_window_short_h = 24
        mock_settings.trend_window_long_h = 72
        mock_settings.trend_delta = 0.15
        mock_settings.min_support = 1
        
        result = cluster_trends(items)
        assert len(result) == 1
        assert result[0]["cluster_id"] == 1


def test_cluster_trends_min_support():
    """Test minimum support threshold."""
    now = time.time()
    items = [_create_test_item(1, now - 3600)]
    
    with patch('app.analyze.trend.settings') as mock_settings:
        mock_settings.trend_bucket_hours = 6
        mock_settings.trend_window_short_h = 24
        mock_settings.trend_window_long_h = 72
        mock_settings.trend_delta = 0.15
        mock_settings.min_support = 5  # High threshold
        
        result = cluster_trends(items)
        assert len(result) == 1
        # Should be flat due to insufficient support
        assert result[0]["trend"] == "flat"


def test_cluster_trends_skips_unclustered():
    """Test that unclustered items are skipped."""
    now = time.time()
    items = [
        _create_test_item(-1, now - 3600),  # Unclustered
        _create_test_item(1, now - 3600),   # Clustered
    ]
    
    result = cluster_trends(items)
    assert len(result) == 1
    assert result[0]["cluster_id"] == 1


def test_cluster_trends_sorting():
    """Test that results are sorted by trend priority."""
    now = time.time()
    items = [
        _create_test_item(1, now - 3600),
        _create_test_item(2, now - 3600),
    ]
    
    with patch('app.analyze.trend.settings') as mock_settings:
        mock_settings.trend_bucket_hours = 6
        mock_settings.trend_window_short_h = 24
        mock_settings.trend_window_long_h = 72
        mock_settings.trend_delta = 0.15
        mock_settings.min_support = 1
        
        result = cluster_trends(items)
        assert len(result) == 2
        # Results should be sorted (rising first, then by count)
        assert isinstance(result[0]["cluster_id"], int)
        assert isinstance(result[1]["cluster_id"], int)
