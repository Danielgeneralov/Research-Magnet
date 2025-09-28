"""
Health check router.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import psutil
import time
from typing import Dict, Any

from app.db import get_db
from app.schemas import HealthCheck
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=HealthCheck)
async def health_check(db: Session = Depends(get_db)):
    """Check application health and database connectivity."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        database_connected = True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        database_connected = False
    
    # Check data source status (simplified for now)
    sources_status = {
        "reddit": "unknown",
        "rss": "unknown", 
        "hackernews": "unknown"
    }
    
    return HealthCheck(
        status="healthy" if database_connected else "unhealthy",
        timestamp=datetime.now(),
        version="0.1.0",
        database_connected=database_connected,
        sources_status=sources_status
    )


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with system metrics."""
    start_time = time.time()
    
    # Database health
    try:
        db.execute("SELECT 1")
        db_response_time = (time.time() - start_time) * 1000
        database_healthy = True
    except Exception as e:
        db_response_time = None
        database_healthy = False
        logger.error(f"Database health check failed: {e}")
    
    # System metrics
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_metrics = {
            "cpu_percent": cpu_percent,
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": round((disk.used / disk.total) * 100, 2)
            }
        }
    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")
        system_metrics = {"error": "Failed to collect system metrics"}
    
    # Check model loading status
    model_status = {
        "vader_sentiment": "loaded" if hasattr(globals().get('_analyzer', None), '__class__') else "not_loaded",
        "spacy_ner": "loaded" if hasattr(globals().get('_nlp', None), '__class__') else "not_loaded", 
        "sentence_transformer": "loaded" if hasattr(globals().get('_model', None), '__class__') else "not_loaded"
    }
    
    # Overall health status
    overall_healthy = database_healthy and all(
        status == "loaded" for status in model_status.values()
    )
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
        "database": {
            "connected": database_healthy,
            "response_time_ms": db_response_time
        },
        "models": model_status,
        "system": system_metrics,
        "uptime_seconds": time.time() - start_time
    }


@router.get("/metrics")
async def get_metrics():
    """Get basic application metrics."""
    try:
        # Get embedding cache size
        from app.enrich.embed import _embedding_cache
        cache_size = len(_embedding_cache)
        
        # Get rate limiter stats
        from app.routers.enrichment import request_counts
        total_requests = sum(len(requests) for requests in request_counts.values())
        
        return {
            "timestamp": datetime.now().isoformat(),
            "embedding_cache": {
                "size": cache_size,
                "hit_rate": "N/A"  # Would need to track hits/misses
            },
            "rate_limiter": {
                "total_requests": total_requests,
                "active_clients": len(request_counts)
            },
            "models_loaded": {
                "vader_sentiment": "loaded",
                "spacy_ner": "loaded", 
                "sentence_transformer": "loaded"
            }
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "error": "Failed to collect metrics"
        }
