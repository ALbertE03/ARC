#!/usr/bin/env python
"""
Enhanced Author Resolution and Consolidation (ARC) System
=========================================================

This script performs author resolution and consolidation using enhanced 
algorithms with benchmarking capabilities.

Usage:
    python create_graph_author_to_articles.py [options]

Options:
    --matcher {traditional,enhanced}  Choose matcher type (default: enhanced)
    --benchmark                       Run benchmark comparison
    --threshold FLOAT                 Similarity threshold (default: 0.85)
    --limit INT                      Limit number of authors for testing
    --export-results                 Export detailed results and metrics
"""

import os
import sys
import logging
import networkx as nx
import time
import json
from tqdm import tqdm

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from models.author_matcher import SmartAuthorMatcher
from models.enhanced_author_matcher import EnhancedAuthorMatcher
from utils.data_processing import (
    load_data,
    build_author_work_map,
    print_consolidation_stats,
    build_full_graph,
    consolidate_authors
)
from db.db_operations import save_to_neo4j

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("author_consolidation.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def consolidate_authors_enhanced(authors_data, author_work_map, threshold=0.85, limit=None):
    """Enhanced consolidation method using the new EnhancedAuthorMatcher."""
    logger.info("\n🚀 Starting Enhanced Author Consolidation")
    logger.info("=" * 70)
    
    # Apply limit if specified
    if limit and len(authors_data) > limit:
        logger.info(f"📊 Limiting to first {limit} authors for testing...")
        authors_data = dict(list(authors_data.items())[:limit])
    
    start_time = time.time()
    
    # Initialize enhanced matcher with optimized settings
    matcher = EnhancedAuthorMatcher(
        similarity_threshold=threshold,
        batch_size=1000,
        use_semantic_similarity=True,
        use_phonetic_matching=True,
        enable_caching=True
    )
    
    # Extract enhanced features
    logger.info("📝 Extracting enhanced features from authors...")
    enhanced_features = {}
    for author_id, author_data in tqdm(authors_data.items(), desc="Extracting features"):
        enhanced_features[author_id] = matcher.extract_features_enhanced(
            author_id, author_data, author_work_map
        )
    
    # Find consolidation candidates
    logger.info("🔍 Finding consolidation candidates...")
    G = matcher.find_candidates_optimized(enhanced_features, author_work_map)
    
    # Perform consolidation
    logger.info("🔍 Identifying connected components...")
    components = list(nx.connected_components(G))
    logger.info(f"   Found {len(components)} connected components")

    logger.info("🔄 Consolidating authors...")
    consolidated, component_stats = consolidate_authors(G, authors_data, components)
    
    processing_time = time.time() - start_time
    
    # Print consolidation stats
    print_consolidation_stats(consolidated, authors_data, component_stats, G)
    
    # Export metrics
    metrics_file = "enhanced_consolidation_metrics.json"
    matcher.export_metrics(metrics_file)
    logger.info(f"📊 Metrics exported to: {metrics_file}")
    
    logger.info(f"\n✅ Enhanced consolidation completed in {processing_time:.2f} seconds")
    logger.info(f"🔗 Found {G.number_of_edges()} potential consolidations")
    logger.info(f"👥 Processed {G.number_of_nodes()} authors")
    
    return consolidated, G, matcher


def consolidate_authors_traditional(authors_data, author_work_map, threshold=0.95, limit=None):
    """Traditional consolidation method using SmartAuthorMatcher."""
    logger.info("\n🔍 Starting Traditional Rule-Based Author Consolidation")
    logger.info("=" * 70)
    
    # Apply limit if specified
    if limit and len(authors_data) > limit:
        logger.info(f"📊 Limiting to first {limit} authors for testing...")
        authors_data = dict(list(authors_data.items())[:limit])
    
    start_time = time.time()
    
    # Initialize traditional matcher
    matcher = SmartAuthorMatcher(similarity_threshold=threshold)

    logger.info("📝 Extracting author features...")
    authors_features = {}
    for author_id, author_data in tqdm(authors_data.items(), desc="Extracting author features"):
        authors_features[author_id] = matcher.extract_features(
            author_id, author_data, author_work_map
        )

    # Find candidates using traditional approach
    logger.info("🔗 Finding consolidation candidates...")
    G = matcher.find_candidates(authors_features, author_work_map)

    logger.info("🔍 Identifying connected components...")
    components = list(nx.connected_components(G))
    logger.info(f"   Found {len(components)} connected components")

    # Perform consolidation
    logger.info("🔄 Consolidating authors...")
    consolidated, component_stats = consolidate_authors(G, authors_data, components)
    
    processing_time = time.time() - start_time

    print_consolidation_stats(consolidated, authors_data, component_stats, G)
    
    logger.info(f"✅ Traditional consolidation completed in {processing_time:.2f} seconds")

    return consolidated, G


def run_consolidation_benchmark(authors_data, author_work_map, limit=None):
    """Run benchmark comparing traditional vs enhanced matchers."""
    logger.info("\n🏁 Running Consolidation Benchmark")
    logger.info("=" * 70)
    
    # Apply limit if specified
    if limit and len(authors_data) > limit:
        logger.info(f"📊 Limiting to {limit} authors for benchmarking...")
        authors_data = dict(list(authors_data.items())[:limit])
    
    # Initialize matchers
    traditional_matcher = SmartAuthorMatcher(similarity_threshold=0.90)
    enhanced_matcher = EnhancedAuthorMatcher(
        similarity_threshold=0.85,
        use_semantic_similarity=True,
        use_phonetic_matching=True,
        enable_caching=True
    )
    
    # Extract traditional features
    logger.info("📝 Extracting traditional features...")
    traditional_features = {}
    for author_id, author_data in tqdm(authors_data.items(), desc="Traditional features"):
        traditional_features[author_id] = traditional_matcher.extract_features(
            author_id, author_data, author_work_map
        )
    
    # Extract enhanced features
    logger.info("📝 Extracting enhanced features...")
    enhanced_features = {}
    for author_id, author_data in tqdm(authors_data.items(), desc="Enhanced features"):
        enhanced_features[author_id] = enhanced_matcher.extract_features_enhanced(
            author_id, author_data, author_work_map
        )
    
    logger.info("🔄 Running benchmarks...")
    
    # Run enhanced matcher with benchmarking
    benchmark_results = enhanced_matcher.benchmark_against_baseline(
        enhanced_features, author_work_map, traditional_matcher
    )
    
    # Display results
    logger.info("\n📊 BENCHMARK RESULTS")
    logger.info("=" * 50)
    
    enhanced_results = benchmark_results.get('enhanced', {})
    baseline_results = benchmark_results.get('baseline', {})
    comparison = benchmark_results.get('comparison', {})
    
    logger.info(f"🚀 Enhanced Matcher:")
    logger.info(f"   ⏱️  Time: {enhanced_results.get('processing_time', 0):.2f} seconds")
    logger.info(f"   🔗 Edges: {enhanced_results.get('edges_found', 0):,}")
    logger.info(f"   ⚡ Speed: {enhanced_results.get('authors_per_second', 0):.1f} authors/sec")
    
    if baseline_results:
        logger.info(f"\n🔍 Traditional Matcher:")
        logger.info(f"   ⏱️  Time: {baseline_results.get('processing_time', 0):.2f} seconds")
        logger.info(f"   🔗 Edges: {baseline_results.get('edges_found', 0):,}")
        logger.info(f"   ⚡ Speed: {baseline_results.get('authors_per_second', 0):.1f} authors/sec")
        
        if comparison:
            logger.info(f"\n📈 Performance Improvement:")
            logger.info(f"   🚀 Speedup: {comparison.get('speedup_factor', 0):.2f}x faster")
            logger.info(f"   🔗 Edge ratio: {comparison.get('edge_ratio', 0):.2f}x")
            logger.info(f"   ⏱️  Time saved: {comparison.get('time_improvement_pct', 0):.1f}%")
    
    # Export benchmark results
    benchmark_file = "main_consolidation_benchmark.json"
    try:
        with open(benchmark_file, 'w', encoding='utf-8') as f:
            json.dump(benchmark_results, f, indent=2, ensure_ascii=False)
        logger.info(f"📊 Benchmark results exported to: {benchmark_file}")
    except Exception as e:
        logger.error(f"❌ Failed to export benchmark results: {e}")
    
    return benchmark_results


def export_detailed_results(consolidated_authors, author_graph, authors_data, works_data, method_name):
    """Export detailed results and analysis."""
    logger.info("📤 Exporting detailed results...")
    
    # Calculate detailed statistics
    original_count = len(authors_data)
    consolidated_count = len(consolidated_authors)
    reduction_count = original_count - consolidated_count
    reduction_percentage = (reduction_count / original_count * 100) if original_count > 0 else 0
    
    # Graph statistics
    graph_stats = {
        "total_nodes": author_graph.number_of_nodes(),
        "total_edges": author_graph.number_of_edges(),
        "edge_density": (2 * author_graph.number_of_edges()) / (author_graph.number_of_nodes() * (author_graph.number_of_nodes() - 1)) if author_graph.number_of_nodes() > 1 else 0,
        "connected_components": nx.number_connected_components(author_graph)
    }
    
    # Component size analysis
    components = list(nx.connected_components(author_graph))
    component_sizes = [len(comp) for comp in components]
    component_analysis = {
        "total_components": len(components),
        "largest_component": max(component_sizes) if component_sizes else 0,
        "average_component_size": sum(component_sizes) / len(component_sizes) if component_sizes else 0,
        "single_author_components": sum(1 for size in component_sizes if size == 1)
    }
    
    # Prepare results summary
    results_summary = {
        "method": method_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_stats": {
            "original_authors": original_count,
            "consolidated_authors": consolidated_count,
            "reduction_count": reduction_count,
            "reduction_percentage": reduction_percentage,
            "total_works": len(works_data)
        },
        "graph_statistics": graph_stats,
        "component_analysis": component_analysis
    }
    
    # Export to JSON
    results_file = f"consolidation_results_{method_name.lower()}_{int(time.time())}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📊 Detailed results exported to: {results_file}")
    return results_file


