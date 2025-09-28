#!/usr/bin/env python3
"""
Example script demonstrating Phase 4 functionality:
- Problem Score computation with interpretable breakdown
- Cluster trend detection
- Full pipeline with ranking and trending
"""

import asyncio
import json
from datetime import datetime
from app.services.ingestion_service import IngestionService
from app.enrich.normalize import normalize_items
from app.enrich.sentiment import add_sentiment
from app.enrich.nlp import add_entities
from app.enrich.embed import add_embeddings
from app.utils.time_decay import add_time_decay
from app.analyze.cluster import cluster_items
from app.utils.scoring import rank_items
from app.analyze.trend import cluster_trends


async def run_phase4_example():
    """Run a complete Phase 4 example."""
    print("🚀 Research Magnet Phase 4 Example")
    print("=" * 50)
    
    # Step 1: Data Ingestion
    print("\n📥 Step 1: Data Ingestion")
    ingestion_service = IngestionService()
    ingestion_result = await ingestion_service.run_ingestion(
        days=3,  # Last 3 days
        min_score=5,
        min_comments=2
    )
    items = ingestion_result["items"]
    print(f"✅ Collected {len(items)} items")
    
    if not items:
        print("❌ No items found. Try adjusting the criteria or check your API keys.")
        return
    
    # Step 2: Enrichment
    print("\n🔍 Step 2: Enrichment Pipeline")
    items = normalize_items(items)
    items = add_sentiment(items)
    items = add_entities(items)
    items = add_embeddings(items)
    items = add_time_decay(items)
    print(f"✅ Enriched {len(items)} items")
    
    # Step 3: Clustering
    print("\n🎯 Step 3: Clustering")
    from app.schemas import EnrichedItem
    enriched_items = [EnrichedItem(**item) for item in items]
    clustering_result = cluster_items(items=enriched_items)
    clustered_items = clustering_result["items"]
    clusters = clustering_result["clusters"]
    print(f"✅ Created {len(clusters)} clusters")
    
    # Step 4: Ranking
    print("\n📊 Step 4: Problem Score Ranking")
    clustered_data = {
        "items": [item.dict() for item in clustered_items],
        "clusters": [cluster.dict() for cluster in clusters]
    }
    ranked_items = rank_items(clustered_data, top=10)
    print(f"✅ Ranked top {len(ranked_items)} items")
    
    # Display top ranked items
    print("\n🏆 Top 5 Problem Items:")
    for i, item in enumerate(ranked_items[:5], 1):
        print(f"\n{i}. {item['title'][:80]}...")
        print(f"   Problem Score: {item['problem_score']:.3f}")
        print(f"   Source: {item['source']} | Score: {item.get('score', 0)} | Comments: {item.get('num_comments', 0)}")
        print(f"   Why it ranks high:")
        why = item['why']
        print(f"     - Engagement Z-score: {why['engagement_z']:.2f}")
        print(f"     - Negative sentiment: {why['neg_sentiment']:.2f}")
        print(f"     - Is question: {why['is_question']}")
        print(f"     - Pain markers: {why['pain_markers']}")
        print(f"     - Cluster density: {why['cluster_density']:.2f}")
        print(f"     - Time decay: {why['time_decay']:.2f}")
    
    # Step 5: Trend Analysis
    print("\n📈 Step 5: Cluster Trend Analysis")
    trend_summaries = cluster_trends(
        [item.dict() for item in clustered_items],
        [cluster.dict() for cluster in clusters]
    )
    print(f"✅ Analyzed trends for {len(trend_summaries)} clusters")
    
    # Display trending clusters
    print("\n🔥 Trending Clusters:")
    for trend in trend_summaries[:5]:
        print(f"\nCluster {trend['cluster_id']}: {trend['trend'].upper()}")
        print(f"  Last count: {trend['last_count']}")
        print(f"  Short-term avg: {trend['sma_short']:.2f}")
        print(f"  Long-term avg: {trend['sma_long']:.2f}")
        if trend.get('top_keywords'):
            print(f"  Keywords: {', '.join(trend['top_keywords'][:3])}")
        if trend.get('representatives'):
            print(f"  Example: {trend['representatives'][0][:60]}...")
    
    # Step 6: Summary Statistics
    print("\n📋 Summary Statistics")
    print(f"Total items processed: {len(items)}")
    print(f"Items with embeddings: {len([item for item in clustered_items if item.embedding])}")
    print(f"Clustered items: {len([item for item in clustered_items if item.cluster_id is not None and item.cluster_id >= 0])}")
    print(f"Rising trends: {len([t for t in trend_summaries if t['trend'] == 'rising'])}")
    print(f"Falling trends: {len([t for t in trend_summaries if t['trend'] == 'falling'])}")
    print(f"Flat trends: {len([t for t in trend_summaries if t['trend'] == 'flat'])}")
    
    # Save results to file
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_items": len(items),
        "clusters": len(clusters),
        "top_ranked": ranked_items[:10],
        "trends": trend_summaries,
        "summary": {
            "rising_trends": len([t for t in trend_summaries if t['trend'] == 'rising']),
            "falling_trends": len([t for t in trend_summaries if t['trend'] == 'falling']),
            "flat_trends": len([t for t in trend_summaries if t['trend'] == 'flat'])
        }
    }
    
    with open("phase4_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to phase4_results.json")
    print("\n🎉 Phase 4 example completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_phase4_example())
