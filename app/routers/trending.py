"""
Trending API endpoints for Research Magnet Phase 4.
Provides cluster trend detection and analysis functionality.
"""

import time
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from collections import defaultdict
from datetime import datetime, timedelta

from app.schemas import (
    TrendRequest,
    TrendResponse,
    ClusterTrend,
    EnrichedItem,
    ClusterSummary
)
from app.services.ingestion_service import IngestionService
from app.db import SessionLocal
from app.enrich.normalize import normalize_items
from app.enrich.sentiment import add_sentiment
from app.enrich.nlp import add_entities
from app.enrich.embed import add_embeddings
from app.utils.time_decay import add_time_decay
from app.analyze.trend import cluster_trends
from app.analyze.cluster import cluster_items
from app.utils.logging import get_enrichment_logger

router = APIRouter()
logger = get_enrichment_logger("trending_api")

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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/run", response_model=TrendResponse)
async def run_trend_analysis(
    request: TrendRequest,
    req: Request,
    db: SessionLocal = Depends(get_db)
):
    """
    Run trend analysis to detect trending clusters.
    
    If items and clusters are provided in the request, use them directly.
    Otherwise, fetch items from ingestion service and run full pipeline.
    """
    # Rate limiting
    client_ip = req.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 10 requests per minute."
        )
    
    # Input validation
    if request.limit > 1000:
        raise HTTPException(
            status_code=400,
            detail="Limit too high. Maximum 1000 items per request."
        )
    
    start_time = time.time()
    
    try:
        # Get items and clusters
        if request.items and request.clusters:
            # Use provided items and clusters
            items = [item.dict() if hasattr(item, 'dict') else item for item in request.items]
            clusters = [cluster.dict() if hasattr(cluster, 'dict') else cluster for cluster in request.clusters]
            logger.info(f"Using {len(items)} provided items and {len(clusters)} clusters for trend analysis")
        else:
            # Run full pipeline to get items and clusters
            ingestion_service = IngestionService()
            ingestion_result = await ingestion_service.run_ingestion(
                days=request.days,
                min_score=10,
                min_comments=5
            )
            
            items = ingestion_result["items"]
            logger.info(f"Fetched {len(items)} items from ingestion service")
            
            # Run enrichment
            items = normalize_items(items)
            items = add_sentiment(items)
            items = add_entities(items)
            items = add_embeddings(items)
            items = add_time_decay(items)
            
            # Run clustering
            clustering_result = cluster_items(items=[EnrichedItem(**item) for item in items])
            items = [item.dict() for item in clustering_result["items"]]
            clusters = [cluster.dict() for cluster in clustering_result["clusters"]]
            
            logger.info(f"Completed enrichment and clustering: {len(items)} items, {len(clusters)} clusters")
        
        if not items:
            return TrendResponse(
                trends=[],
                total_items=0,
                processing_time_ms=0.0
            )
        
        # Run trend analysis
        trend_summaries = cluster_trends(items, clusters)
        
        # Convert to ClusterTrend objects
        cluster_trends_list = []
        for trend_data in trend_summaries:
            try:
                cluster_trend = ClusterTrend(
                    cluster_id=trend_data["cluster_id"],
                    trend=trend_data["trend"],
                    last_count=trend_data["last_count"],
                    sma_short=trend_data["sma_short"],
                    sma_long=trend_data["sma_long"],
                    series_tail=trend_data["series_tail"],
                    top_keywords=trend_data.get("top_keywords"),
                    representatives=trend_data.get("representatives"),
                    size=trend_data.get("size")
                )
                cluster_trends_list.append(cluster_trend)
            except Exception as e:
                logger.warning(f"Failed to create ClusterTrend: {e}")
                continue
        
        processing_time = (time.time() - start_time) * 1000
        
        return TrendResponse(
            trends=cluster_trends_list,
            total_items=len(items),
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Trend analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Trend analysis failed: {str(e)}"
        )
