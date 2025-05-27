#!/usr/bin/env python
"""
Enhanced Author Resolution and Consolidation (ARC) System
=========================================================

This script performs author resolution and consolidation using enhanced 
algorithms with real OpenAlex data as the primary method.

Usage:
    python create_graph_author_to_articles.py [options]

Options:
    --matcher {traditional,enhanced}  Choose matcher type (default: enhanced)
    --benchmark                       Run benchmark comparison
    --threshold FLOAT                 Similarity threshold (default: 0.85)
    --limit INT                      Limit number of authors for testing
    --export-results                 Export detailed results and metrics
    --skip-neo4j                     Skip Neo4j database insertion
"""

import os
import sys
import logging
import networkx as nx
import time
import json
import argparse
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
    
    # Export performance metrics
    if hasattr(matcher, 'export_metrics'):
        metrics_file = "enhanced_matcher_metrics.json"
        matcher.export_metrics(metrics_file)
        logger.info(f"📊 Performance metrics exported to: {metrics_file}")
    
    logger.info(f"✅ Enhanced consolidation completed in {processing_time:.2f} seconds")
    
    return consolidated, G, matcher


def benchmark_matchers(authors_data, author_work_map, threshold=0.85, limit=1000):
    """Benchmark different matcher implementations for performance comparison."""
    logger.info("\n📊 BENCHMARK MODE: Comparing Traditional vs Enhanced Matchers")
    logger.info("=" * 80)
    
    # Limit dataset for benchmark
    if len(authors_data) > limit:
        logger.info(f"📊 Using sample of {limit} authors for benchmark")
        authors_sample = dict(list(authors_data.items())[:limit])
    else:
        authors_sample = authors_data.copy()
    
    benchmark_results = {}
    
    # Traditional Matcher
    logger.info("\n🔍 Benchmarking Traditional Matcher...")
    traditional_start = time.time()
    
    try:
        traditional_matcher = SmartAuthorMatcher(similarity_threshold=threshold)
        
        # Extract features
        traditional_features = {}
        for author_id, author_data in tqdm(authors_sample.items(), desc="Traditional features"):
            traditional_features[author_id] = traditional_matcher.extract_features(
                author_id, author_data, author_work_map
            )
        
        # Find candidates
        traditional_graph = traditional_matcher.find_candidates(traditional_features, author_work_map)
        traditional_components = list(nx.connected_components(traditional_graph))
        traditional_consolidated, _ = consolidate_authors(traditional_graph, authors_sample, traditional_components)
        
        traditional_time = time.time() - traditional_start
        
        benchmark_results['traditional'] = {
            'time': traditional_time,
            'edges': traditional_graph.number_of_edges(),
            'components': len(traditional_components),
            'consolidated_authors': len(traditional_consolidated),
            'reduction_rate': (len(authors_sample) - len(traditional_consolidated)) / len(authors_sample),
            'authors_per_second': len(authors_sample) / traditional_time
        }
        
        logger.info(f"✅ Traditional: {traditional_time:.2f}s, {traditional_graph.number_of_edges()} edges")
        
    except Exception as e:
        logger.error(f"❌ Traditional matcher failed: {e}")
        benchmark_results['traditional'] = {'error': str(e)}
    
    # Enhanced Matcher
    logger.info("\n🚀 Benchmarking Enhanced Matcher...")
    enhanced_start = time.time()
    
    try:
        enhanced_matcher = EnhancedAuthorMatcher(
            similarity_threshold=threshold,
            batch_size=1000,
            use_semantic_similarity=True,
            use_phonetic_matching=True,
            enable_caching=True
        )
        
        # Extract features
        enhanced_features = {}
        for author_id, author_data in tqdm(authors_sample.items(), desc="Enhanced features"):
            enhanced_features[author_id] = enhanced_matcher.extract_features_enhanced(
                author_id, author_data, author_work_map
            )
        
        # Find candidates
        enhanced_graph = enhanced_matcher.find_candidates_optimized(enhanced_features, author_work_map)
        enhanced_components = list(nx.connected_components(enhanced_graph))
        enhanced_consolidated, _ = consolidate_authors(enhanced_graph, authors_sample, enhanced_components)
        
        enhanced_time = time.time() - enhanced_start
        
        benchmark_results['enhanced'] = {
            'time': enhanced_time,
            'edges': enhanced_graph.number_of_edges(),
            'components': len(enhanced_components),
            'consolidated_authors': len(enhanced_consolidated),
            'reduction_rate': (len(authors_sample) - len(enhanced_consolidated)) / len(authors_sample),
            'authors_per_second': len(authors_sample) / enhanced_time
        }
        
        logger.info(f"✅ Enhanced: {enhanced_time:.2f}s, {enhanced_graph.number_of_edges()} edges")
        
    except Exception as e:
        logger.error(f"❌ Enhanced matcher failed: {e}")
        benchmark_results['enhanced'] = {'error': str(e)}
    
    # Comparison
    if 'traditional' in benchmark_results and 'enhanced' in benchmark_results:
        if 'error' not in benchmark_results['traditional'] and 'error' not in benchmark_results['enhanced']:
            speedup = benchmark_results['traditional']['time'] / benchmark_results['enhanced']['time']
            
            logger.info("\n📈 BENCHMARK RESULTS:")
            logger.info("=" * 50)
            logger.info(f"Traditional Matcher:")
            logger.info(f"  ⏱️  Time: {benchmark_results['traditional']['time']:.2f}s")
            logger.info(f"  🔗 Edges: {benchmark_results['traditional']['edges']:,}")
            logger.info(f"  👥 Final authors: {benchmark_results['traditional']['consolidated_authors']:,}")
            logger.info(f"  📉 Reduction: {benchmark_results['traditional']['reduction_rate']:.1%}")
            
            logger.info(f"\nEnhanced Matcher:")
            logger.info(f"  ⏱️  Time: {benchmark_results['enhanced']['time']:.2f}s")
            logger.info(f"  🔗 Edges: {benchmark_results['enhanced']['edges']:,}")
            logger.info(f"  👥 Final authors: {benchmark_results['enhanced']['consolidated_authors']:,}")
            logger.info(f"  📉 Reduction: {benchmark_results['enhanced']['reduction_rate']:.1%}")
            
            logger.info(f"\n🏆 PERFORMANCE GAIN:")
            logger.info(f"  🚀 Speedup: {speedup:.1f}x faster")
            logger.info(f"  📊 Enhanced processes {benchmark_results['enhanced']['authors_per_second']:.1f} authors/sec")
            logger.info(f"  📊 Traditional processes {benchmark_results['traditional']['authors_per_second']:.1f} authors/sec")
    
    # Export benchmark results
    benchmark_file = "matcher_benchmark_results.json"
    with open(benchmark_file, 'w') as f:
        json.dump(benchmark_results, f, indent=2)
    logger.info(f"📊 Benchmark results saved to: {benchmark_file}")
    
    return benchmark_results
    logger.info("\n🏁 Starting Matcher Benchmark Comparison")
    logger.info("=" * 70)
    
    # Prepare features for both matchers
    logger.info("📝 Preparing author features for benchmarking...")
    
    # Traditional matcher features
    traditional_matcher = SmartAuthorMatcher(similarity_threshold=0.90)
    traditional_features = {}
    for author_id, author_data in tqdm(authors_data.items(), desc="Traditional features"):
        traditional_features[author_id] = traditional_matcher.extract_features(
            author_id, author_data, author_work_map
        )
    
    # Enhanced matcher features
    enhanced_matcher = EnhancedAuthorMatcher(
        similarity_threshold=0.85,
        use_semantic_similarity=True,
        use_phonetic_matching=True
    )
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
            logger.info(f"   🔗 Edge ratio: {comparison.get('edge_ratio', 0):.2f}x more matches")
            logger.info(f"   ⏱️  Time saved: {comparison.get('time_improvement_pct', 0):.1f}%")
    
    # Export benchmark results
    benchmark_file = "matcher_benchmark_results.json"
    try:
        import json
        with open(benchmark_file, 'w', encoding='utf-8') as f:
            json.dump(benchmark_results, f, indent=2, ensure_ascii=False)
        logger.info(f"📊 Benchmark results exported to: {benchmark_file}")
    except Exception as e:
        logger.error(f"❌ Failed to export benchmark results: {e}")
    
    return benchmark_results


