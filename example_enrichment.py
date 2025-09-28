#!/usr/bin/env python3
"""
Example script demonstrating the Phase 2 enrichment pipeline.
"""

import asyncio
import json
from typing import List, Dict, Any

from app.enrich.normalize import normalize_items
from app.enrich.sentiment import add_sentiment
from app.enrich.nlp import add_entities
from app.enrich.embed import add_embeddings
from app.utils.time_decay import add_time_decay


def create_sample_items() -> List[Dict[str, Any]]:
    """Create sample items for testing the enrichment pipeline."""
    return [
        {
            "source": "reddit",
            "title": "How to stop sugar cravings in 14 days?",
            "body": "I'm struggling with sugar cravings and need help! I've tried everything but can't seem to break the habit. Any advice?",
            "url": "https://reddit.com/r/health/comments/example",
            "created_utc": 1695000000,  # Recent timestamp
            "score": 120,
            "num_comments": 45
        },
        {
            "source": "hackernews",
            "title": "Struggling to get more matches on dating apps",
            "body": "I've been using Tinder and Hinge for months but barely get any matches. My profile looks good but something isn't working. Help!",
            "url": "https://news.ycombinator.com/item?id=example",
            "created_utc": 1694900000,  # Older timestamp
            "score": 85,
            "num_comments": 23
        },
        {
            "source": "rss",
            "title": "Side hustle income ideas for 2024",
            "body": "Looking to make an extra $5k per month through side hustles. What are the best opportunities right now?",
            "url": "https://example.com/side-hustle-ideas",
            "created_utc": 1694800000,  # Even older timestamp
            "score": 200,
            "num_comments": 67
        }
    ]


async def run_enrichment_pipeline(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run the complete enrichment pipeline on items."""
    print(f"Starting enrichment pipeline for {len(items)} items...")
    
    # Step 1: Normalize and derive signals
    print("Step 1: Normalizing text and deriving signals...")
    items = normalize_items(items)
    
    # Step 2: Add sentiment analysis
    print("Step 2: Adding sentiment analysis...")
    items = add_sentiment(items)
    
    # Step 3: Extract entities
    print("Step 3: Extracting entities...")
    items = add_entities(items)
    
    # Step 4: Generate embeddings
    print("Step 4: Generating embeddings...")
    items = add_embeddings(items)
    
    # Step 5: Add time decay weights
    print("Step 5: Adding time decay weights...")
    items = add_time_decay(items, half_life_hours=72)
    
    print("Enrichment pipeline completed!")
    return items


def print_enrichment_results(items: List[Dict[str, Any]]):
    """Print the enrichment results in a readable format."""
    for i, item in enumerate(items, 1):
        print(f"\n--- Item {i} ---")
        print(f"Source: {item.get('source', 'unknown')}")
        print(f"Title: {item.get('title', 'N/A')}")
        print(f"Body: {item.get('body', 'N/A')[:100]}...")
        
        # Signals
        signals = item.get('signals', {})
        print(f"Signals:")
        print(f"  - Is Question: {signals.get('is_question', 0)}")
        print(f"  - Pain Markers: {signals.get('pain_markers', 0)}")
        print(f"  - How-to Markers: {signals.get('how_to_markers', 0)}")
        print(f"  - Has Numbers: {signals.get('has_numbers', 0)}")
        print(f"  - Has Measurable Goal: {signals.get('has_measurable_goal', 0)}")
        print(f"  - Domain Tags: {signals.get('domain_tags', [])}")
        
        # Sentiment
        sentiment = item.get('sentiment')
        if sentiment is not None:
            print(f"Sentiment: {sentiment:.3f}")
        
        # Entities
        entities = item.get('entities', [])
        if entities:
            print(f"Entities: {[(e['text'], e['label']) for e in entities]}")
        
        # Embedding info
        embedding = item.get('embedding')
        if embedding:
            print(f"Embedding: {len(embedding)} dimensions")
        
        # Time decay
        time_decay = item.get('time_decay_weight')
        if time_decay is not None:
            print(f"Time Decay Weight: {time_decay:.3f}")


async def main():
    """Main function to run the example."""
    print("Research Magnet Phase 2 - Enrichment Pipeline Example")
    print("=" * 60)
    
    # Create sample items
    items = create_sample_items()
    print(f"Created {len(items)} sample items")
    
    # Run enrichment pipeline
    enriched_items = await run_enrichment_pipeline(items)
    
    # Print results
    print_enrichment_results(enriched_items)
    
    # Save results to JSON file
    output_file = "enrichment_results.json"
    with open(output_file, 'w') as f:
        # Convert to JSON-serializable format
        json_items = []
        for item in enriched_items:
            json_item = item.copy()
            # Convert any non-serializable objects
            if 'signals' in json_item and isinstance(json_item['signals'], dict):
                json_item['signals'] = dict(json_item['signals'])
            json_items.append(json_item)
        
        json.dump(json_items, f, indent=2, default=str)
    
    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
