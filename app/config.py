"""
Configuration management for Research Magnet.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database
    database_url: str = Field(default="sqlite:///./research_magnet.db", env="DATABASE_URL")
    
    # Reddit API
    reddit_client_id: Optional[str] = Field(default=None, env="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(default=None, env="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(default="research-magnet/0.1.0", env="REDDIT_USER_AGENT")
    reddit_rate_limit: int = Field(default=60, env="REDDIT_RATE_LIMIT")
    
    # Hacker News API
    hn_base_url: str = Field(default="https://hn.algolia.com/api/v1", env="HN_BASE_URL")
    hn_rate_limit: int = Field(default=100, env="HN_RATE_LIMIT")
    
    # RSS Feeds
    rss_feeds: List[str] = Field(default_factory=list, env="RSS_FEEDS")
    rss_rate_limit: int = Field(default=30, env="RSS_RATE_LIMIT")
    
    # NLP Configuration
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    similarity_threshold: float = Field(default=0.8, env="SIMILARITY_THRESHOLD")
    clustering_min_samples: int = Field(default=5, env="CLUSTERING_MIN_SAMPLES")
    clustering_min_cluster_size: int = Field(default=3, env="CLUSTERING_MIN_CLUSTER_SIZE")
    
    # Clustering Configuration
    use_hdbscan: bool = Field(default=False, env="USE_HDBSCAN")
    max_clusters: int = Field(default=25, env="MAX_CLUSTERS")
    tfidf_max_features: int = Field(default=1000, env="TFIDF_MAX_FEATURES")
    clustering_random_seed: int = Field(default=42, env="CLUSTERING_RANDOM_SEED")
    
    # Export Configuration
    export_format: str = Field(default="json", env="EXPORT_FORMAT")
    export_dir: str = Field(default="./exports", env="EXPORT_DIR")
    
    # Phase 4 Scoring Configuration
    w_e: float = Field(default=0.35, env="W_E")
    w_n: float = Field(default=0.20, env="W_N")
    w_q: float = Field(default=0.15, env="W_Q")
    w_p: float = Field(default=0.15, env="W_P")
    w_d: float = Field(default=0.10, env="W_D")
    w_t: float = Field(default=0.05, env="W_T")
    half_life_hours: int = Field(default=72, env="HALF_LIFE_HOURS")
    density_norm: float = Field(default=20.0, env="DENSITY_NORM")
    
    # Phase 4 Trend Detection Configuration
    trend_bucket_hours: int = Field(default=6, env="TREND_BUCKET_HOURS")
    trend_window_short_h: int = Field(default=24, env="TREND_WINDOW_SHORT_H")
    trend_window_long_h: int = Field(default=72, env="TREND_WINDOW_LONG_H")
    trend_delta: float = Field(default=0.15, env="TREND_DELTA")
    min_support: int = Field(default=3, env="MIN_SUPPORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> any:
            if field_name == "rss_feeds":
                return [feed.strip() for feed in raw_val.split(",") if feed.strip()]
            return cls.json_loads(raw_val)


# Global settings instance
settings = Settings()
