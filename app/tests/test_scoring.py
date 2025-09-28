"""
Tests for Phase 4 scoring functionality.
"""

import pytest
import numpy as np
from unittest.mock import patch
from app.utils.scoring import rank_items, _zscore, _cluster_density


def _create_test_item(title, score=50, comments=10, sentiment=-0.3, cluster_id=0, created_utc=1700000000):
    """Create a test item with default values."""
    return {
        "title": title,
        "score": score,
        "num_comments": comments,
        "sentiment": sentiment,
        "cluster_id": cluster_id,
        "created_utc": created_utc,
        "signals": {
            "is_question": 1,
            "pain_markers": 1
        }
    }


def test_zscore_basic():
    """Test z-score calculation."""
    arr = [1, 2, 3, 4, 5]
    assert _zscore(3, arr) == 0.0  # Mean should have z-score of 0
    assert _zscore(5, arr) > 0  # Above mean should be positive
    assert _zscore(1, arr) < 0  # Below mean should be negative


def test_zscore_empty_array():
    """Test z-score with empty array."""
    assert _zscore(5, []) == 0.0


def test_zscore_single_value():
    """Test z-score with single value."""
    assert _zscore(5, [5]) == 0.0


def test_cluster_density():
    """Test cluster density calculation."""
    items = [
        _create_test_item("Item 1", cluster_id=1),
        _create_test_item("Item 2", cluster_id=1),
        _create_test_item("Item 3", cluster_id=2),
    ]
    
    # Cluster 1 has 2 items, density should be 2/20 = 0.1
    density_1 = _cluster_density(items, 1)
    assert density_1 == 0.1
    
    # Cluster 2 has 1 item, density should be 1/20 = 0.05
    density_2 = _cluster_density(items, 2)
    assert density_2 == 0.05
    
    # Cluster 3 doesn't exist, density should be 0
    density_3 = _cluster_density(items, 3)
    assert density_3 == 0.0


def test_rank_items_basic():
    """Test basic ranking functionality."""
    items = []
    for i in range(10):
        items.append(_create_test_item(f"Item {i}", score=10*i, comments=i))
    
    clustered = {
        "items": items,
        "clusters": [{"cluster_id": 0, "size": 10}]
    }
    
    ranked = rank_items(clustered, top=5)
    
    assert len(ranked) == 5
    assert all("problem_score" in item for item in ranked)
    assert all("why" in item for item in ranked)
    
    # Should be sorted by problem_score descending
    scores = [item["problem_score"] for item in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_items_empty():
    """Test ranking with empty input."""
    result = rank_items({"items": [], "clusters": []})
    assert result == []


def test_rank_items_single_item():
    """Test ranking with single item."""
    item = _create_test_item("Single item", score=100, comments=50)
    clustered = {
        "items": [item],
        "clusters": [{"cluster_id": 0, "size": 1}]
    }
    
    ranked = rank_items(clustered, top=10)
    assert len(ranked) == 1
    assert ranked[0]["problem_score"] is not None
    assert "why" in ranked[0]


def test_rank_items_problem_score_components():
    """Test that problem score includes all expected components."""
    item = _create_test_item(
        "Test item",
        score=100,
        comments=50,
        sentiment=-0.5,
        cluster_id=1
    )
    
    # Create multiple items for cluster density calculation
    items = [item] + [_create_test_item(f"Other {i}", cluster_id=1) for i in range(5)]
    
    clustered = {
        "items": items,
        "clusters": [{"cluster_id": 1, "size": 6}]
    }
    
    ranked = rank_items(clustered, top=1)
    assert len(ranked) == 1
    
    why = ranked[0]["why"]
    assert "engagement_z" in why
    assert "neg_sentiment" in why
    assert "is_question" in why
    assert "pain_markers" in why
    assert "cluster_density" in why
    assert "time_decay" in why
    assert "weights" in why


def test_rank_items_negative_sentiment():
    """Test that negative sentiment is properly handled."""
    positive_item = _create_test_item("Positive", sentiment=0.5)
    negative_item = _create_test_item("Negative", sentiment=-0.5)
    
    clustered = {
        "items": [positive_item, negative_item],
        "clusters": [{"cluster_id": 0, "size": 2}]
    }
    
    ranked = rank_items(clustered, top=2)
    
    # Find the negative sentiment item
    neg_item = next(item for item in ranked if item["sentiment"] == -0.5)
    assert neg_item["why"]["neg_sentiment"] == 0.5  # max(0, -(-0.5))
    
    # Find the positive sentiment item
    pos_item = next(item for item in ranked if item["sentiment"] == 0.5)
    assert pos_item["why"]["neg_sentiment"] == 0.0  # max(0, -0.5)


def test_rank_items_deterministic():
    """Test that ranking is deterministic for same input."""
    items = [_create_test_item(f"Item {i}", score=i*10) for i in range(5)]
    clustered = {
        "items": items,
        "clusters": [{"cluster_id": 0, "size": 5}]
    }
    
    ranked1 = rank_items(clustered, top=5)
    ranked2 = rank_items(clustered, top=5)
    
    # Should get same results
    assert len(ranked1) == len(ranked2)
    for i in range(len(ranked1)):
        assert ranked1[i]["problem_score"] == ranked2[i]["problem_score"]


@patch('app.utils.scoring.settings')
def test_rank_items_weights(mock_settings):
    """Test that different weights affect scoring."""
    # Set custom weights
    mock_settings.w_e = 1.0
    mock_settings.w_n = 0.0
    mock_settings.w_q = 0.0
    mock_settings.w_p = 0.0
    mock_settings.w_d = 0.0
    mock_settings.w_t = 0.0
    mock_settings.density_norm = 20.0
    
    # Create items with different engagement
    high_engagement = _create_test_item("High", score=100, comments=50)
    low_engagement = _create_test_item("Low", score=10, comments=5)
    
    clustered = {
        "items": [high_engagement, low_engagement],
        "clusters": [{"cluster_id": 0, "size": 2}]
    }
    
    ranked = rank_items(clustered, top=2)
    
    # High engagement should rank higher
    assert ranked[0]["score"] + ranked[0]["num_comments"] > ranked[1]["score"] + ranked[1]["num_comments"]


def test_rank_items_top_limit():
    """Test that top parameter limits results."""
    items = [_create_test_item(f"Item {i}") for i in range(20)]
    clustered = {
        "items": items,
        "clusters": [{"cluster_id": 0, "size": 20}]
    }
    
    ranked = rank_items(clustered, top=5)
    assert len(ranked) == 5
    
    ranked = rank_items(clustered, top=100)
    assert len(ranked) == 20  # Should not exceed available items
