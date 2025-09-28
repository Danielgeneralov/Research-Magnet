"""
Clustering functionality for Research Magnet Phase 3.
Groups enriched items into clusters of related problems.
"""

import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import logging

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False

from app.config import settings
from app.schemas import EnrichedItem, ClusterSummary

logger = logging.getLogger(__name__)


def cluster_items(
    items: List[EnrichedItem], 
    k: Optional[int] = None,
    use_hdbscan: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Cluster enriched items into groups of related problems.
    
    Args:
        items: List of enriched items with embeddings
        k: Number of clusters (if None, uses heuristic: sqrt(n) capped at max_clusters)
        use_hdbscan: Whether to use HDBSCAN (if None, uses config setting)
    
    Returns:
        Dictionary with 'clusters' and 'items' keys
    """
    if not items:
        return {"clusters": [], "items": [], "algorithm_used": "none"}
    
    # Filter items with embeddings
    items_with_embeddings = [item for item in items if item.embedding is not None]
    
    if not items_with_embeddings:
        logger.warning("No items with embeddings found for clustering")
        # Set cluster_id to -1 for all items
        for item in items:
            item.cluster_id = -1
        return {"clusters": [], "items": items, "algorithm_used": "none"}
    
    logger.info(f"Clustering {len(items_with_embeddings)} items with embeddings")
    
    # Use config defaults if not specified
    if use_hdbscan is None:
        use_hdbscan = settings.use_hdbscan
    
    # Calculate number of clusters if not provided
    if k is None:
        n_items = len(items_with_embeddings)
        k = min(int(np.sqrt(n_items)), settings.max_clusters)
        k = max(1, k)  # At least 1 cluster
    
    # Extract embeddings with validation
    try:
        embeddings = np.array([item.embedding for item in items_with_embeddings])
    except ValueError as e:
        logger.warning(f"Invalid embeddings detected: {e}")
        return {"clusters": [], "items": items, "algorithm_used": "none"}
    
    # Perform clustering
    if use_hdbscan and HDBSCAN_AVAILABLE:
        cluster_labels, algorithm_used = _cluster_with_hdbscan(embeddings)
    else:
        cluster_labels, algorithm_used = _cluster_with_kmeans(embeddings, k)
    
    # Assign cluster IDs to items
    cluster_id_map = {}
    for i, item in enumerate(items_with_embeddings):
        cluster_id = int(cluster_labels[i])
        if cluster_id == -1:  # HDBSCAN noise points
            cluster_id = max(cluster_labels) + 1 if len(set(cluster_labels)) > 1 else 0
        cluster_id_map[i] = cluster_id  # Use index instead of item as key
    
    # Add cluster_id to all items (including those without embeddings)
    for i, item in enumerate(items):
        if item in items_with_embeddings:
            # Find the index of this item in items_with_embeddings
            embedding_index = items_with_embeddings.index(item)
            item.cluster_id = cluster_id_map[embedding_index]
        else:
            item.cluster_id = -1  # No cluster for items without embeddings
    
    # Ensure all items have cluster_id set
    for item in items:
        if item.cluster_id is None:
            item.cluster_id = -1
    
    # Build cluster summaries
    clusters = _build_cluster_summaries(items_with_embeddings, cluster_id_map)
    
    logger.info(f"Created {len(clusters)} clusters using {algorithm_used}")
    
    return {
        "clusters": clusters,
        "items": items,
        "algorithm_used": algorithm_used
    }


def _cluster_with_kmeans(embeddings: np.ndarray, k: int) -> Tuple[np.ndarray, str]:
    """Cluster embeddings using KMeans."""
    logger.info(f"Using KMeans with k={k}")
    
    kmeans = KMeans(
        n_clusters=k,
        random_state=settings.clustering_random_seed,
        n_init=10
    )
    cluster_labels = kmeans.fit_predict(embeddings)
    
    return cluster_labels, "KMeans"


def _cluster_with_hdbscan(embeddings: np.ndarray) -> Tuple[np.ndarray, str]:
    """Cluster embeddings using HDBSCAN."""
    logger.info("Using HDBSCAN")
    
    if not HDBSCAN_AVAILABLE:
        raise ImportError("HDBSCAN is not available")
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=settings.clustering_min_cluster_size,
        min_samples=settings.clustering_min_samples,
        metric='cosine'
    )
    cluster_labels = clusterer.fit_predict(embeddings)
    
    return cluster_labels, "HDBSCAN"


def _build_cluster_summaries(
    items: List[EnrichedItem], 
    cluster_id_map: Dict[int, int]
) -> List[ClusterSummary]:
    """Build cluster summaries with keywords and representatives."""
    clusters = []
    
    # Group items by cluster
    cluster_groups = {}
    for i, item in enumerate(items):
        cluster_id = cluster_id_map[i]
        if cluster_id not in cluster_groups:
            cluster_groups[cluster_id] = []
        cluster_groups[cluster_id].append(item)
    
    # Build summary for each cluster
    for cluster_id, cluster_items in cluster_groups.items():
        if not cluster_items:
            continue
            
        # Extract top keywords using TF-IDF
        top_keywords = _extract_top_keywords(cluster_items)
        
        # Select representative items (top 3 by engagement)
        representatives = _select_representatives(cluster_items)
        
        cluster_summary = ClusterSummary(
            cluster_id=cluster_id,
            size=len(cluster_items),
            top_keywords=top_keywords,
            representatives=representatives
        )
        clusters.append(cluster_summary)
    
    # Sort clusters by size (largest first)
    clusters.sort(key=lambda x: x.size, reverse=True)
    
    return clusters


def _extract_top_keywords(items: List[EnrichedItem], max_keywords: int = 5) -> List[str]:
    """Extract top keywords from cluster items using TF-IDF."""
    if not items:
        return []
    
    # Prepare text for TF-IDF
    texts = []
    for item in items:
        text_parts = []
        if item.title:
            text_parts.append(item.title)
        if item.body:
            text_parts.append(item.body)
        texts.append(" ".join(text_parts))
    
    if not texts or not any(texts):
        return []
    
    try:
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=settings.tfidf_max_features,
            stop_words='english',
            ngram_range=(1, 2),  # Include unigrams and bigrams
            min_df=1,  # Minimum document frequency
            max_df=0.95  # Maximum document frequency
        )
        
        # Fit and transform
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        
        # Calculate mean TF-IDF scores across all documents in cluster
        mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
        
        # Get top keywords
        top_indices = np.argsort(mean_scores)[-max_keywords:][::-1]
        top_keywords = [feature_names[i] for i in top_indices if mean_scores[i] > 0]
        
        return top_keywords[:max_keywords]
        
    except Exception as e:
        logger.warning(f"Failed to extract keywords: {e}")
        return []


def _select_representatives(items: List[EnrichedItem], max_representatives: int = 3) -> List[str]:
    """Select representative items based on engagement metrics."""
    if not items:
        return []
    
    # Calculate engagement score for each item
    scored_items = []
    for item in items:
        # Combine score and comments with time decay weight
        engagement_score = 0
        if item.score is not None:
            engagement_score += item.score
        if item.num_comments is not None:
            engagement_score += item.num_comments * 2  # Comments are weighted more
        
        # Apply time decay if available
        if item.time_decay_weight is not None:
            engagement_score *= item.time_decay_weight
        
        scored_items.append((item, engagement_score))
    
    # Sort by engagement score (highest first)
    scored_items.sort(key=lambda x: x[1], reverse=True)
    
    # Select top representatives
    representatives = []
    for item, _ in scored_items[:max_representatives]:
        if item.title:
            representatives.append(item.title)
    
    return representatives


def _validate_clustering_input(items: List[EnrichedItem]) -> bool:
    """Validate input for clustering."""
    if not items:
        return False
    
    # Check if at least some items have embeddings
    items_with_embeddings = [item for item in items if item.embedding is not None]
    if not items_with_embeddings:
        logger.warning("No items with embeddings found")
        return False
    
    # Check embedding dimensions
    embedding_dims = [len(item.embedding) for item in items_with_embeddings if item.embedding]
    if not embedding_dims:
        return False
    
    # All embeddings should have the same dimension
    if len(set(embedding_dims)) > 1:
        logger.warning("Inconsistent embedding dimensions found")
        return False
    
    return True
