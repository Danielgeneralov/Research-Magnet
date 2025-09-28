"""
SQLAlchemy models for Research Magnet.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.sql import func
from app.db import Base


class ResearchRun(Base):
    """Model for tracking research runs."""
    
    __tablename__ = "research_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running", nullable=False)  # running, completed, failed
    total_sources = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    total_problems = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    config_snapshot = Column(JSON, nullable=True)  # Store config at time of run


class DataSource(Base):
    """Model for tracking data sources."""
    
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    source_type = Column(String(50), nullable=False)  # reddit, rss, hackernews
    url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())


class ResearchItem(Base):
    """Model for individual research items (posts, articles, etc.)."""
    
    __tablename__ = "research_items"
    
    id = Column(Integer, primary_key=True, index=True)
    research_run_id = Column(Integer, nullable=False, index=True)
    source_id = Column(Integer, nullable=False, index=True)
    
    # Basic content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    url = Column(String(1000), nullable=True)
    author = Column(String(200), nullable=True)
    
    # Metadata
    published_at = Column(DateTime, nullable=True)
    collected_at = Column(DateTime, default=func.now())
    
    # Engagement metrics
    upvotes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    
    # NLP scores
    sentiment_score = Column(Float, nullable=True)
    problem_density = Column(Float, nullable=True)
    keyword_score = Column(Float, nullable=True)
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    cluster_id = Column(Integer, nullable=True)
    
    # Raw data
    raw_data = Column(JSON, nullable=True)


class ProblemCluster(Base):
    """Model for clustered problems."""
    
    __tablename__ = "problem_clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    research_run_id = Column(Integer, nullable=False, index=True)
    
    # Cluster metadata
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # List of keywords
    
    # Scoring
    problem_score = Column(Float, nullable=False)
    engagement_score = Column(Float, nullable=False)
    freshness_score = Column(Float, nullable=False)
    final_score = Column(Float, nullable=False)
    
    # Statistics
    item_count = Column(Integer, default=0)
    source_diversity = Column(Integer, default=0)  # Number of different sources
    
    created_at = Column(DateTime, default=func.now())


class ExportJob(Base):
    """Model for tracking export jobs."""
    
    __tablename__ = "export_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    research_run_id = Column(Integer, nullable=False, index=True)
    
    # Export details
    format = Column(String(20), nullable=False)  # json, csv, markdown
    file_path = Column(String(500), nullable=True)
    status = Column(String(50), default="pending", nullable=False)  # pending, completed, failed
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