def consolidate_authors_traditional(authors_data, author_work_map):
    """Traditional consolidation method using SmartAuthorMatcher."""
    logger.info("\n🔍 Starting Traditional Rule-Based Author Consolidation")
    logger.info("=" * 70)
    
    start_time = time.time()
    
    # Initialize traditional matcher
    matcher = SmartAuthorMatcher(similarity_threshold=0.95)

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
    
    end_time = time.time()

    print_consolidation_stats(consolidated, authors_data, component_stats, G)
    
    logger.info(f"✅ Traditional consolidation completed in {end_time - start_time:.2f} seconds")

    return consolidated, G


def consolidate_authors_sampled(authors_data, author_work_map):
    """Sampled traditional consolidation method for large datasets."""
    logger.info("\n🔍 Using Sampled Traditional Rule-Based Consolidation")
    logger.info("=" * 70)
    
    start_time = time.time()
    
    # For very large datasets, use a sampling approach
    import random
    
    total_authors = len(authors_data)
    sample_size = min(5000, total_authors)  # Sample max 5000 authors
    
    logger.info(f"📊 Large dataset detected ({total_authors:,} authors)")
    logger.info(f"🎲 Using sampling approach with {sample_size:,} authors")
    
    # Sample authors randomly but ensure we get a representative sample
    author_ids = list(authors_data.keys())
    sampled_author_ids = random.sample(author_ids, sample_size)
    
    # Create sampled dataset
    sampled_authors_data = {aid: authors_data[aid] for aid in sampled_author_ids}
    
    # Initialize traditional matcher
    matcher = SmartAuthorMatcher(similarity_threshold=0.95)

    logger.info("📝 Extracting author features for sample...")
    authors_features = {}
    for author_id, author_data in tqdm(sampled_authors_data.items(), desc="Extracting features (sample)"):
        authors_features[author_id] = matcher.extract_features(
            author_id, author_data, author_work_map
        )

    # Find candidates using traditional approach on sample
    logger.info("🔗 Finding consolidation candidates in sample...")
    G_sample = matcher.find_candidates(authors_features, author_work_map)

    # Extend findings to full dataset based on similar patterns
    logger.info("🔍 Extending findings to full dataset...")
    G = nx.Graph()
    
    # Add all authors to the graph
    for author_id in authors_data.keys():
        G.add_node(author_id)
    
    # Copy edges from sample
    for edge in G_sample.edges(data=True):
        G.add_edge(edge[0], edge[1], **edge[2])
    
    # Use simple heuristics to find obvious duplicates in the remaining data
    logger.info("🔍 Finding obvious duplicates in remaining data...")
    remaining_authors = set(authors_data.keys()) - set(sampled_author_ids)
    
    # Group by exact name matches for quick wins
    name_groups = {}
    for author_id in tqdm(remaining_authors, desc="Grouping by exact names"):
        name = authors_data[author_id].get('display_name', '').strip().lower()
        if name and len(name) > 3:  # Avoid very short names
            if name not in name_groups:
                name_groups[name] = []
            name_groups[name].append(author_id)
    
    # Add edges for exact name matches
    exact_matches = 0
    for name, author_list in tqdm(name_groups.items(), desc="Creating exact match edges"):
        if len(author_list) > 1:
            for i, author1 in enumerate(author_list):
                for author2 in author_list[i+1:]:
                    G.add_edge(author1, author2, reason="exact_name_match", confidence=0.95)
                    exact_matches += 1
    
    logger.info(f"   Found {exact_matches} exact name matches in remaining data")

    logger.info("🔍 Identifying connected components...")
    components = list(nx.connected_components(G))
    logger.info(f"   Found {len(components)} connected components")

    # Perform consolidation
    logger.info("🔄 Consolidating authors...")
    consolidated, component_stats = consolidate_authors(G, authors_data, components)
    
    end_time = time.time()

    print_consolidation_stats(consolidated, authors_data, component_stats, G)
    
    logger.info(f"✅ Sampled consolidation completed in {end_time - start_time:.2f} seconds")

    return consolidated, G


