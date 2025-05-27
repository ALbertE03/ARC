#!/usr/bin/env python
"""
Test script for the Enhanced Author Matcher
============================================

This script allows you to test and benchmark the enhanced author matcher
with various configurations and sample data.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from models.enhanced_author_matcher import EnhancedAuthorMatcher, PerformanceMetrics
from models.author_matcher import SmartAuthorMatcher
from utils.data_processing import load_data, build_author_work_map

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_real_data(data_dir="data", limit=None):
    """Load real author and works data from OpenAlex files."""
    authors_file = os.path.join(data_dir, "openalex_authors_complete.json")
    works_file = os.path.join(data_dir, "openalex_data.json")
    
    if not os.path.exists(authors_file):
        logger.error(f"❌ Authors file not found: {authors_file}")
        return None, None
        
    if not os.path.exists(works_file):
        logger.error(f"❌ Works file not found: {works_file}")
        return None, None
    
    logger.info("📚 Loading real OpenAlex data...")
    authors_data, works_data = load_data(authors_file, works_file)
    
    if not authors_data or not works_data:
        logger.error("❌ Failed to load data")
        return None, None
    
    # Apply limit if specified
    if limit and len(authors_data) > limit:
        logger.info(f"📊 Limiting to first {limit} authors for testing...")
        authors_data = dict(list(authors_data.items())[:limit])
        
        # Filter works to only include those by selected authors
        selected_author_ids = set(authors_data.keys())
        author_work_map = build_author_work_map(works_data)
        
        # Keep only works that have at least one selected author
        filtered_works = {}
        for work_id, work in works_data.items():
            authorships = work.get("authorships", [])
            if any(auth.get("author", {}).get("id", "").split("/")[-1] in selected_author_ids 
                   for auth in authorships):
                filtered_works[work_id] = work
        
        works_data = filtered_works
        logger.info(f"📄 Filtered to {len(works_data)} works by selected authors")
    
    logger.info(f"✅ Real data loaded: {len(authors_data)} authors, {len(works_data)} works")
    return authors_data, works_data


def test_enhanced_matcher(authors_data, works_data, config=None):
    """Test the enhanced matcher with given data and configuration."""
    logger.info("🚀 Testing Enhanced Author Matcher...")
    
    # Default configuration
    default_config = {
        "similarity_threshold": 0.85,
        "use_semantic_similarity": True,
        "use_phonetic_matching": True,
        "enable_caching": True,
        "batch_size": 500
    }
    
    if config:
        default_config.update(config)
    
    # Initialize matcher
    matcher = EnhancedAuthorMatcher(**default_config)
    
    # Build author-work mapping
    author_work_map = build_author_work_map(works_data)
    
    # Extract features
    logger.info("📝 Extracting enhanced features...")
    authors_features = {}
    for author_id, author_data in authors_data.items():
        authors_features[author_id] = matcher.extract_features_enhanced(
            author_id, author_data, author_work_map
        )
    
    # Find candidates
    logger.info("🔍 Finding consolidation candidates...")
    graph = matcher.find_candidates_optimized(authors_features, author_work_map)
    
    # Print results
    logger.info(f"📊 Results: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    # Export metrics
    metrics_file = "test_enhanced_matcher_metrics.json"
    matcher.export_metrics(metrics_file)
    
    return matcher, graph


def benchmark_matchers(authors_data, works_data):
    """Benchmark enhanced vs traditional matcher."""
    logger.info("🏁 Running matcher benchmark...")
    
    # Build author-work mapping
    author_work_map = build_author_work_map(works_data)
    
    # Test traditional matcher
    logger.info("🔄 Testing traditional matcher...")
    traditional_matcher = SmartAuthorMatcher(similarity_threshold=0.90)
    
    # Extract traditional features
    traditional_features = {}
    for author_id, author_data in authors_data.items():
        traditional_features[author_id] = traditional_matcher.extract_features(
            author_id, author_data, author_work_map
        )
    
    # Test enhanced matcher with benchmarking
    logger.info("🚀 Testing enhanced matcher...")
    enhanced_matcher = EnhancedAuthorMatcher(
        similarity_threshold=0.85,
        use_semantic_similarity=True,
        use_phonetic_matching=True
    )
    
    enhanced_features = {}
    for author_id, author_data in authors_data.items():
        enhanced_features[author_id] = enhanced_matcher.extract_features_enhanced(
            author_id, author_data, author_work_map
        )
    
    # Run benchmark
    results = enhanced_matcher.benchmark_against_baseline(
        enhanced_features, author_work_map, traditional_matcher
    )
    
    # Save results
    with open("benchmark_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("📊 Benchmark completed! Results saved to benchmark_results.json")
    return results


def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Enhanced Author Matcher')
    parser.add_argument('--mode', choices=['test', 'benchmark'], default='test',
                       help='Test mode (default: test)')
    parser.add_argument('--limit', type=int, default=500,
                       help='Limit number of authors to process (default: 500)')
    parser.add_argument('--data-dir', type=str, default='data',
                       help='Data directory path')
    
    args = parser.parse_args()
    
    # Load real data
    authors_data, works_data = load_real_data(args.data_dir, args.limit)
    
    if authors_data is None or works_data is None:
        logger.error("❌ Failed to load data. Please ensure OpenAlex data files are available.")
        return
    
    if args.mode == 'test':
        # Test enhanced matcher with real data
        logger.info("🚀 Testing Enhanced Author Matcher with real OpenAlex data...")
        matcher, graph = test_enhanced_matcher(authors_data, works_data)
        
        logger.info("✅ Real data test completed!")
        
    elif args.mode == 'benchmark':
        # Benchmark mode with real data
        logger.info("🏁 Running benchmark with real OpenAlex data...")
        results = benchmark_matchers(authors_data, works_data)
        
        # Print summary
        enhanced = results.get('enhanced', {})
        baseline = results.get('baseline', {})
        comparison = results.get('comparison', {})
        
        if enhanced and baseline:
            logger.info(f"\n📈 BENCHMARK SUMMARY:")
            logger.info(f"   Enhanced: {enhanced.get('processing_time', 0):.2f}s, {enhanced.get('edges_found', 0)} edges")
            logger.info(f"   Traditional: {baseline.get('processing_time', 0):.2f}s, {baseline.get('edges_found', 0)} edges")
            
            if comparison:
                logger.info(f"   Speedup: {comparison.get('speedup_factor', 0):.2f}x")
                logger.info(f"   Edge ratio: {comparison.get('edge_ratio', 0):.2f}x")
        
        logger.info("✅ Benchmark completed!")


if __name__ == "__main__":
    main()
