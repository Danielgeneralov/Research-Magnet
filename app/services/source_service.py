"""
Source service for managing data sources.
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import logging

from app.models import DataSource
from app.schemas import DataSourceCreate

logger = logging.getLogger(__name__)


class SourceService:
    """Service for managing data sources."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_all_sources(self) -> List[DataSource]:
        """Get all data sources."""
        return self.db.query(DataSource).all()
    
    async def get_source(self, source_id: int) -> Optional[DataSource]:
        """Get a specific data source."""
        return self.db.query(DataSource).filter(DataSource.id == source_id).first()
    
    async def create_source(self, source_data: DataSourceCreate) -> DataSource:
        """Create a new data source."""
        try:
            source = DataSource(**source_data.dict())
            self.db.add(source)
            self.db.commit()
            self.db.refresh(source)
            return source
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create data source: {e}")
            raise
    
    async def initialize_default_sources(self) -> None:
        """Initialize default data sources."""
        default_sources = [
            {
                "name": "Reddit - Startups",
                "source_type": "reddit",
                "url": "r/startups",
                "is_active": True
            },
            {
                "name": "Reddit - Entrepreneur", 
                "source_type": "reddit",
                "url": "r/entrepreneur",
                "is_active": True
            },
            {
                "name": "Reddit - Technology",
                "source_type": "reddit", 
                "url": "r/technology",
                "is_active": True
            },
            {
                "name": "Hacker News",
                "source_type": "hackernews",
                "url": "https://hn.algolia.com/api/v1",
                "is_active": True
            },
            {
                "name": "TechCrunch RSS",
                "source_type": "rss",
                "url": "https://techcrunch.com/feed/",
                "is_active": True
            }
        ]
        
        for source_data in default_sources:
            existing = self.db.query(DataSource).filter(
                DataSource.name == source_data["name"]
            ).first()
            
            if not existing:
                source = DataSource(**source_data)
                self.db.add(source)
        
        self.db.commit()
        logger.info("Default data sources initialized")
    
    async def check_sources_status(self) -> Dict[str, str]:
        """Check status of all data sources."""
        sources = await self.get_all_sources()
        status = {}
        
        for source in sources:
            if source.is_active:
                # TODO: Implement actual status checking
                status[source.name] = "unknown"
            else:
                status[source.name] = "disabled"
        
        return status
