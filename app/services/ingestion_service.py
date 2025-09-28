"""
Ingestion service for coordinating data collection from all sources.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from app.ingestion.reddit_source import RedditSource, RedditItem
from app.ingestion.hackernews_source import HackerNewsSource, HackerNewsItem
from app.ingestion.gnews_source import GoogleNewsSource, GoogleNewsItem

logger = logging.getLogger(__name__)


@dataclass
class NormalizedItem:
    """Normalized item from any source."""
    source: str
    subsource: str
    title: str
    url: str
    created_utc: int
    score: int
    num_comments: int
    body: str
    raw: Dict[str, Any]


class IngestionService:
    """Service for coordinating data ingestion from all sources."""
    
    def __init__(self):
        """Initialize ingestion service."""
        self.sources = {}
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize all data sources."""
        try:
            self.sources["reddit"] = RedditSource()
            logger.info("Reddit source initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit source: {e}")
            self.sources["reddit"] = None
        
        try:
            self.sources["hackernews"] = HackerNewsSource()
            logger.info("Hacker News source initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Hacker News source: {e}")
            self.sources["hackernews"] = None
        
        try:
            self.sources["gnews"] = GoogleNewsSource()
            logger.info("Google News source initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google News source: {e}")
            self.sources["gnews"] = None
    
    async def run_ingestion(
        self, 
        days: int = 7, 
        min_score: int = 10, 
        min_comments: int = 5,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run ingestion from all sources.
        
        Args:
            days: Number of days to look back
            min_score: Minimum score threshold
            min_comments: Minimum comments threshold
            sources: List of sources to use (None for all)
            
        Returns:
            Dictionary with ingestion results
        """
        logger.info(f"Starting ingestion for {days} days, min_score={min_score}, min_comments={min_comments}")
        
        if sources is None:
            sources = list(self.sources.keys())
        
        # Run ingestion from all sources in parallel
        tasks = []
        for source_name in sources:
            if self.sources.get(source_name):
                task = self._fetch_from_source(
                    source_name, days, min_score, min_comments
                )
                tasks.append(task)
            else:
                logger.warning(f"Source {source_name} not available")
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        all_items = []
        source_stats = {}
        
        for i, result in enumerate(results):
            source_name = sources[i]
            if isinstance(result, Exception):
                logger.error(f"Error in {source_name}: {result}")
                source_stats[source_name] = {
                    "status": "error",
                    "error": str(result),
                    "count": 0
                }
            else:
                items, stats = result
                all_items.extend(items)
                source_stats[source_name] = stats
        
        # Convert to normalized format
        normalized_items = self._normalize_items(all_items)
        
        # Calculate overall stats
        total_items = len(normalized_items)
        successful_sources = sum(1 for stats in source_stats.values() if stats["status"] == "success")
        
        logger.info(f"Ingestion completed: {total_items} items from {successful_sources}/{len(sources)} sources")
        
        return {
            "items": [asdict(item) for item in normalized_items],
            "total_items": total_items,
            "sources_used": sources,
            "source_stats": source_stats,
            "ingestion_time": datetime.utcnow().isoformat(),
            "parameters": {
                "days": days,
                "min_score": min_score,
                "min_comments": min_comments
            }
        }
    
    async def _fetch_from_source(
        self, 
        source_name: str, 
        days: int, 
        min_score: int, 
        min_comments: int
    ) -> tuple[List[NormalizedItem], Dict[str, Any]]:
        """Fetch items from a specific source."""
        source = self.sources[source_name]
        if not source:
            return [], {"status": "error", "error": "Source not initialized", "count": 0}
        
        try:
            start_time = datetime.utcnow()
            
            if source_name == "reddit":
                items = await source.fetch_items(days, min_score, min_comments)
            elif source_name == "hackernews":
                items = await source.fetch_items(days, min_score, min_comments)
            elif source_name == "gnews":
                items = await source.fetch_items(days, min_score, min_comments)
            else:
                raise ValueError(f"Unknown source: {source_name}")
            
            # Convert to normalized format
            normalized_items = self._normalize_items(items)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            stats = {
                "status": "success",
                "count": len(normalized_items),
                "duration_seconds": duration,
                "error": None
            }
            
            logger.info(f"{source_name}: {len(normalized_items)} items in {duration:.2f}s")
            return normalized_items, stats
            
        except Exception as e:
            logger.error(f"Error fetching from {source_name}: {e}")
            return [], {
                "status": "error",
                "count": 0,
                "duration_seconds": 0,
                "error": str(e)
            }
    
    def _normalize_items(self, items: List) -> List[NormalizedItem]:
        """Convert items from any source to normalized format."""
        normalized = []
        
        for item in items:
            if isinstance(item, (RedditItem, HackerNewsItem, GoogleNewsItem)):
                normalized_item = NormalizedItem(
                    source=item.source,
                    subsource=item.subsource,
                    title=item.title,
                    url=item.url,
                    created_utc=item.created_utc,
                    score=item.score,
                    num_comments=item.num_comments,
                    body=item.body,
                    raw=item.raw or {}
                )
                normalized.append(normalized_item)
            elif isinstance(item, NormalizedItem):
                # Already normalized, just add it
                normalized.append(item)
            else:
                logger.warning(f"Unknown item type: {type(item)}")
        
        return normalized
    
    async def test_sources(self) -> Dict[str, bool]:
        """Test connection to all sources."""
        results = {}
        
        for source_name, source in self.sources.items():
            if source:
                try:
                    if hasattr(source, 'test_connection'):
                        results[source_name] = await source.test_connection()
                    else:
                        results[source_name] = True
                except Exception as e:
                    logger.error(f"Error testing {source_name}: {e}")
                    results[source_name] = False
            else:
                results[source_name] = False
        
        return results
    
    async def close(self):
        """Close all source connections."""
        for source_name, source in self.sources.items():
            if source and hasattr(source, 'close'):
                try:
                    await source.close()
                    logger.info(f"Closed {source_name} source")
                except Exception as e:
                    logger.error(f"Error closing {source_name}: {e}")
