"""
Enrichment API endpoints for Research Magnet Phase 2.
"""

import time
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from collections import defaultdict
from datetime import datetime, timedelta

from app.schemas import (
    EnrichmentRequest, 
    EnrichmentResponse, 
    EnrichedItem,
    PipelineRunRequest,
    PipelineRunResponse,
    EnhancedPipelineRunResponse
)
from app.services.ingestion_service import IngestionService
from app.db import SessionLocal
from app.enrich.normalize import normalize_items
from app.enrich.sentiment import add_sentiment
from app.enrich.nlp import add_entities
from app.enrich.embed import add_embeddings
from app.utils.time_decay import add_time_decay
from app.utils.logging import get_enrichment_logger
from app.analyze.cluster import cluster_items

router = APIRouter()
logger = get_enrichment_logger("enrichment_api")

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


@router.post("/run", response_model=EnrichmentResponse)
async def run_enrichment(
    request: EnrichmentRequest,
    req: Request,
    db: SessionLocal = Depends(get_db)
):
    """
    Run enrichment pipeline on items.
    
    If items are provided in the request, use them directly.
    Otherwise, fetch items from ingestion service.
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
        # Get items to enrich
        if request.items:
            items = request.items
            logger.info(f"Using {len(items)} provided items for enrichment")
        else:
            # Fetch items from ingestion service
            ingestion_service = IngestionService()
            ingestion_result = await ingestion_service.run_ingestion(
                days=request.days,
                min_score=10,
                min_comments=5
            )
            items = ingestion_result["items"]
            logger.info(f"Fetched {len(items)} items from ingestion service")
        
        if not items:
            return EnrichmentResponse(
                count=0,
                items=[],
                processing_time_ms=0.0
            )
        
        # Run enrichment pipeline
        enriched_items = await run_enrichment_pipeline(
            items, 
            half_life_hours=request.half_life_hours
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return EnrichmentResponse(
            count=len(enriched_items),
            items=enriched_items,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Enrichment failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Enrichment failed: {str(e)}"
        )


@router.post("/pipeline/run", response_model=EnhancedPipelineRunResponse)
async def run_full_pipeline(
    request: PipelineRunRequest,
    req: Request,
    db: SessionLocal = Depends(get_db)
):
    """
    Run the complete pipeline: ingestion + enrichment + clustering.
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
        # Run ingestion
        ingestion_service = IngestionService()
        ingestion_result = await ingestion_service.run_ingestion(
            days=request.days,
            min_score=10,
            min_comments=5
        )
        
        items = ingestion_result["items"]
        logger.info(f"Completed ingestion: {len(items)} items")
        
        # Run enrichment
        enriched_items = await run_enrichment_pipeline(
            items,
            half_life_hours=request.half_life_hours
        )
        
        # Run clustering
        clustering_result = cluster_items(items=enriched_items)
        clustered_items = clustering_result["items"]
        clusters = clustering_result["clusters"]
        
        processing_time = (time.time() - start_time) * 1000
        
        return EnhancedPipelineRunResponse(
            research_run_id="pipeline_run",  # Placeholder since we don't track run IDs
            total_items=len(items),
            enriched_items=len(enriched_items),
            clustered_items=len([item for item in clustered_items if item.cluster_id is not None and item.cluster_id >= 0]),
            clusters=clusters,
            processing_time_ms=processing_time,
            items=clustered_items
        )
        
    except Exception as e:
        logger.error(f"Full pipeline failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline failed: {str(e)}"
        )


async def run_enrichment_pipeline(
    items: List[Dict[str, Any]], 
    half_life_hours: int = 72
) -> List[EnrichedItem]:
    """
    Run the complete enrichment pipeline on items.
    
    Args:
        items: List of raw items to enrich
        half_life_hours: Half-life for time decay calculation
    
    Returns:
        List of enriched items
    """
    if not items:
        return []
    
    logger.info(f"Starting enrichment pipeline for {len(items)} items")
    
    # Step 1: Normalize and derive signals
    items = normalize_items(items)
    
    # Step 2: Add sentiment analysis
    items = add_sentiment(items)
    
    # Step 3: Extract entities
    items = add_entities(items)
    
    # Step 4: Generate embeddings
    items = add_embeddings(items)
    
    # Step 5: Add time decay weights
    items = add_time_decay(items, half_life_hours)
    
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