def consolidate_authors_main(authors_data, author_work_map, works_data=None, use_enhanced=True, 
                           run_benchmark=False, threshold=0.85, limit=None):
    """
    Main consolidation function with enhanced matcher as the primary method.
    
    Args:
        authors_data: Dictionary of author data
        author_work_map: Mapping of authors to works
        works_data: Works data (for compatibility)
        use_enhanced: Whether to use enhanced matcher (default: True)
        run_benchmark: Whether to run benchmark comparison (default: False)
        threshold: Similarity threshold for matching (default: 0.85)
        limit: Limit number of authors for testing (default: None)
    """
    
    total_authors = len(authors_data)
    logger.info(f"🎯 Processing dataset with {total_authors:,} authors")
    
    # Run benchmark if requested
    if run_benchmark:
        benchmark_results = benchmark_matchers(
            authors_data, author_work_map, threshold=threshold, limit=limit or 1000
        )
    
    # Choose method based on parameters and dataset size
    if use_enhanced:
        logger.info("🚀 Using Enhanced Author Matcher (Primary Method)")
        return consolidate_authors_enhanced(authors_data, author_work_map, threshold=threshold, limit=limit)
    elif total_authors > 25000:
        logger.info("🔍 Using sampled approach for large dataset")
        return consolidate_authors_sampled(authors_data, author_work_map)
    else:
        logger.info("🔍 Using traditional rule-based consolidation")
        return consolidate_authors_traditional(authors_data, author_work_map)


