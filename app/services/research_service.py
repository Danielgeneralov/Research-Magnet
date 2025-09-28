"""
Research service for managing research runs and results.
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from app.models import ResearchRun, ProblemCluster, DataSource
from app.schemas import ResearchResults, ResearchRunCreate
from app.config import settings

logger = logging.getLogger(__name__)


class ResearchService:
    """Service for managing research operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def start_research_run(self) -> ResearchRun:
        """Start a new research run."""
        try:
            # Create new research run
            research_run = ResearchRun(
                status="running",
                config_snapshot=settings.dict()
            )
            self.db.add(research_run)
            self.db.commit()
            self.db.refresh(research_run)
            
            logger.info(f"Started research run {research_run.id}")
            return research_run
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to start research run: {e}")
            raise
    
    async def run_research(self, run_id: int) -> None:
        """Run the complete research pipeline."""
        try:
            research_run = self.db.query(ResearchRun).filter(ResearchRun.id == run_id).first()
            if not research_run:
                logger.error(f"Research run {run_id} not found")
                return
            
            logger.info(f"Starting research pipeline for run {run_id}")
            
            # TODO: Implement actual research pipeline
            # 1. Collect data from all sources
            # 2. Process with NLP pipeline
            # 3. Cluster problems
            # 4. Rank results
            
            # For now, just mark as completed
            research_run.status = "completed"
            research_run.completed_at = datetime.now()
            research_run.total_sources = 3  # Placeholder
            research_run.total_items = 0    # Placeholder
            research_run.total_problems = 0 # Placeholder
            
            self.db.commit()
            logger.info(f"Completed research run {run_id}")
            
        except Exception as e:
            logger.error(f"Research run {run_id} failed: {e}")
            research_run = self.db.query(ResearchRun).filter(ResearchRun.id == run_id).first()
            if research_run:
                research_run.status = "failed"
                research_run.error_message = str(e)
                research_run.completed_at = datetime.now()
                self.db.commit()
            raise
    
    async def get_research_runs(self, limit: int = 10, offset: int = 0) -> List[ResearchRun]:
        """Get list of research runs."""
        return (
            self.db.query(ResearchRun)
            .order_by(ResearchRun.started_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    async def get_research_run(self, run_id: int) -> Optional[ResearchRun]:
        """Get a specific research run."""
        return self.db.query(ResearchRun).filter(ResearchRun.id == run_id).first()
    
    async def get_latest_results(self) -> Optional[ResearchResults]:
        """Get the latest research results."""
        # Get the most recent completed run
        latest_run = (
            self.db.query(ResearchRun)
            .filter(ResearchRun.status == "completed")
            .order_by(ResearchRun.completed_at.desc())
            .first()
        )
        
        if not latest_run:
            return None
        
        return await self.get_results_by_run(latest_run.id)
    
    async def get_results_by_run(self, run_id: int) -> Optional[ResearchResults]:
        """Get research results for a specific run."""
        research_run = await self.get_research_run(run_id)
        if not research_run:
            return None
        
        # Get problem clusters for this run
        clusters = (
            self.db.query(ProblemCluster)
            .filter(ProblemCluster.research_run_id == run_id)
            .order_by(ProblemCluster.final_score.desc())
            .limit(10)
            .all()
        )
        
        # Get data sources
        sources = self.db.query(DataSource).filter(DataSource.is_active == True).all()
        
        return ResearchResults(
            research_run=research_run,
            total_problems=len(clusters),
            top_clusters=clusters,
            sources_used=sources
        )