def main():
    """Main function to execute the author-article graph creation workflow."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enhanced Author Resolution and Consolidation System')
    parser.add_argument('--matcher', choices=['traditional', 'enhanced'], default='enhanced',
                       help='Choose matcher type (default: enhanced)')
    parser.add_argument('--benchmark', action='store_true',
                       help='Run benchmark comparison between matchers')
    parser.add_argument('--threshold', type=float, default=0.85,
                       help='Similarity threshold for matching (default: 0.85)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of authors for testing')
    parser.add_argument('--export-results', action='store_true',
                       help='Export detailed results and metrics')
    parser.add_argument('--skip-neo4j', action='store_true',
                       help='Skip saving to Neo4j database')
    
    # Handle case where script is called directly (no args)
    try:
        args = parser.parse_args()
    except:
        # If parsing fails (like in Jupyter), use defaults
        class DefaultArgs:
            matcher = 'enhanced'
            benchmark = False
            threshold = 0.85
            limit = None
            export_results = False
            skip_neo4j = False
        args = DefaultArgs()
    
    use_enhanced = (args.matcher == 'enhanced')
    
    logger.info("🚀 Starting Enhanced Author Resolution and Consolidation (ARC) System")
    logger.info("=" * 80)
    
    # System information
    import platform
    logger.info(f"🖥️ System: {platform.system()} {platform.release()}")
    logger.info(f"🐍 Python: {platform.python_version()}")
    
    method_name = "Enhanced" if use_enhanced else "Traditional"
    logger.info(f"🎯 Method: {method_name} Author Matcher")
    logger.info(f"🎚️ Threshold: {args.threshold}")
    
    if args.limit:
        logger.info(f"📊 Author limit: {args.limit:,}")
    
    if args.benchmark:
        logger.info("🏁 Benchmark mode enabled")
    
    if args.export_results:
        logger.info("📤 Detailed results export enabled")
    
    try:
        # Load data files
        authors_file = os.path.join(project_root, "data/openalex_authors_complete.json")
        works_file = os.path.join(project_root, "data/openalex_data.json")
        
        # Verify files exist
        if not os.path.exists(authors_file):
            logger.error(f"❌ Authors file not found: {authors_file}")
            logger.error("Please ensure the data files are available")
            sys.exit(1)
        
        if not os.path.exists(works_file):
            logger.error(f"❌ Works file not found: {works_file}")
            logger.error("Please ensure the data files are available")
            sys.exit(1)

        # Load data
        logger.info("📚 Loading OpenAlex data...")
        authors_data, works_data = load_data(authors_file, works_file)
        author_work_map = build_author_work_map(works_data)
        
        logger.info(f"📊 Loaded {len(authors_data):,} authors and {len(works_data):,} works")
        
        # Data quality summary
        total_authorship_records = sum(len(works) for works in author_work_map.values())
        avg_works_per_author = total_authorship_records / len(authors_data) if authors_data else 0
        avg_authors_per_work = sum(len(work.get('authorships', [])) for work in works_data.values()) / len(works_data) if works_data else 0
        
        logger.info(f"📈 Average works per author: {avg_works_per_author:.1f}")
        logger.info(f"📈 Average authors per work: {avg_authors_per_work:.1f}")

        # Run benchmark if requested
        if args.benchmark:
            benchmark_results = run_consolidation_benchmark(
                authors_data, author_work_map, args.limit
            )
        
        # Perform consolidation
        logger.info(f"🎯 Starting {method_name} consolidation...")
        
        if use_enhanced:
            consolidation_result = consolidate_authors_enhanced(
                authors_data, author_work_map, args.threshold, args.limit
            )
            consolidated_authors, author_graph, matcher = consolidation_result
        else:
            consolidation_result = consolidate_authors_traditional(
                authors_data, author_work_map, args.threshold, args.limit
            )
            consolidated_authors, author_graph = consolidation_result
            matcher = None

        # Analysis and statistics
        logger.info("\n📊 Analyzing consolidation results...")
        original_count = len(authors_data)
        if args.limit and original_count > args.limit:
            original_count = args.limit
            
        consolidated_count = len(consolidated_authors)
        reduction_percentage = ((original_count - consolidated_count) / original_count * 100) if original_count > 0 else 0
        consolidation_rate = author_graph.number_of_edges() / original_count if original_count > 0 else 0
        
        logger.info(f"   📉 Author reduction: {reduction_percentage:.1f}% ({original_count:,} → {consolidated_count:,})")
        logger.info(f"   🔗 Consolidation edges: {author_graph.number_of_edges():,}")
        logger.info(f"   📊 Edge density: {consolidation_rate:.3f}")
        
        # Connected components analysis
        components = list(nx.connected_components(author_graph))
        largest_component = max(len(comp) for comp in components) if components else 0
        logger.info(f"   🔗 Connected components: {len(components):,}")
        logger.info(f"   📏 Largest component: {largest_component} authors")

        # Export detailed results if requested
        if args.export_results:
            results_file = export_detailed_results(
                consolidated_authors, author_graph, authors_data, works_data, method_name
            )

        # Build full graph for Neo4j (unless skipped)
        if not args.skip_neo4j:
            logger.info("🏗️ Building full knowledge graph...")
            full_graph, graph_stats = build_full_graph(consolidated_authors, works_data)
            
            logger.info(f"   📊 Knowledge graph nodes: {full_graph.number_of_nodes():,}")
            logger.info(f"   📊 Knowledge graph edges: {full_graph.number_of_edges():,}")
            
            # Save to Neo4j database
            logger.info("💾 Saving to Neo4j database...")
            save_to_neo4j(full_graph, consolidated_authors, works_data)
            logger.info("✅ Data successfully saved to Neo4j database")

        # Final summary
        logger.info("\n🎉 PROCESS COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        logger.info(f"📊 Final Statistics:")
        logger.info(f"   • Method: {method_name}")
        logger.info(f"   • Original authors: {original_count:,}")
        logger.info(f"   • Consolidated authors: {consolidated_count:,}")
        logger.info(f"   • Author reduction: {reduction_percentage:.1f}%")
        logger.info(f"   • Consolidation edges: {author_graph.number_of_edges():,}")
        
        if not args.skip_neo4j:
            logger.info(f"   • Knowledge graph nodes: {full_graph.number_of_nodes():,}")
            logger.info(f"   • Knowledge graph edges: {full_graph.number_of_edges():,}")
        
        if matcher and hasattr(matcher, 'metrics'):
            logger.info(f"   • Performance: {matcher.metrics.authors_per_second:.1f} authors/sec")
            logger.info(f"   • Match breakdown: exact={matcher.metrics.exact_matches}, fuzzy={matcher.metrics.fuzzy_matches}, orcid={matcher.metrics.orcid_matches}")
        
        if args.benchmark:
            logger.info("   • Benchmark results saved to main_consolidation_benchmark.json")
        
        if args.export_results:
            logger.info(f"   • Detailed results exported to {results_file}")
        
        # Recommendations
        logger.info("\n💡 RECOMMENDATIONS:")
        if use_enhanced and matcher and hasattr(matcher, 'metrics'):
            if matcher.metrics.authors_per_second > 1000:
                logger.info("   ✅ Excellent performance - suitable for large-scale processing")
            if matcher.metrics.exact_matches / (matcher.metrics.exact_matches + matcher.metrics.fuzzy_matches) > 0.7:
                logger.info("   ✅ High-confidence matches dominate - good data quality")
        
        if reduction_percentage > 20:
            logger.info("   ⚠️ High consolidation rate detected - consider manual validation")
        elif reduction_percentage < 2:
            logger.info("   💡 Low consolidation rate - consider lowering similarity threshold")
        
        return True

    except KeyboardInterrupt:
        logger.info("⏹️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error in main process: {str(e)}", exc_info=True)
        logger.error("Check the logs above for more details")
        sys.exit(1)


if __name__ == "__main__":
    main()
