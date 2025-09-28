"""
Research router for managing research runs and results.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.db import get_db
from app.schemas import ResearchRun, ResearchResults, ResearchRunCreate
from app.services.research_service import ResearchService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/run", response_model=ResearchRun)
async def start_research_run(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start a new research run."""
    try:
        research_service = ResearchService(db)
        research_run = await research_service.start_research_run()
        
        # Run research in background
        background_tasks.add_task(research_service.run_research, research_run.id)
        
        return research_run
    except Exception as e:
        logger.error(f"Failed to start research run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs", response_model=List[ResearchRun])
async def get_research_runs(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get list of research runs."""
    try:
        research_service = ResearchService(db)
        runs = await research_service.get_research_runs(limit=limit, offset=offset)
        return runs
    except Exception as e:
        logger.error(f"Failed to get research runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}", response_model=ResearchRun)
async def get_research_run(
    run_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific research run."""
    try:
        research_service = ResearchService(db)
        run = await research_service.get_research_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Research run not found")
        return run
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get research run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results", response_model=ResearchResults)
async def get_latest_results(
    db: Session = Depends(get_db)
):
    """Get the latest research results."""
    try:
        research_service = ResearchService(db)
        results = await research_service.get_latest_results()
        if not results:
            raise HTTPException(status_code=404, detail="No research results found")
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{run_id}", response_model=ResearchResults)
async def get_results_by_run(
    run_id: int,
    db: Session = Depends(get_db)
):
    """Get research results for a specific run."""
    try:
        research_service = ResearchService(db)
        results = await research_service.get_results_by_run(run_id)
        if not results:
            raise HTTPException(status_code=404, detail="Research results not found")
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
