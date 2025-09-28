"""
Pydantic schemas for Research Magnet API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ResearchRunBase(BaseModel):
    """Base schema for research runs."""
    pass


class ResearchRunCreate(ResearchRunBase):
    """Schema for creating a research run."""
    pass


class ResearchRun(ResearchRunBase):
    """Schema for research run responses."""
    id: int
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    total_sources: int
    total_items: int
    total_problems: int
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class DataSourceBase(BaseModel):
    """Base schema for data sources."""
    name: str
    source_type: str
    url: Optional[str] = None
    is_active: bool = True


class DataSourceCreate(DataSourceBase):
    """Schema for creating data sources."""
    pass


class DataSource(DataSourceBase):
    """Schema for data source responses."""
    id: int
    last_checked: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ResearchItemBase(BaseModel):
    """Base schema for research items."""
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None


class ResearchItemCreate(ResearchItemBase):
    """Schema for creating research items."""
    research_run_id: int
    source_id: int
    upvotes: int = 0
    comments: int = 0
    shares: int = 0
    raw_data: Optional[Dict[str, Any]] = None


class ResearchItem(ResearchItemBase):
    """Schema for research item responses."""
    id: int
    research_run_id: int
    source_id: int
    collected_at: datetime
    upvotes: int
    comments: int
    shares: int
    sentiment_score: Optional[float]
    problem_density: Optional[float]
    keyword_score: Optional[float]
    is_processed: bool
    is_duplicate: bool
    cluster_id: Optional[int]
    
    class Config:
        from_attributes = True


class ProblemClusterBase(BaseModel):
    """Base schema for problem clusters."""
    name: str
    description: Optional[str] = None
    keywords: Optional[List[str]] = None


class ProblemClusterCreate(ProblemClusterBase):
    """Schema for creating problem clusters."""
    research_run_id: int
    problem_score: float
    engagement_score: float
    freshness_score: float
    final_score: float
    item_count: int = 0
    source_diversity: int = 0


class ProblemCluster(ProblemClusterBase):
    """Schema for problem cluster responses."""
    id: int
    research_run_id: int
    problem_score: float
    engagement_score: float
    freshness_score: float
    final_score: float
    item_count: int
    source_diversity: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExportJobBase(BaseModel):
    """Base schema for export jobs."""
    research_run_id: int
    format: str


class ExportJobCreate(ExportJobBase):
    """Schema for creating export jobs."""
    pass


class ExportJob(ExportJobBase):
    """Schema for export job responses."""
    id: int
    file_path: Optional[str]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class ResearchResults(BaseModel):
    """Schema for research results summary."""
    research_run: ResearchRun
    total_problems: int
    top_clusters: List[ProblemCluster]
    sources_used: List[DataSource]
    export_formats: List[str] = ["json", "csv", "markdown"]


class HealthCheck(BaseModel):
    """Schema for health check responses."""
    status: str
    timestamp: datetime
    version: str
    database_connected: bool
    sources_status: Dict[str, str]


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
