"""
Export router for generating and downloading research results.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import logging
import os

from app.db import get_db
from app.schemas import ExportJob, ExportJobCreate
from app.services.export_service import ExportService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=ExportJob)
async def create_export_job(
    export_job: ExportJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new export job."""
    try:
        export_service = ExportService(db)
        job = await export_service.create_export_job(export_job)
        
        # Process export in background
        background_tasks.add_task(export_service.process_export_job, job.id)
        
        return job
    except Exception as e:
        logger.error(f"Failed to create export job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=List[ExportJob])
async def get_export_jobs(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get list of export jobs."""
    try:
        export_service = ExportService(db)
        jobs = await export_service.get_export_jobs(limit=limit, offset=offset)
        return jobs
    except Exception as e:
        logger.error(f"Failed to get export jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=ExportJob)
async def get_export_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific export job."""
    try:
        export_service = ExportService(db)
        job = await export_service.get_export_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Export job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get export job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{job_id}")
async def download_export(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Download an exported file."""
    try:
        export_service = ExportService(db)
        job = await export_service.get_export_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Export job not found")
        
        if job.status != "completed" or not job.file_path:
            raise HTTPException(status_code=400, detail="Export job not completed or file not available")
        
        if not os.path.exists(job.file_path):
            raise HTTPException(status_code=404, detail="Export file not found")
        
        return FileResponse(
            path=job.file_path,
            filename=os.path.basename(job.file_path),
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download export {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
