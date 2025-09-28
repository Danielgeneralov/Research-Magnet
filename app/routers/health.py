"""
Health check router.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging

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
