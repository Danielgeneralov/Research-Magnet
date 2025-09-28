"""
Google News data source integration via RSS parsing.
"""

import feedparser
import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlencode

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GoogleNewsItem:
    """Normalized Google News item."""
    source: str = "gnews"
    subsource: str = ""
    title: str = ""
    url: str = ""
    created_utc: int = 0
    score: int = 0
    num_comments: int = 0
    body: str = ""
    raw: Dict[str, Any] = None


class GoogleNewsSource:
    """Google News data source using RSS feeds."""
    
    def __init__(self):
        """Initialize Google News source."""
        self.base_url = "https://news.google.com/rss"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        
        # Use specific RSS feeds instead of search queries
        self.rss_feeds = [
            "https://techcrunch.com/feed/",  # TechCrunch
            "https://blog.ycombinator.com/feed/",  # Y Combinator
            "https://feeds.feedburner.com/venturebeat/SZYF",  # VentureBeat
            "https://feeds.feedburner.com/arstechnica/index/",  # Ars Technica
            "https://feeds.feedburner.com/oreilly/radar",  # O'Reilly Radar
            "https://feeds.feedburner.com/venturebeat/SZYF",  # VentureBeat
            "https://blog.ycombinator.com/feed/",  # Y Combinator
            "https://techcrunch.com/feed/",  # TechCrunch
            "https://feeds.feedburner.com/arstechnica/index/",  # Ars Technica
            "https://feeds.feedburner.com/oreilly/radar"  # O'Reilly Radar
        ]
        
        logger.info(f"RSS News source initialized with {len(self.rss_feeds)} feeds")
    
    async def fetch_items(self, days: int = 7, min_score: int = 0, min_comments: int = 0) -> List[GoogleNewsItem]:
        """
        Fetch items from RSS feeds.
        
        Args:
            days: Number of days to look back
            min_score: Minimum score threshold (not applicable for RSS)
            min_comments: Minimum comments threshold (not applicable for RSS)
            
        Returns:
            List of normalized Google News items
        """
        items = []
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        # Make cutoff_time timezone-aware for comparison
        cutoff_time = cutoff_time.replace(tzinfo=None)
        
        try:
            for i, feed_url in enumerate(self.rss_feeds):
                try:
                    feed_items = await self._fetch_rss_feed(
                        feed_url, cutoff_time
                    )
                    items.extend(feed_items)
                    logger.info(f"Fetched {len(feed_items)} items from feed {i+1}: {feed_url}")
                    
                except Exception as e:
                    logger.error(f"Error fetching items from feed '{feed_url}': {e}")
                    continue
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_items = []
            for item in items:
                if item.url not in seen_urls:
                    seen_urls.add(item.url)
                    unique_items.append(item)
            
            logger.info(f"Google News source returned {len(unique_items)} unique items")
            return unique_items
            
        except Exception as e:
            logger.error(f"Error in Google News fetch: {e}")
            return []
    
    async def _fetch_rss_feed(self, feed_url: str, cutoff_time: datetime) -> List[GoogleNewsItem]:
        """Fetch RSS feed from a specific URL."""
        items = []
        
        try:
            # Fetch RSS feed directly
            response = await self.client.get(feed_url)
            response.raise_for_status()
            
            # Parse RSS feed
            feed = feedparser.parse(response.text)
            
            if feed.bozo:
                logger.warning(f"RSS feed parsing warning for '{feed_url}': {feed.bozo_exception}")
            
            for entry in feed.entries:
                try:
                    # Parse publication date (be more lenient with date parsing)
                    pub_date = self._parse_date(entry.get("published", ""))
                    if pub_date:
                        # Convert to naive datetime for comparison
                        if pub_date.tzinfo is not None:
                            pub_date = pub_date.replace(tzinfo=None)
                        if pub_date < cutoff_time:
                            continue
                    # If we can't parse the date, include the item anyway
                    
                    # Extract article data
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    summary = entry.get("summary", "")
                    source = entry.get("source", {}).get("title", "Unknown")
                    
                    # Skip if no title or link
                    if not title or not link:
                        continue
                    
                    # Create normalized item
                    item = GoogleNewsItem(
                        source="gnews",
                        subsource=f"RSS ({source})",
                        title=title,
                        url=link,
                        created_utc=int(pub_date.timestamp()) if pub_date else 0,
                        score=0,  # RSS doesn't have scores
                        num_comments=0,  # RSS doesn't have comments
                        body=summary,
                        raw={
                            "title": title,
                            "link": link,
                            "summary": summary,
                            "published": entry.get("published", ""),
                            "source": source,
                            "tags": [tag.term for tag in entry.get("tags", [])],
                            "author": entry.get("author", ""),
                            "guid": entry.get("guid", ""),
                            "feed_title": feed.feed.get("title", ""),
                            "feed_description": feed.feed.get("description", ""),
                            "feed_url": feed_url
                        }
                    )
                    
                    items.append(item)
                    
                except Exception as e:
                    logger.warning(f"Error processing RSS entry: {e}")
                    continue
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching RSS from '{feed_url}': {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching RSS from '{feed_url}': {e}")
        
        return items
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats from RSS feeds."""
        if not date_str:
            return None
        
        # Common date formats in RSS feeds
        date_formats = [
            "%a, %d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S"
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try feedparser's date parsing as fallback
        try:
            import time
            parsed_time = time.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
            return datetime(*parsed_time[:6])
        except:
            pass
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    async def test_connection(self) -> bool:
        """Test RSS feeds connection."""
        try:
            # Test the first RSS feed
            test_feed = self.rss_feeds[0]
            response = await self.client.get(test_feed)
            response.raise_for_status()
            
            # Try to parse the feed
            feed = feedparser.parse(response.text)
            if not feed.bozo:
                logger.info("RSS feeds connection successful")
                return True
            else:
                logger.warning(f"RSS feed parsing warning: {feed.bozo_exception}")
                return False
                
        except Exception as e:
            logger.error(f"RSS feeds connection failed: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
