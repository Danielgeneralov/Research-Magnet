"""
Clustering API endpoints for Research Magnet Phase 3.
"""

import time
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from collections import defaultdict
from datetime import datetime, timedelta

from app.schemas import (
    ClusteringRequest,
    ClusteringResponse,
    EnrichedItem
)
from app.services.ingestion_service import IngestionService
from app.enrich.normalize import normalize_items
from app.enrich.sentiment import add_sentiment
from app.enrich.nlp import add_entities
from app.enrich.embed import add_embeddings
from app.utils.time_decay import add_time_decay
from app.analyze.cluster import cluster_items
from app.utils.logging import get_enrichment_logger

router = APIRouter()
logger = get_enrichment_logger("clustering_api")

# Simple rate limiter
request_counts = defaultdict(list)
RATE_LIMIT = 10  # requests per minute
RATE_WINDOW = 60  # seconds

def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit."""
    now = datetime.now()
    # Clean old requests
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip] 
        if now - req_time < timedelta(seconds=RATE_WINDOW)
    ]
    
    # Check if under limit
    if len(request_counts[client_ip]) >= RATE_LIMIT:
        return False
    
    # Add current request
    request_counts[client_ip].append(now)
    return True


def get_db():
    """Dependency to get database session."""
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/run", response_model=ClusteringResponse)
async def run_clustering(
    request: ClusteringRequest,
    req: Request,
    db = Depends(get_db)
):
    """
    Run clustering on enriched items.
    
    If items are provided in the request, use them directly.
    Otherwise, fetch and enrich items from ingestion service.
    """
    # Rate limiting
    client_ip = req.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 10 requests per minute."
        )
    
    # Input validation
    if request.items and len(request.items) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Too many items. Maximum 1000 items per request."
        )
    
    start_time = time.time()
    
    try:
        # Get items to cluster
        if request.items:
            items = request.items
            logger.info(f"Using {len(items)} provided items for clustering")
        else:
            # Fetch and enrich items from ingestion service
            ingestion_service = IngestionService()
            ingestion_result = await ingestion_service.run_ingestion(
                days=7,  # Default to 7 days
                min_score=10,
                min_comments=5
            )
            raw_items = ingestion_result["items"]
            logger.info(f"Fetched {len(raw_items)} items from ingestion service")
            
            if not raw_items:
                return ClusteringResponse(
                    clusters=[],
                    items=[],
                    processing_time_ms=0.0,
                    algorithm_used="none"
                )
            
            # Enrich items
            items = await _enrich_items(raw_items)
            logger.info(f"Enriched {len(items)} items for clustering")
        
        if not items:
            return ClusteringResponse(
                clusters=[],
                items=[],
                processing_time_ms=0.0,
                algorithm_used="none"
            )
        
        # Run clustering
        clustering_result = cluster_items(
            items=items,
            k=request.k
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return ClusteringResponse(
            clusters=clustering_result["clusters"],
            items=clustering_result["items"],
            processing_time_ms=processing_time,
            algorithm_used=clustering_result["algorithm_used"]
        )
        
    except Exception as e:
        logger.error(f"Clustering failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Clustering failed: {str(e)}"
        )


async def _enrich_items(raw_items: List[Dict[str, Any]]) -> List[EnrichedItem]:
    """
    Enrich raw items with NLP features.
    
    Args:
        raw_items: List of raw items from ingestion
    
    Returns:
        List of enriched items
    """
    if not raw_items:
        return []
    
    logger.info(f"Starting enrichment for {len(raw_items)} items")
    
    # Step 1: Normalize and derive signals
    items = normalize_items(raw_items)
    
    # Step 2: Add sentiment analysis
    items = add_sentiment(items)
    
    # Step 3: Extract entities
    items = add_entities(items)
    
    # Step 4: Generate embeddings
    items = add_embeddings(items)
    
    # Step 5: Add time decay weights
    items = add_time_decay(items, half_life_hours=72)
    
    # Convert to EnrichedItem objects
    enriched_items = []
    for item in items:
        try:
            enriched_item = EnrichedItem(
                source=item.get('source', 'unknown'),
                title=item.get('title', ''),
                body=item.get('body'),
                url=item.get('url'),
                created_utc=item.get('created_utc'),
                score=item.get('score'),
                num_comments=item.get('num_comments'),
                sentiment=item.get('sentiment'),
                entities=item.get('entities', []),
                embedding=item.get('embedding'),
                signals=item.get('signals'),
                time_decay_weight=item.get('time_decay_weight')
            )
            enriched_items.append(enriched_item)
        except Exception as e:
            logger.warning(f"Failed to create EnrichedItem: {e}")
            continue
    
    logger.info(f"Completed enrichment: {len(enriched_items)} items processed")
    return enriched_items
