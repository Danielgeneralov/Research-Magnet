"""
Hacker News data source integration using Algolia API.
"""

import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class HackerNewsItem:
    """Normalized Hacker News item."""
    source: str = "hackernews"
    subsource: str = "HN"
    title: str = ""
    url: str = ""
    created_utc: int = 0
    score: int = 0
    num_comments: int = 0
    body: str = ""
    raw: Dict[str, Any] = None


class HackerNewsSource:
    """Hacker News data source using Algolia API."""
    
    def __init__(self):
        """Initialize Hacker News source."""
        self.base_url = settings.hn_base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Search queries for different topics
        self.queries = [
            "startup",
            "entrepreneur", 
            "productivity",
            "SaaS",
            "machine learning",
            "artificial intelligence",
            "programming",
            "web development",
            "data science",
            "technology"
        ]
        
        logger.info(f"Hacker News source initialized with {len(self.queries)} search queries")
    
    async def fetch_items(self, days: int = 7, min_score: int = 10, min_comments: int = 5) -> List[HackerNewsItem]:
        """
        Fetch items from Hacker News.
        
        Args:
            days: Number of days to look back
            min_score: Minimum score threshold
            min_comments: Minimum comments threshold
            
        Returns:
            List of normalized Hacker News items
        """
        items = []
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        cutoff_timestamp = int(cutoff_time.timestamp())
        
        try:
            for query in self.queries:
                try:
                    query_items = await self._search_stories(
                        query, cutoff_timestamp, min_score, min_comments
                    )
                    items.extend(query_items)
                    logger.info(f"Fetched {len(query_items)} items for query: {query}")
                    
                except Exception as e:
                    logger.error(f"Error fetching items for query '{query}': {e}")
                    continue
            
            # Remove duplicates based on story ID
            seen_ids = set()
            unique_items = []
            for item in items:
                story_id = item.raw.get("objectID") if item.raw else None
                if story_id and story_id not in seen_ids:
                    seen_ids.add(story_id)
                    unique_items.append(item)
            
            logger.info(f"Hacker News source returned {len(unique_items)} unique items")
            return unique_items
            
        except Exception as e:
            logger.error(f"Error in Hacker News fetch: {e}")
            return []
    
    async def _search_stories(
        self, 
        query: str, 
        cutoff_timestamp: int, 
        min_score: int, 
        min_comments: int
    ) -> List[HackerNewsItem]:
        """Search for stories using Algolia API."""
        items = []
        
        try:
            # Build search parameters
            params = {
                "query": query,
                "tags": "story",  # Only stories, not comments
                "numericFilters": f"created_at_i>={cutoff_timestamp},points>={min_score},num_comments>={min_comments}",
                "hitsPerPage": 100,
                "page": 0
            }
            
            response = await self.client.get(
                f"{self.base_url}/search",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            hits = data.get("hits", [])
            
            for hit in hits:
                try:
                    # Extract story data
                    story_id = hit.get("objectID")
                    title = hit.get("title", "")
                    url = hit.get("url", "")
                    points = hit.get("points", 0)
                    num_comments = hit.get("num_comments", 0)
                    created_at = hit.get("created_at_i", 0)
                    author = hit.get("author", "")
                    story_text = hit.get("story_text", "")
                    
                    # Skip if no URL (Ask HN, Show HN, etc.)
                    if not url:
                        continue
                    
                    # Create normalized item
                    item = HackerNewsItem(
                        source="hackernews",
                        subsource=f"HN ({query})",
                        title=title,
                        url=url,
                        created_utc=created_at,
                        score=points,
                        num_comments=num_comments,
                        body=story_text,
                        raw={
                            "objectID": story_id,
                            "author": author,
                            "story_id": story_id,
                            "story_text": story_text,
                            "comment_text": hit.get("comment_text", ""),
                            "parent_id": hit.get("parent_id"),
                            "story_title": hit.get("story_title", ""),
                            "story_url": hit.get("story_url", ""),
                            "created_at": hit.get("created_at"),
                            "created_at_i": created_at,
                            "tags": hit.get("_tags", []),
                            "points": points,
                            "num_comments": num_comments,
                            "url": url,
                            "title": title
                        }
                    )
                    
                    items.append(item)
                    
                except Exception as e:
                    logger.warning(f"Error processing HN story {hit.get('objectID', 'unknown')}: {e}")
                    continue
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in HN search: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error in HN search for '{query}': {e}")
        
        return items
    
    async def test_connection(self) -> bool:
        """Test Hacker News API connection."""
        try:
            response = await self.client.get(f"{self.base_url}/search", params={"query": "test", "hitsPerPage": 1})
            response.raise_for_status()
            logger.info("Hacker News API connection successful")
            return True
        except Exception as e:
            logger.error(f"Hacker News API connection failed: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
