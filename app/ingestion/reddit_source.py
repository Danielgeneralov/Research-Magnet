"""
Reddit data source integration using PRAW.
"""

import praw
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RedditItem:
    """Normalized Reddit item."""
    source: str = "reddit"
    subsource: str = ""
    title: str = ""
    url: str = ""
    created_utc: int = 0
    score: int = 0
    num_comments: int = 0
    body: str = ""
    raw: Dict[str, Any] = None


class RedditSource:
    """Reddit data source using PRAW."""
    
    def __init__(self):
        """Initialize Reddit source."""
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            raise ValueError("Reddit API credentials not configured")
        
        self.reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent
        )
        
        # Subreddits to monitor
        self.subreddits = [
            "startups",
            "entrepreneur", 
            "technology",
            "programming",
            "webdev",
            "MachineLearning",
            "artificial",
            "datascience",
            "productivity",
            "SaaS"
        ]
        
        logger.info(f"Reddit source initialized for {len(self.subreddits)} subreddits")
    
    async def fetch_items(self, days: int = 7, min_score: int = 10, min_comments: int = 5) -> List[RedditItem]:
        """
        Fetch items from Reddit subreddits.
        
        Args:
            days: Number of days to look back
            min_score: Minimum score threshold
            min_comments: Minimum comments threshold
            
        Returns:
            List of normalized Reddit items
        """
        items = []
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        try:
            for subreddit_name in self.subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # Fetch hot posts
                    hot_items = await self._fetch_posts(
                        subreddit, "hot", cutoff_time, min_score, min_comments
                    )
                    items.extend(hot_items)
                    
                    # Fetch top posts from the week
                    top_items = await self._fetch_posts(
                        subreddit, "top", cutoff_time, min_score, min_comments, time_filter="week"
                    )
                    items.extend(top_items)
                    
                    logger.info(f"Fetched {len(hot_items + top_items)} items from r/{subreddit_name}")
                    
                except Exception as e:
                    logger.error(f"Error fetching from r/{subreddit_name}: {e}")
                    continue
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_items = []
            for item in items:
                if item.url not in seen_urls:
                    seen_urls.add(item.url)
                    unique_items.append(item)
            
            logger.info(f"Reddit source returned {len(unique_items)} unique items")
            return unique_items
            
        except Exception as e:
            logger.error(f"Error in Reddit fetch: {e}")
            return []
    
    async def _fetch_posts(
        self, 
        subreddit, 
        sort: str, 
        cutoff_time: datetime, 
        min_score: int, 
        min_comments: int,
        time_filter: str = None
    ) -> List[RedditItem]:
        """Fetch posts from a subreddit with filtering."""
        items = []
        
        try:
            # Get the appropriate listing
            if sort == "hot":
                posts = subreddit.hot(limit=100)
            elif sort == "top":
                posts = subreddit.top(time_filter=time_filter or "week", limit=100)
            else:
                posts = subreddit.new(limit=100)
            
            for post in posts:
                try:
                    # Check if post is within time range
                    post_time = datetime.utcfromtimestamp(post.created_utc)
                    if post_time < cutoff_time:
                        continue
                    
                    # Apply filters
                    if post.score < min_score or post.num_comments < min_comments:
                        continue
                    
                    # Skip stickied posts
                    if post.stickied:
                        continue
                    
                    # Create normalized item
                    item = RedditItem(
                        source="reddit",
                        subsource=f"r/{subreddit.display_name}",
                        title=post.title,
                        url=post.url,
                        created_utc=int(post.created_utc),
                        score=post.score,
                        num_comments=post.num_comments,
                        body=post.selftext if hasattr(post, 'selftext') else "",
                        raw={
                            "id": post.id,
                            "author": str(post.author) if post.author else "[deleted]",
                            "permalink": f"https://reddit.com{post.permalink}",
                            "subreddit": subreddit.display_name,
                            "upvote_ratio": getattr(post, 'upvote_ratio', 0),
                            "is_self": post.is_self,
                            "over_18": post.over_18,
                            "spoiler": getattr(post, 'spoiler', False),
                            "locked": getattr(post, 'locked', False),
                            "archived": getattr(post, 'archived', False)
                        }
                    )
                    
                    items.append(item)
                    
                except Exception as e:
                    logger.warning(f"Error processing post {getattr(post, 'id', 'unknown')}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error fetching {sort} posts from r/{subreddit.display_name}: {e}")
        
        return items
    
    async def test_connection(self) -> bool:
        """Test Reddit API connection."""
        try:
            # Try to access a simple subreddit
            test_subreddit = self.reddit.subreddit("test")
            _ = test_subreddit.display_name
            logger.info("Reddit API connection successful")
            return True
        except Exception as e:
            logger.error(f"Reddit API connection failed: {e}")
            return False
