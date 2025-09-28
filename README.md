# Research Magnet

A multi-source research tool that discovers trending, unsolved problems suitable for digital products by analyzing Reddit, RSS feeds, and Hacker News.

## Features

- **Multi-Source Data Collection**: Reddit API, RSS/Atom feeds, Hacker News
- **Advanced NLP Pipeline**: Deduplication, sentiment analysis, keyword extraction, clustering
- **Intelligent Ranking**: Combines freshness, engagement, problem density, and cross-thread repetition
- **Multiple Export Formats**: JSON, CSV, and Markdown reports
- **Rate-Limited & Respectful**: Respects API limits and terms of service

## Quick Start

### 1. Environment Setup

```bash
# Clone and navigate to the project
cd research-magnet

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy environment template
cp env.sample .env
```

### 2. Get Reddit API Keys

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Choose "script" as the app type
4. Fill in the details:
   - Name: `research-magnet`
   - Description: `Multi-source research tool for discovering trending problems`
   - About URL: (leave blank)
   - Redirect URI: `http://localhost:8080` (required but not used)
5. Copy the client ID and secret to your `.env` file

### 3. Configure Feeds

Edit your `.env` file to add RSS feeds:

```bash
# Add your feeds (comma-separated)
RSS_FEEDS=https://feeds.feedburner.com/oreilly/radar,https://blog.ycombinator.com/feed/,https://feeds.feedburner.com/venturebeat/SZYF
```

### 4. Run the Application

```bash
# Start the FastAPI server
uvicorn app.main:app --reload
```

### 5. Test the Ingestion (Phase 1)

```bash
# Test all sources
curl 'http://localhost:8000/ingest/sources/status'

# Run ingestion for 7 days
curl 'http://localhost:8000/ingest/run?days=7'

# Run with custom filters
curl 'http://localhost:8000/ingest/run?days=3&min_score=20&min_comments=10'

# Test individual sources
curl 'http://localhost:8000/ingest/sources/reddit/test'
curl 'http://localhost:8000/ingest/sources/hackernews/test'
curl 'http://localhost:8000/ingest/sources/gnews/test'
```

### 6. Access the API

- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Ingestion API: http://localhost:8000/ingest/run
- Research Results: http://localhost:8000/research/results

## Database Setup

```bash
# Initialize database
alembic upgrade head

# Create a new migration (when you modify models)
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

## Project Structure

```
research-magnet/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── db.py                # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/             # API route handlers
│   ├── services/            # Business logic
│   ├── nlp/                 # NLP processing modules
│   ├── ingestion/           # Data source integrations
│   ├── rank/                # Ranking algorithms
│   ├── export/              # Export functionality
│   └── tests/               # Test suite
├── alembic/                 # Database migrations
├── exports/                 # Generated reports
├── pyproject.toml           # Project dependencies
├── env.sample               # Environment template
└── README.md
```

## Data Sources

### Reddit (Phase 1)
- **Subreddits**: r/startups, r/entrepreneur, r/technology, r/programming, r/webdev, r/MachineLearning, r/artificial, r/datascience, r/productivity, r/SaaS
- **API**: PRAW (Python Reddit API Wrapper)
- **Rate Limit**: 60 requests/minute
- **Data**: Hot/top posts, comments, upvotes, engagement metrics
- **Filters**: Score, comments, time range

### Hacker News (Phase 1)
- **API**: Algolia Search API
- **Queries**: startup, entrepreneur, productivity, SaaS, machine learning, AI, programming, web development, data science, technology
- **Rate Limit**: 100 requests/minute
- **Data**: Stories, comments, points, timestamps
- **Filters**: Points, comments, time range

### Google News (Phase 1)
- **API**: RSS feeds
- **Queries**: startup, entrepreneur, technology, AI, machine learning, programming, web development, SaaS, productivity, innovation
- **Rate Limit**: 30 requests/minute
- **Data**: Articles, publication dates, content, publisher info
- **Filters**: Time range, publisher authority

### RSS/Atom Feeds (Future)
- **Sources**: Tech blogs, news sites, Substack newsletters
- **Rate Limit**: 30 requests/minute
- **Data**: Articles, publication dates, content

## NLP Pipeline

1. **Deduplication**: MinHash/SimHash + FAISS embeddings for similarity detection
2. **Keyword Extraction**: KeyBERT and rake-nltk for keyphrase identification
3. **Sentiment Analysis**: VADER for sentiment scoring
4. **Clustering**: K-Means for grouping similar problems
5. **Ranking**: Multi-factor scoring system

## Ranking Algorithm

The ranking system combines multiple factors:

- **Freshness**: Recent content gets higher scores
- **Engagement**: High upvotes, comments, shares
- **Problem Density**: Frequency of complaint/frustration terms
- **Cross-Thread Repetition**: Problems mentioned across multiple sources
- **Source Authority**: Weighted by source credibility

## Phase 1 Response Format

The `/ingest/run` endpoint returns normalized data in this format:

```json
{
  "items": [
    {
      "source": "reddit|hackernews|gnews",
      "subsource": "r/startups | HN | GNews (query)",
      "title": "How I built my startup in 30 days",
      "url": "https://example.com/post",
      "created_utc": 1234567890,
      "score": 512,
      "num_comments": 88,
      "body": "This is the post content...",
      "raw": {
        "id": "abc123",
        "author": "username",
        "permalink": "https://reddit.com/r/startups/comments/abc123"
      }
    }
  ],
  "total_items": 150,
  "sources_used": ["reddit", "hackernews", "gnews"],
  "source_stats": {
    "reddit": {"status": "success", "count": 75, "duration_seconds": 2.5},
    "hackernews": {"status": "success", "count": 50, "duration_seconds": 1.8},
    "gnews": {"status": "success", "count": 25, "duration_seconds": 3.2}
  },
  "ingestion_time": "2024-01-15T10:30:00Z",
  "parameters": {
    "days": 7,
    "min_score": 10,
    "min_comments": 5
  }
}
```

## API Endpoints

### Core API
- `GET /health` - Health check
- `GET /research/results` - Get latest research results
- `POST /research/run` - Trigger new research run
- `GET /research/export/{format}` - Export results in specified format
- `GET /sources/status` - Check data source status

### Ingestion API (Phase 1)
- `GET /ingest/run` - Run data ingestion from all sources
- `GET /ingest/sources/status` - Check status of all data sources
- `GET /ingest/sources/reddit/test` - Test Reddit connection
- `GET /ingest/sources/hackernews/test` - Test Hacker News connection
- `GET /ingest/sources/gnews/test` - Test Google News connection
- `GET /ingest/health` - Ingestion service health check

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black app/

# Sort imports
isort app/

# Type checking
mypy app/
```

### Adding New Data Sources

1. Create a new module in `app/ingestion/`
2. Implement the `DataSource` interface
3. Add configuration to `app/config.py`
4. Register in `app/services/research_service.py`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For questions or issues, please open a GitHub issue or contact the development team.
