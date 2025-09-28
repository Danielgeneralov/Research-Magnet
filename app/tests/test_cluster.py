"""
Unit tests for clustering functionality.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from typing import List

from app.analyze.cluster import cluster_items, _extract_top_keywords, _select_representatives
from app.schemas import EnrichedItem, Entity, Signals


class TestClustering:
    """Test clustering functionality."""
    
    def create_test_items(self, num_items: int = 10) -> List[EnrichedItem]:
        """Create test items with embeddings."""
        items = []
        for i in range(num_items):
            # Create embeddings that group into 2 clusters
            if i < num_items // 2:
                # First cluster: health/fitness related
                embedding = [0.1, 0.2, 0.3, 0.4] + [0.0] * 380  # 384-dim embedding
                title = f"Health question {i}: How to lose weight?"
                body = f"Body about fitness and health {i}"
            else:
                # Second cluster: tech/programming related
                embedding = [0.8, 0.9, 0.7, 0.6] + [0.0] * 380  # 384-dim embedding
                title = f"Tech question {i}: How to debug Python code?"
                body = f"Body about programming and technology {i}"
            
            item = EnrichedItem(
                source="test",
                title=title,
                body=body,
                url=f"https://example.com/{i}",
                created_utc=1600000000.0 + i,
                score=100 + i,
                num_comments=10 + i,
                sentiment=0.1 if i % 2 == 0 else -0.1,
                entities=[
                    Entity(text="test", label="PERSON") if i % 3 == 0 else Entity(text="tech", label="ORG")
                ],
                embedding=embedding,
                signals=Signals(
                    is_question=1,
                    pain_markers=1 if i % 2 == 0 else 0,
                    how_to_markers=1,
                    has_numbers=1 if i % 4 == 0 else 0,
                    has_measurable_goal=1 if i % 5 == 0 else 0,
                    domain_tags=["health"] if i < num_items // 2 else ["tech"]
                ),
                time_decay_weight=0.8
            )
            items.append(item)
        
        return items
    
    def test_cluster_items_basic(self):
        """Test basic clustering functionality."""
        items = self.create_test_items(10)
        
        result = cluster_items(items)
        
        assert "clusters" in result
        assert "items" in result
        assert "algorithm_used" in result
        
        # Should have some clusters
        assert len(result["clusters"]) > 0
        assert len(result["clusters"]) <= 10  # Should not exceed number of items
        
        # All items should be returned
        assert len(result["items"]) == 10
        
        # Items should have cluster_id assigned
        for item in result["items"]:
            assert hasattr(item, 'cluster_id')
            assert item.cluster_id is not None
    
    def test_cluster_items_empty_input(self):
        """Test clustering with empty input."""
        result = cluster_items([])
        
        assert result["clusters"] == []
        assert result["items"] == []
        assert result["algorithm_used"] == "none"
    
    def test_cluster_items_no_embeddings(self):
        """Test clustering with items that have no embeddings."""
        items = []
        for i in range(5):
            item = EnrichedItem(
                source="test",
                title=f"Test item {i}",
                body=f"Test body {i}",
                embedding=None  # No embedding
            )
            items.append(item)
        
        result = cluster_items(items)
        
        # Should return empty clusters but all items
        assert result["clusters"] == []
        assert len(result["items"]) == 5
        
        # Items should have cluster_id = -1 (no cluster)
        for item in result["items"]:
            assert item.cluster_id == -1
    
    def test_cluster_items_with_k_parameter(self):
        """Test clustering with specific k parameter."""
        items = self.create_test_items(20)
        
        result = cluster_items(items, k=3)
        
        # Should respect the k parameter (approximately)
        assert len(result["clusters"]) <= 3
        assert result["algorithm_used"] == "KMeans"
    
    def test_cluster_items_hdbscan(self):
        """Test clustering with HDBSCAN (if available)."""
        items = self.create_test_items(15)
        
        with patch('app.analyze.cluster.HDBSCAN_AVAILABLE', True):
            with patch('app.analyze.cluster._cluster_with_hdbscan') as mock_hdbscan_func:
                with patch('app.analyze.cluster.settings') as mock_settings:
                    mock_settings.use_hdbscan = True
                    mock_settings.clustering_min_cluster_size = 2
                    mock_settings.clustering_min_samples = 2
                    mock_settings.max_clusters = 25
                    
                    # Mock HDBSCAN function to return cluster labels
                    mock_hdbscan_func.return_value = (np.array([0, 0, 1, 1, 2, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2]), "HDBSCAN")
                    
                    result = cluster_items(items, use_hdbscan=True)
                    
                    assert result["algorithm_used"] == "HDBSCAN"
                    assert len(result["clusters"]) > 0
    
    def test_cluster_summaries_structure(self):
        """Test that cluster summaries have correct structure."""
        items = self.create_test_items(10)
        
        result = cluster_items(items)
        
        for cluster in result["clusters"]:
            assert hasattr(cluster, 'cluster_id')
            assert hasattr(cluster, 'size')
            assert hasattr(cluster, 'top_keywords')
            assert hasattr(cluster, 'representatives')
            
            assert isinstance(cluster.cluster_id, int)
            assert isinstance(cluster.size, int)
            assert isinstance(cluster.top_keywords, list)
            assert isinstance(cluster.representatives, list)
            
            assert cluster.size > 0
            assert len(cluster.top_keywords) <= 5
            assert len(cluster.representatives) <= 3
    
    def test_extract_top_keywords(self):
        """Test keyword extraction functionality."""
        items = self.create_test_items(5)
        
        keywords = _extract_top_keywords(items)
        
        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        
        # Should contain some relevant keywords (be more flexible with TF-IDF results)
        all_text = " ".join([item.title + " " + (item.body or "") for item in items]).lower()
        if keywords:  # Only check if keywords were extracted
            # At least one keyword should be found in the text
            found_keywords = [kw for kw in keywords if kw.lower() in all_text]
            assert len(found_keywords) > 0, f"None of the keywords {keywords} found in text"
    
    def test_extract_top_keywords_empty(self):
        """Test keyword extraction with empty input."""
        keywords = _extract_top_keywords([])
        assert keywords == []
    
    def test_extract_top_keywords_no_text(self):
        """Test keyword extraction with items that have no text."""
        items = []
        for i in range(3):
            item = EnrichedItem(
                source="test",
                title="",  # Empty title
                body="",   # Empty body
                embedding=[0.1] * 384
            )
            items.append(item)
        
        keywords = _extract_top_keywords(items)
        assert keywords == []
    
    def test_select_representatives(self):
        """Test representative selection functionality."""
        items = self.create_test_items(10)
        
        representatives = _select_representatives(items)
        
        assert isinstance(representatives, list)
        assert len(representatives) <= 3
        
        # Should be titles from the items
        item_titles = [item.title for item in items if item.title]
        for rep in representatives:
            assert rep in item_titles
    
    def test_select_representatives_empty(self):
        """Test representative selection with empty input."""
        representatives = _select_representatives([])
        assert representatives == []
    
    def test_select_representatives_no_titles(self):
        """Test representative selection with items that have no titles."""
        items = []
        for i in range(3):
            item = EnrichedItem(
                source="test",
                title="",  # Empty title
                body=f"Body {i}",
                score=100 + i,
                num_comments=10 + i,
                embedding=[0.1] * 384
            )
            items.append(item)
        
        representatives = _select_representatives(items)
        assert representatives == []
    
    def test_clustering_deterministic(self):
        """Test that clustering is deterministic with fixed seed."""
        items = self.create_test_items(10)
        
        # Run clustering twice with same seed
        result1 = cluster_items(items, k=2)
        result2 = cluster_items(items, k=2)
        
        # Should produce same number of clusters
        assert len(result1["clusters"]) == len(result2["clusters"])
        
        # Should produce same algorithm
        assert result1["algorithm_used"] == result2["algorithm_used"]
    
    def test_clustering_performance(self):
        """Test clustering performance with larger dataset."""
        items = self.create_test_items(100)  # 100 items
        
        import time
        start_time = time.time()
        
        result = cluster_items(items)
        
        processing_time = time.time() - start_time
        
        # Should complete in reasonable time (less than 5 seconds as per requirements)
        assert processing_time < 5.0
        
        # Should still produce valid results
        assert len(result["clusters"]) > 0
        assert len(result["items"]) == 100
    
    def test_clustering_mixed_embeddings(self):
        """Test clustering with items that have mixed embedding availability."""
        items = []
        
        # Items with embeddings
        for i in range(5):
            item = EnrichedItem(
                source="test",
                title=f"Item with embedding {i}",
                body=f"Body {i}",
                embedding=[0.1 + i * 0.1] * 384,
                score=100 + i,
                num_comments=10 + i
            )
            items.append(item)
        
        # Items without embeddings
        for i in range(3):
            item = EnrichedItem(
                source="test",
                title=f"Item without embedding {i}",
                body=f"Body {i}",
                embedding=None,
                score=50 + i,
                num_comments=5 + i
            )
            items.append(item)
        
        result = cluster_items(items)
        
        # Should cluster items with embeddings
        items_with_embeddings = [item for item in result["items"] if item.embedding is not None]
        items_without_embeddings = [item for item in result["items"] if item.embedding is None]
        
        assert len(items_with_embeddings) == 5
        assert len(items_without_embeddings) == 3
        
        # Items with embeddings should have valid cluster IDs
        for item in items_with_embeddings:
            assert item.cluster_id is not None
            assert item.cluster_id >= 0
        
        # Items without embeddings should have cluster_id = -1
        for item in items_without_embeddings:
            assert item.cluster_id == -1


class TestClusteringEdgeCases:
    """Test edge cases and error handling."""
    
    def test_clustering_single_item(self):
        """Test clustering with single item."""
        items = [EnrichedItem(
            source="test",
            title="Single item",
            body="Single body",
            embedding=[0.1] * 384,
            score=100,
            num_comments=10
        )]
        
        result = cluster_items(items)
        
        assert len(result["clusters"]) == 1
        assert result["clusters"][0].size == 1
        assert result["items"][0].cluster_id == 0
    
    def test_clustering_identical_items(self):
        """Test clustering with identical items."""
        items = []
        for i in range(5):
            item = EnrichedItem(
                source="test",
                title="Identical title",
                body="Identical body",
                embedding=[0.1] * 384,  # Same embedding
                score=100,
                num_comments=10
            )
            items.append(item)
        
        result = cluster_items(items)
        
        # Should handle identical items gracefully
        assert len(result["clusters"]) > 0
        assert len(result["items"]) == 5
    
    def test_clustering_invalid_embeddings(self):
        """Test clustering with invalid embeddings."""
        items = []
        for i in range(3):
            item = EnrichedItem(
                source="test",
                title=f"Item {i}",
                body=f"Body {i}",
                embedding=[0.1] * (100 + i),  # Different dimensions
                score=100 + i,
                num_comments=10 + i
            )
            items.append(item)
        
        # Should handle gracefully and return empty clusters
        result = cluster_items(items)
        
        assert result["clusters"] == []
        assert len(result["items"]) == 3