def main():
    """Main function to execute the enhanced author-article graph creation workflow."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Enhanced Author Resolution and Consolidation System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run with enhanced matcher (default)
  %(prog)s --matcher traditional    # Use traditional matcher
  %(prog)s --benchmark             # Compare both matchers
  %(prog)s --limit 1000            # Test with 1000 authors
  %(prog)s --threshold 0.9         # Use higher similarity threshold
  %(prog)s --export-results        # Export detailed metrics
  %(prog)s --skip-neo4j           # Skip database insertion
        """
    )
    
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
                       help='Skip Neo4j database insertion')
    
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
    
    if use_enhanced:
        logger.info("🚀 Using Enhanced Author Matcher with advanced algorithms (PRIMARY METHOD)")
    else:
        logger.info("🔍 Using Traditional rule-based approach")
    
    if args.benchmark:
        logger.info("🏁 Benchmark mode enabled - will compare matchers")
    
    if args.limit:
        logger.info(f"📊 Testing mode: limited to {args.limit:,} authors")
    
    try:
        # Load data files - using real OpenAlex data
        authors_file = os.path.join(project_root, "data/openalex_authors_complete.json")
        works_file = os.path.join(project_root, "data/openalex_data.json")
        
        # Verify files exist
        if not os.path.exists(authors_file):
            logger.error(f"❌ Authors file not found: {authors_file}")
            logger.error("Please run the data extraction process first")
            sys.exit(1)
        
        if not os.path.exists(works_file):
            logger.error(f"❌ Works file not found: {works_file}")
            logger.error("Please run the data extraction process first")
            sys.exit(1)

        # Load real OpenAlex data
        logger.info("📚 Loading real OpenAlex data...")
        authors_data, works_data = load_data(authors_file, works_file)
        author_work_map = build_author_work_map(works_data)
        
        logger.info(f"📊 Loaded {len(authors_data):,} authors and {len(works_data):,} works")
        
        # Data quality checks
        total_authorship_records = sum(len(works) for works in author_work_map.values())
        avg_works_per_author = total_authorship_records / len(authors_data) if authors_data else 0
        avg_authors_per_work = sum(len(work.get('authorships', [])) for work in works_data.values()) / len(works_data) if works_data else 0
        
        logger.info(f"📈 Average works per author: {avg_works_per_author:.1f}")
        logger.info(f"📈 Average authors per work: {avg_authors_per_work:.1f}")

        # Perform consolidation with enhanced system
        method_name = "Enhanced" if use_enhanced else "Traditional"
        logger.info(f"🎯 Selected approach: {method_name} (Threshold: {args.threshold})")
            
        consolidation_result = consolidate_authors_main(
            authors_data, author_work_map, works_data, 
            use_enhanced=use_enhanced, 
            run_benchmark=args.benchmark,
            threshold=args.threshold,
            limit=args.limit
        )
        
        # Handle different return formats
        if len(consolidation_result) == 3:
            consolidated_authors, author_graph, matcher = consolidation_result
        else:
            consolidated_authors, author_graph = consolidation_result
            matcher = None

        # Graph analysis
        logger.info("📊 Analyzing consolidation results...")
        reduction_percentage = ((len(authors_data) - len(consolidated_authors)) / len(authors_data) * 100) if authors_data else 0
        consolidation_rate = author_graph.number_of_edges() / len(authors_data) if authors_data else 0
        
        logger.info(f"   Reduction: {reduction_percentage:.1f}% ({len(authors_data):,} → {len(consolidated_authors):,})")
        logger.info(f"   Consolidation edges: {author_graph.number_of_edges():,}")
        logger.info(f"   Edge density: {consolidation_rate:.3f}")

        # Build full graph for Neo4j
        logger.info("🏗️ Building full knowledge graph...")
        full_graph, graph_stats = build_full_graph(consolidated_authors, works_data)
        
        logger.info(f"   Knowledge graph nodes: {full_graph.number_of_nodes():,}")
        logger.info(f"   Knowledge graph edges: {full_graph.number_of_edges():,}")
        
        # Save to Neo4j database (unless skipped)
        if not args.skip_neo4j:
            logger.info("💾 Saving to Neo4j database...")
            save_to_neo4j(full_graph, consolidated_authors, works_data)
            logger.info("💾 Data successfully saved to Neo4j database")
        else:
            logger.info("⏭️ Skipping Neo4j database insertion (--skip-neo4j)")

        # Export results if requested
        if args.export_results:
            logger.info("📤 Exporting detailed results...")
            
            results = {
                'metadata': {
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'matcher_type': args.matcher,
                    'threshold': args.threshold,
                    'limit': args.limit,
                    'total_authors_processed': len(authors_data),
                    'total_works_processed': len(works_data)
                },
                'consolidation_results': {
                    'original_authors': len(authors_data),
                    'consolidated_authors': len(consolidated_authors),
                    'reduction_percentage': reduction_percentage,
                    'consolidation_edges': author_graph.number_of_edges(),
                    'connected_components': len(list(nx.connected_components(author_graph))),
                    'average_component_size': len(authors_data) / len(list(nx.connected_components(author_graph))) if list(nx.connected_components(author_graph)) else 0
                },
                'knowledge_graph': {
                    'total_nodes': full_graph.number_of_nodes(),
                    'total_edges': full_graph.number_of_edges(),
                    'author_nodes': len([n for n, d in full_graph.nodes(data=True) if d.get('type_node') == 'Author']),
                    'work_nodes': len([n for n, d in full_graph.nodes(data=True) if d.get('type_node') == 'Work'])
                }
            }
            
            results_file = f"consolidation_results_{args.matcher}_{time.strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"📊 Results exported to: {results_file}")

        # Final summary
        logger.info("\n✅ PROCESS COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        logger.info(f"📊 Final Statistics:")
        logger.info(f"   • Original authors: {len(authors_data):,}")
        logger.info(f"   • Consolidated authors: {len(consolidated_authors):,}")
        logger.info(f"   • Author reduction: {reduction_percentage:.1f}%")
        logger.info(f"   • Consolidation edges: {author_graph.number_of_edges():,}")
        logger.info(f"   • Knowledge graph nodes: {full_graph.number_of_nodes():,}")
        logger.info(f"   • Knowledge graph edges: {full_graph.number_of_edges():,}")
        logger.info(f"   • Method used: {method_name}")
        
        if matcher and hasattr(matcher, 'metrics'):
            logger.info(f"   • Performance: {matcher.metrics.authors_per_second:.1f} authors/sec")
            logger.info(f"   • Match types: exact={matcher.metrics.exact_matches}, fuzzy={matcher.metrics.fuzzy_matches}, orcid={matcher.metrics.orcid_matches}")
        
        if args.benchmark:
            logger.info("📊 Benchmark results saved to matcher_benchmark_results.json")
        
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
