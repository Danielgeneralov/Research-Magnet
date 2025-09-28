"""
Export service for generating research results in various formats.
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging
import os
import json

from app.models import ExportJob, ResearchRun, ProblemCluster, ResearchItem
from app.schemas import ExportJobCreate
from app.config import settings

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting research results."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_export_job(self, job_data: ExportJobCreate) -> ExportJob:
        """Create a new export job."""
        try:
            job = ExportJob(**job_data.dict())
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            return job
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create export job: {e}")
            raise
    
    async def get_export_jobs(self, limit: int = 10, offset: int = 0) -> List[ExportJob]:
        """Get list of export jobs."""
        return (
            self.db.query(ExportJob)
            .order_by(ExportJob.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    async def get_export_job(self, job_id: int) -> Optional[ExportJob]:
        """Get a specific export job."""
        return self.db.query(ExportJob).filter(ExportJob.id == job_id).first()
    
    async def process_export_job(self, job_id: int) -> None:
        """Process an export job."""
        try:
            job = await self.get_export_job(job_id)
            if not job:
                logger.error(f"Export job {job_id} not found")
                return
            
            logger.info(f"Processing export job {job_id} in {job.format} format")
            
            # Get research data
            research_run = self.db.query(ResearchRun).filter(ResearchRun.id == job.research_run_id).first()
            if not research_run:
                job.status = "failed"
                job.error_message = "Research run not found"
                job.completed_at = datetime.now()
                self.db.commit()
                return
            
            # Create export directory if it doesn't exist
            os.makedirs(settings.export_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"research_results_{job.research_run_id}_{timestamp}.{job.format}"
            file_path = os.path.join(settings.export_dir, filename)
            
            # Export based on format
            if job.format == "json":
                await self._export_json(research_run, file_path)
            elif job.format == "csv":
                await self._export_csv(research_run, file_path)
            elif job.format == "markdown":
                await self._export_markdown(research_run, file_path)
            else:
                raise ValueError(f"Unsupported export format: {job.format}")
            
            # Update job status
            job.status = "completed"
            job.file_path = file_path
            job.completed_at = datetime.now()
            self.db.commit()
            
            logger.info(f"Export job {job_id} completed: {file_path}")
            
        except Exception as e:
            logger.error(f"Export job {job_id} failed: {e}")
            job = await self.get_export_job(job_id)
            if job:
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.now()
                self.db.commit()
            raise
    
    async def _export_json(self, research_run: ResearchRun, file_path: str) -> None:
        """Export results as JSON."""
        # Get clusters and items
        clusters = (
            self.db.query(ProblemCluster)
            .filter(ProblemCluster.research_run_id == research_run.id)
            .order_by(ProblemCluster.final_score.desc())
            .all()
        )
        
        items = (
            self.db.query(ResearchItem)
            .filter(ResearchItem.research_run_id == research_run.id)
            .all()
        )
        
        data = {
            "research_run": {
                "id": research_run.id,
                "started_at": research_run.started_at.isoformat(),
                "completed_at": research_run.completed_at.isoformat() if research_run.completed_at else None,
                "status": research_run.status,
                "total_sources": research_run.total_sources,
                "total_items": research_run.total_items,
                "total_problems": research_run.total_problems
            },
            "clusters": [
                {
                    "id": cluster.id,
                    "name": cluster.name,
                    "description": cluster.description,
                    "keywords": cluster.keywords,
                    "problem_score": cluster.problem_score,
                    "engagement_score": cluster.engagement_score,
                    "freshness_score": cluster.freshness_score,
                    "final_score": cluster.final_score,
                    "item_count": cluster.item_count,
                    "source_diversity": cluster.source_diversity
                }
                for cluster in clusters
            ],
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "content": item.content,
                    "url": item.url,
                    "author": item.author,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "upvotes": item.upvotes,
                    "comments": item.comments,
                    "shares": item.shares,
                    "sentiment_score": item.sentiment_score,
                    "problem_density": item.problem_density,
                    "cluster_id": item.cluster_id
                }
                for item in items
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def _export_csv(self, research_run: ResearchRun, file_path: str) -> None:
        """Export results as CSV."""
        import pandas as pd
        
        # Get clusters
        clusters = (
            self.db.query(ProblemCluster)
            .filter(ProblemCluster.research_run_id == research_run.id)
            .order_by(ProblemCluster.final_score.desc())
            .all()
        )
        
        # Convert to DataFrame
        cluster_data = []
        for cluster in clusters:
            cluster_data.append({
                "cluster_id": cluster.id,
                "name": cluster.name,
                "description": cluster.description,
                "keywords": ", ".join(cluster.keywords) if cluster.keywords else "",
                "problem_score": cluster.problem_score,
                "engagement_score": cluster.engagement_score,
                "freshness_score": cluster.freshness_score,
                "final_score": cluster.final_score,
                "item_count": cluster.item_count,
                "source_diversity": cluster.source_diversity
            })
        
        df = pd.DataFrame(cluster_data)
        df.to_csv(file_path, index=False)
    
    async def _export_markdown(self, research_run: ResearchRun, file_path: str) -> None:
        """Export results as Markdown."""
        # Get clusters
        clusters = (
            self.db.query(ProblemCluster)
            .filter(ProblemCluster.research_run_id == research_run.id)
            .order_by(ProblemCluster.final_score.desc())
            .all()
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Research Results - Run {research_run.id}\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Status:** {research_run.status}\n")
            f.write(f"**Total Sources:** {research_run.total_sources}\n")
            f.write(f"**Total Items:** {research_run.total_items}\n")
            f.write(f"**Total Problems:** {research_run.total_problems}\n\n")
            
            f.write("## Top Problem Clusters\n\n")
            
            for i, cluster in enumerate(clusters, 1):
                f.write(f"### {i}. {cluster.name}\n\n")
                if cluster.description:
                    f.write(f"{cluster.description}\n\n")
                
                f.write(f"**Score:** {cluster.final_score:.2f}\n")
                f.write(f"**Problem Score:** {cluster.problem_score:.2f}\n")
                f.write(f"**Engagement Score:** {cluster.engagement_score:.2f}\n")
                f.write(f"**Freshness Score:** {cluster.freshness_score:.2f}\n")
                f.write(f"**Items:** {cluster.item_count}\n")
                f.write(f"**Source Diversity:** {cluster.source_diversity}\n")
                
                if cluster.keywords:
                    f.write(f"**Keywords:** {', '.join(cluster.keywords)}\n")
                
                f.write("\n---\n\n")
