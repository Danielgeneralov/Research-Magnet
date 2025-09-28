"""
FastAPI main application for Research Magnet.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

from app.config import settings
from app.routers import health, research, sources, export, ingestion
from app.db import engine
from app.models import Base

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Research Magnet",
    description="Multi-source research tool that discovers trending, unsolved problems suitable for digital products",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(research.router, prefix="/research", tags=["research"])
app.include_router(sources.router, prefix="/sources", tags=["sources"])
app.include_router(export.router, prefix="/export", tags=["export"])
app.include_router(ingestion.router, prefix="/ingest", tags=["ingestion"])


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Research Magnet API...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    # Initialize data sources
    try:
        from app.services.source_service import SourceService
        from app.db import SessionLocal
        db = SessionLocal()
        try:
            source_service = SourceService(db)
            await source_service.initialize_default_sources()
            logger.info("Default data sources initialized")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to initialize default sources: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down Research Magnet API...")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
