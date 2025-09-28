# Research Magnet Phase 2 - NLP Enrichment Pipeline

This document describes the Phase 2 implementation of Research Magnet, which adds comprehensive NLP enrichment capabilities to the existing data ingestion pipeline.

## 🎯 Overview

Phase 2 extends the MVP with lightweight NLP signals, sentiment analysis, entity extraction, and embeddings to normalize, clean, and enrich each ingested item. The implementation is designed to be idempotent, performant, and production-ready.

## 🏗️ Architecture

### New Components

- **`app/enrich/`** - Core enrichment modules
  - `normalize.py` - Text cleaning and signal detection
  - `sentiment.py` - VADER sentiment analysis
  - `nlp.py` - spaCy NER entity extraction
  - `embed.py` - Sentence transformer embeddings

- **`app/utils/`** - Utility modules
  - `logging.py` - Enrichment-specific logging
  - `time_decay.py` - Freshness scoring

- **`app/routers/enrichment.py`** - New API endpoints
- **`app/schemas.py`** - Extended with enrichment models

### Data Flow

```
Raw Items → Normalize → Sentiment → Entities → Embeddings → Time Decay → Enriched Items
```

## 🚀 Features

### Text Normalization
- Remove URLs, markdown links, and HTML tags
- Collapse excessive whitespace
- Preserve emojis and punctuation
- Clip text to 5000 characters

### Signal Detection
- **is_question**: Detects question patterns
- **pain_markers**: Identifies frustration/complaint indicators
- **how_to_markers**: Detects instructional content
- **has_numbers**: Checks for numeric content
- **has_measurable_goal**: Identifies quantifiable objectives
- **domain_tags**: Categorizes content by domain (health, money, dating, career, productivity)

### Sentiment Analysis
- VADER sentiment scoring (-1 to 1)
- Handles social media text effectively
- Processes combined title + body content

### Entity Extraction
- spaCy NER with simplified labels
- Extracts: PERSON, ORG, LOC, PRODUCT, TIME, MONEY
- Handles text length limits gracefully

### Text Embeddings
- Sentence transformer model (all-MiniLM-L6-v2)
- 384-dimensional vectors
- Batch processing for performance
- Fallback handling for failures

### Time Decay Scoring
- Configurable half-life (default 72 hours)
- Exponential decay formula
- Handles missing timestamps gracefully

## 📊 API Endpoints

### POST /enrich/run
Enrich items with NLP features.

**Request:**
```json
{
  "items": [
    {
      "source": "reddit",
      "title": "How to stop sugar cravings in 14 days?",
      "body": "I'm struggling with sugar cravings...",
      "created_utc": 1695000000,
      "score": 120,
      "num_comments": 45
    }
  ],
  "days": 7,
  "limit": 200,
  "half_life_hours": 72
}
```

**Response:**
```json
{
  "count": 1,
  "items": [
    {
      "source": "reddit",
      "title": "How to stop sugar cravings in 14 days?",
      "body": "I'm struggling with sugar cravings...",
      "sentiment": -0.05,
      "entities": [{"text": "14 days", "label": "TIME"}],
      "embedding": [0.1, 0.2, ...], // 384 dimensions
      "signals": {
        "is_question": 1,
        "pain_markers": 1,
        "how_to_markers": 1,
        "has_numbers": 1,
        "has_measurable_goal": 1,
        "domain_tags": ["health"]
      },
      "time_decay_weight": 0.92,
      "created_utc": 1695000000,
      "score": 120,
      "num_comments": 45
    }
  ],
  "processing_time_ms": 1250.5
}
```

### POST /enrich/pipeline/run
Run complete pipeline: ingestion + enrichment.

**Request:**
```json
{
  "days": 7,
  "limit": 200,
  "half_life_hours": 72
}
```

**Response:**
```json
{
  "research_run_id": 123,
  "total_items": 150,
  "enriched_items": 148,
  "processing_time_ms": 5000.2,
  "items": [...] // Same as /enrich/run response
}
```

## 🛠️ Installation & Setup

### Prerequisites
```bash
# Install Python dependencies
pip install -e .

# Install spaCy model
python -m spacy download en_core_web_sm
```

### Environment Variables
```bash
# Optional configuration
HALF_LIFE_HOURS=72
EMBED_MODEL=all-MiniLM-L6-v2
SPACY_MODEL=en_core_web_sm
```

### Running the Server
```bash
# Start the development server
python -m app.cli start

# Or run directly
python -m app.main
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest

# Run enrichment tests specifically
pytest app/tests/test_enrich.py -v

# Run with coverage
pytest --cov=app.enrich app/tests/test_enrich.py
```

### Example Usage
```bash
# Run the example script
python example_enrichment.py
```

## 📈 Performance

### Benchmarks
- **Text Normalization**: ~1ms per item
- **Sentiment Analysis**: ~5ms per item
- **Entity Extraction**: ~10ms per item
- **Embedding Generation**: ~50ms per item (with batching)
- **Time Decay**: ~0.1ms per item

### Optimization Features
- Lazy loading of ML models (singleton pattern)
- Batch processing for embeddings
- Text length limits to prevent memory issues
- Graceful error handling and fallbacks
- Comprehensive logging for monitoring

## 🔧 Configuration

### Domain Tag Rules
The system uses configurable keyword mappings for domain detection:

```python
DOMAIN_RULES = {
    "health": ["diet", "craving", "calorie", "workout", ...],
    "money": ["side hustle", "income", "freelance", ...],
    "dating": ["match", "tinder", "hinge", "conversation", ...],
    "career": ["resume", "interview", "faang", "portfolio", ...],
    "productivity": ["deep work", "focus", "pomodoro", ...]
}
```

### Signal Detection Patterns
- **Pain Markers**: "struggling", "stuck", "can't", "frustrated", etc.
- **How-to Markers**: "how to", "best way to", "step by step", etc.
- **Measurable Goals**: Regex patterns for quantities, timeframes, etc.

## 🐛 Error Handling

### Graceful Degradation
- Missing spaCy model: Returns empty entities with warning
- Embedding failures: Returns zero vectors
- Sentiment failures: Returns neutral score (0.0)
- Text processing errors: Logs warning and continues

### Logging
- Structured logging with timing information
- Step-by-step progress tracking
- Error context and debugging information
- Performance metrics

## 🔮 Future Enhancements

### Planned Features
- Custom domain tag rules via configuration
- Advanced clustering algorithms
- Real-time processing capabilities
- Caching for repeated items
- A/B testing for signal detection

### Performance Improvements
- Redis caching for embeddings
- Async processing for large batches
- Model quantization for faster inference
- GPU acceleration support

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contributing

### Code Standards
- Follow existing code style (Black formatting)
- Add type hints for all functions
- Include comprehensive tests
- Update documentation for new features

### Testing Requirements
- Unit tests for all functions
- Integration tests for API endpoints
- Performance tests for large datasets
- Error handling tests

## 📄 License

This project is part of Research Magnet and follows the same license terms.

---

*For questions or issues, please refer to the main project documentation or create an issue in the repository.*
