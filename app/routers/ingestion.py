"""
Ingestion router for data collection endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging

from app.services.ingestion_service import IngestionService

router = APIRouter()
logger = logging.getLogger(__name__)

# Global ingestion service instance
ingestion_service = IngestionService()


@router.get("/run")
async def run_ingestion(
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    min_score: int = Query(10, ge=0, description="Minimum score threshold"),
    min_comments: int = Query(5, ge=0, description="Minimum comments threshold"),
    sources: Optional[List[str]] = Query(None, description="Sources to use (reddit, hackernews, gnews)"),
    background: bool = Query(False, description="Run in background")
):
    """
    Run data ingestion from all configured sources.
    
    Returns normalized items in the format:
    {
        "source": "reddit|hackernews|gnews",
        "subsource": "r/loseit | HN | query",
        "title": "...",
        "url": "...",
        "created_utc": 12345678,
        "score": 512,
        "num_comments": 88,
        "body": "(optional)",
        "raw": {...}
    }
    """
    try:
        # Validate sources parameter
        valid_sources = ["reddit", "hackernews", "gnews"]
        if sources:
            invalid_sources = [s for s in sources if s not in valid_sources]
            if invalid_sources:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid sources: {invalid_sources}. Valid sources: {valid_sources}"
                )
        
        logger.info(f"Starting ingestion: days={days}, min_score={min_score}, min_comments={min_comments}, sources={sources}")
        
        if background:
            # Run in background (for future implementation)
            # For now, just run synchronously
            logger.info("Background execution requested but not yet implemented")
        
        # Run ingestion
        result = await ingestion_service.run_ingestion(
            days=days,
            min_score=min_score,
            min_comments=min_comments,
            sources=sources
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ingestion endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/status")
async def get_sources_status():
    """Get status of all data sources."""
    try:
        status = await ingestion_service.test_sources()
        return {
            "sources": status,
            "total_sources": len(status),
            "active_sources": sum(1 for active in status.values() if active)
        }
    except Exception as e:
        logger.error(f"Error checking sources status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/reddit/test")
async def test_reddit():
    """Test Reddit source connection."""
    try:
        reddit_source = ingestion_service.sources.get("reddit")
        if not reddit_source:
            raise HTTPException(status_code=503, detail="Reddit source not available")
        
        is_connected = await reddit_source.test_connection()
        return {
            "source": "reddit",
            "connected": is_connected,
            "message": "Reddit API connection successful" if is_connected else "Reddit API connection failed"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Reddit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/hackernews/test")
async def test_hackernews():
    """Test Hacker News source connection."""
    try:
        hn_source = ingestion_service.sources.get("hackernews")
        if not hn_source:
            raise HTTPException(status_code=503, detail="Hacker News source not available")
        
        is_connected = await hn_source.test_connection()
        return {
            "source": "hackernews",
            "connected": is_connected,
            "message": "Hacker News API connection successful" if is_connected else "Hacker News API connection failed"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Hacker News: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/gnews/test")
async def test_gnews():
    """Test Google News source connection."""
    try:
        gnews_source = ingestion_service.sources.get("gnews")
        if not gnews_source:
            raise HTTPException(status_code=503, detail="Google News source not available")
        
        is_connected = await gnews_source.test_connection()
        return {
            "source": "gnews",
            "connected": is_connected,
            "message": "Google News RSS connection successful" if is_connected else "Google News RSS connection failed"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Google News: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def ingestion_health():
    """Health check for ingestion service."""
    try:
        sources_status = await ingestion_service.test_sources()
        active_sources = sum(1 for active in sources_status.values() if active)
        total_sources = len(sources_status)
        
        return {
            "status": "healthy" if active_sources > 0 else "degraded",
            "active_sources": active_sources,
            "total_sources": total_sources,
            "sources": sources_status
        }
    except Exception as e:
        logger.error(f"Error in ingestion health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
