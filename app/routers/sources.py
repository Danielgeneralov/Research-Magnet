"""
Data sources router for managing data source configurations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from app.db import get_db
from app.schemas import DataSource, DataSourceCreate
from app.services.source_service import SourceService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[DataSource])
async def get_data_sources(db: Session = Depends(get_db)):
    """Get all configured data sources."""
    try:
        source_service = SourceService(db)
        sources = await source_service.get_all_sources()
        return sources
    except Exception as e:
        logger.error(f"Failed to get data sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=DataSource)
async def create_data_source(
    source: DataSourceCreate,
    db: Session = Depends(get_db)
):
    """Create a new data source."""
    try:
        source_service = SourceService(db)
        new_source = await source_service.create_source(source)
        return new_source
    except Exception as e:
        logger.error(f"Failed to create data source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}", response_model=DataSource)
async def get_data_source(
    source_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific data source."""
    try:
        source_service = SourceService(db)
        source = await source_service.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Data source not found")
        return source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get data source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=dict)
async def get_sources_status(db: Session = Depends(get_db)):
    """Get status of all data sources."""
    try:
        source_service = SourceService(db)
        status = await source_service.check_sources_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get sources status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
