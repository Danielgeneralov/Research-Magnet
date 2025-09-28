"""
Pydantic schemas for Research Magnet API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Tuple
from pydantic import BaseModel, Field, validator


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


# Phase 2 Enrichment Schemas

class Entity(BaseModel):
    """Schema for extracted entities."""
    text: str = Field(..., description="The entity text")
    label: str = Field(..., description="The entity label (ORG, PERSON, LOC, etc.)")


class Signals(BaseModel):
    """Schema for derived signals from text analysis."""
    is_question: int = Field(0, ge=0, le=1, description="1 if text contains a question")
    pain_markers: int = Field(0, ge=0, le=1, description="1 if text contains pain indicators")
    how_to_markers: int = Field(0, ge=0, le=1, description="1 if text contains how-to indicators")
    has_numbers: int = Field(0, ge=0, le=1, description="1 if text contains numbers")
    has_measurable_goal: int = Field(0, ge=0, le=1, description="1 if text contains measurable goals")
    domain_tags: List[str] = Field(default_factory=list, description="Detected domain tags")


class EnrichedItem(BaseModel):
    """Schema for enriched research items with NLP features."""
    # Original fields
    source: str = Field(..., description="Data source (reddit, hackernews, etc.)")
    title: str = Field(..., description="Item title")
    body: Optional[str] = Field(None, description="Item body content")
    url: Optional[str] = Field(None, description="Item URL")
    created_utc: Optional[float] = Field(None, description="Unix timestamp of creation")
    score: Optional[int] = Field(None, description="Upvote/score count")
    num_comments: Optional[int] = Field(None, description="Number of comments")
    
    # Enriched fields
    sentiment: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Sentiment score (-1 to 1)")
    entities: List[Entity] = Field(default_factory=list, description="Extracted entities")
    embedding: Optional[List[float]] = Field(None, description="Text embedding vector")
    signals: Optional[Signals] = Field(None, description="Derived signals")
    time_decay_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Time decay weight (0 to 1)")
    cluster_id: Optional[int] = Field(None, description="Cluster ID assigned during clustering")


class EnrichmentRequest(BaseModel):
    """Schema for enrichment request."""
    items: Optional[List[Dict[str, Any]]] = Field(None, description="Items to enrich (if not provided, will fetch from ingestion)")
    days: int = Field(7, ge=1, le=30, description="Days of data to fetch if items not provided")
    limit: int = Field(200, ge=1, le=1000, description="Maximum items to process")
    half_life_hours: int = Field(72, ge=1, le=168, description="Half-life for time decay in hours")


class EnrichmentResponse(BaseModel):
    """Schema for enrichment response."""
    count: int = Field(..., description="Number of enriched items")
    items: List[EnrichedItem] = Field(..., description="Enriched items")
    processing_time_ms: Optional[float] = Field(None, description="Total processing time in milliseconds")


class PipelineRunRequest(BaseModel):
    """Schema for full pipeline run request."""
    days: int = Field(7, ge=1, le=30, description="Days of data to fetch")
    limit: int = Field(200, ge=1, le=1000, description="Maximum items to process")
    half_life_hours: int = Field(72, ge=1, le=168, description="Half-life for time decay in hours")


class PipelineRunResponse(BaseModel):
    """Schema for full pipeline run response."""
    research_run_id: Optional[str] = Field(None, description="ID of the research run")
    total_items: int = Field(..., description="Total items processed")
    enriched_items: int = Field(..., description="Number of successfully enriched items")
    processing_time_ms: Optional[float] = Field(None, description="Total processing time in milliseconds")
    items: List[EnrichedItem] = Field(..., description="Enriched items")


# Phase 3 Clustering Schemas

class ClusterSummary(BaseModel):
    """Schema for cluster summary information."""
    cluster_id: int = Field(..., description="Unique cluster identifier")
    size: int = Field(..., description="Number of items in this cluster")
    top_keywords: List[str] = Field(..., description="Top keywords for this cluster")
    representatives: List[str] = Field(..., description="Representative item titles (up to 3)")


class ClusteringRequest(BaseModel):
    """Schema for clustering request."""
    items: Optional[List[EnrichedItem]] = Field(None, description="Items to cluster (if not provided, will fetch from enrichment)")
    k: Optional[int] = Field(None, description="Number of clusters (if not provided, will use heuristic)")


class ClusteringResponse(BaseModel):
    """Schema for clustering response."""
    clusters: List[ClusterSummary] = Field(..., description="Cluster summaries")
    items: List[EnrichedItem] = Field(..., description="Items with cluster_id assigned")
    processing_time_ms: Optional[float] = Field(None, description="Total processing time in milliseconds")
    algorithm_used: str = Field(..., description="Clustering algorithm used (KMeans or HDBSCAN)")


class EnhancedPipelineRunResponse(BaseModel):
    """Enhanced schema for full pipeline run response with clustering."""
    research_run_id: Optional[str] = Field(None, description="ID of the research run")
    total_items: int = Field(..., description="Total items processed")
    enriched_items: int = Field(..., description="Number of successfully enriched items")
    clustered_items: int = Field(..., description="Number of successfully clustered items")
    clusters: List[ClusterSummary] = Field(..., description="Cluster summaries")
    processing_time_ms: Optional[float] = Field(None, description="Total processing time in milliseconds")
    items: List[EnrichedItem] = Field(..., description="Enriched and clustered items")


# Phase 4 Ranking & Trending Schemas

class ProblemScoreBreakdown(BaseModel):
    """Schema for Problem Score breakdown components."""
    engagement_z: float = Field(..., description="Z-score of engagement (score + comments)")
    neg_sentiment: float = Field(..., description="Negative sentiment component (max(0, -sentiment))")
    is_question: int = Field(..., description="Question signal (0 or 1)")
    pain_markers: int = Field(..., description="Pain markers signal (0 or 1)")
    cluster_density: float = Field(..., description="Cluster density (size / DENSITY_NORM)")
    time_decay: float = Field(..., description="Time decay weight (0 to 1)")
    weights: Dict[str, float] = Field(..., description="Scoring weights used")


class RankedItem(EnrichedItem):
    """Schema for ranked item with Problem Score."""
    problem_score: float = Field(..., description="Overall Problem Score")
    why: ProblemScoreBreakdown = Field(..., description="Score breakdown explanation")


class RankingRequest(BaseModel):
    """Schema for ranking request."""
    items: Optional[List[EnrichedItem]] = Field(None, description="Items to rank (if not provided, will fetch from pipeline)")
    clusters: Optional[List[ClusterSummary]] = Field(None, description="Cluster summaries (if not provided, will fetch from pipeline)")
    days: int = Field(7, ge=1, le=30, description="Days of data to fetch if items not provided")
    limit: int = Field(200, ge=1, le=1000, description="Maximum items to process")
    top: int = Field(50, ge=1, le=500, description="Number of top items to return")


class RankingResponse(BaseModel):
    """Schema for ranking response."""
    top_items: List[RankedItem] = Field(..., description="Top ranked items")
    total_items: int = Field(..., description="Total items processed")
    processing_time_ms: Optional[float] = Field(None, description="Total processing time in milliseconds")


class ClusterTrend(BaseModel):
    """Schema for cluster trend information."""
    cluster_id: int = Field(..., description="Cluster identifier")
    trend: str = Field(..., description="Trend direction: rising, falling, or flat")
    last_count: int = Field(..., description="Count in most recent time bucket")
    sma_short: float = Field(..., description="Short-term moving average")
    sma_long: float = Field(..., description="Long-term moving average")
    series_tail: List[Tuple[int, int]] = Field(..., description="Last 10 time buckets (bucket_id, count)")
    top_keywords: Optional[List[str]] = Field(None, description="Top keywords for this cluster")
    representatives: Optional[List[str]] = Field(None, description="Representative item titles")
    size: Optional[int] = Field(None, description="Total cluster size")


class TrendRequest(BaseModel):
    """Schema for trend analysis request."""
    items: Optional[List[EnrichedItem]] = Field(None, description="Items to analyze (if not provided, will fetch from pipeline)")
    clusters: Optional[List[ClusterSummary]] = Field(None, description="Cluster summaries (if not provided, will fetch from pipeline)")
    days: int = Field(7, ge=1, le=30, description="Days of data to fetch if items not provided")
    limit: int = Field(200, ge=1, le=1000, description="Maximum items to process")


class TrendResponse(BaseModel):
    """Schema for trend analysis response."""
    trends: List[ClusterTrend] = Field(..., description="Cluster trend summaries")
    total_items: int = Field(..., description="Total items analyzed")
    processing_time_ms: Optional[float] = Field(None, description="Total processing time in milliseconds")


class FullPipelineResponse(BaseModel):
    """Schema for full pipeline response with ranking and trending."""
    research_run_id: Optional[str] = Field(None, description="ID of the research run")
    total_items: int = Field(..., description="Total items processed")
    enriched_items: int = Field(..., description="Number of successfully enriched items")
    clustered_items: int = Field(..., description="Number of successfully clustered items")
    clusters: List[ClusterSummary] = Field(..., description="Cluster summaries")
    ranked_top: List[RankedItem] = Field(..., description="Top ranked items")
    cluster_trends: List[ClusterTrend] = Field(..., description="Cluster trend summaries")
    processing_time_ms: Optional[float] = Field(None, description="Total processing time in milliseconds")
    items: List[EnrichedItem] = Field(..., description="All processed items")
