#!/usr/bin/env python
"""
Comprehensive Author Matcher Benchmarking Suite
==============================================

This script provides comprehensive benchmarking and comparison between
different author matching algorithms.
"""

import sys
import os
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from models.author_matcher import SmartAuthorMatcher
from models.enhanced_author_matcher import EnhancedAuthorMatcher
from benchmarking.performance_analyzer import PerformanceAnalyzer
from utils.data_processing import load_sample_data, create_test_dataset

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_data(data_file: str, sample_size: int = None) -> Dict[str, Any]:
    """
    Load test data for benchmarking.
    
    Args:
        data_file: Path to the data file
        sample_size: Optional limit on number of authors to load
        
    Returns:
        Dictionary with authors and work mappings
    """
    logger.info(f"📁 Loading test data from: {data_file}")
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        authors = data.get('authors', {})
        works = data.get('works', {})
        
        # Create author-work mapping
        author_work_map = {}
        for work_id, work_data in works.items():
            for author in work_data.get('authorships', []):
                author_id = author.get('author', {}).get('id', '').split('/')[-1]
                if author_id:
                    if author_id not in author_work_map:
                        author_work_map[author_id] = []
                    author_work_map[author_id].append(work_id)
        
        # Sample data if requested
        if sample_size and len(authors) > sample_size:
            logger.info(f"🎯 Sampling {sample_size} authors from {len(authors)} total")
            author_ids = list(authors.keys())[:sample_size]
            authors = {aid: authors[aid] for aid in author_ids}
            
            # Filter work mappings to only include sampled authors
            author_work_map = {aid: works for aid, works in author_work_map.items() 
                             if aid in authors}
        
        logger.info(f"✅ Loaded {len(authors)} authors with {len(author_work_map)} work mappings")
        
        return {
            'authors': authors,
            'works': works,
            'author_work_map': author_work_map
        }
        
    except Exception as e:
        logger.error(f"❌ Error loading test data: {e}")
        raise


def benchmark_traditional_matcher(test_data: Dict[str, Any]) -> Any:
    """Benchmark the traditional SmartAuthorMatcher."""
    logger.info("🔧 Running Traditional Author Matcher...")
    
    matcher = SmartAuthorMatcher(
        similarity_threshold=0.90,
        batch_size=500
    )
    
    authors = test_data['authors']
    author_work_map = test_data['author_work_map']
    
    # Extract features
    authors_features = {}
    for author_id, author_data in authors.items():
        features = matcher.extract_features(author_id, author_data, author_work_map)
        authors_features[author_id] = features
    
    # Find candidates
    result_graph = matcher.find_candidates(authors_features, author_work_map)
    
    # Add metrics to result
    result_graph.total_comparisons = len(authors) * (len(authors) - 1) // 2
    result_graph.total_edges = len(result_graph.edges())
    
    return result_graph


def benchmark_enhanced_matcher(test_data: Dict[str, Any]) -> Any:
    """Benchmark the Enhanced Author Matcher."""
    logger.info("🚀 Running Enhanced Author Matcher...")
    
    matcher = EnhancedAuthorMatcher(
        similarity_threshold=0.90,
        batch_size=1000,
        use_semantic_similarity=True,
        use_phonetic_matching=True,
        enable_caching=True
    )
    
    authors = test_data['authors']
    author_work_map = test_data['author_work_map']
    
    # Run the enhanced consolidation
    result_graph = matcher.consolidate_authors(authors, author_work_map)
    
    return result_graph


def benchmark_enhanced_optimized(test_data: Dict[str, Any]) -> Any:
    """Benchmark the Enhanced Matcher with optimized settings."""
    logger.info("⚡ Running Enhanced Author Matcher (Optimized)...")
    
    matcher = EnhancedAuthorMatcher(
        similarity_threshold=0.85,  # Slightly lower threshold
        batch_size=2000,  # Larger batches
        use_semantic_similarity=True,
        use_phonetic_matching=True,
        enable_caching=True
    )
    
    authors = test_data['authors']
    author_work_map = test_data['author_work_map']
    
    # Run with optimized settings
    result_graph = matcher.consolidate_authors(authors, author_work_map)
    
    return result_graph


def benchmark_enhanced_conservative(test_data: Dict[str, Any]) -> Any:
    """Benchmark the Enhanced Matcher with conservative settings."""
    logger.info("🛡️ Running Enhanced Author Matcher (Conservative)...")
    
    matcher = EnhancedAuthorMatcher(
        similarity_threshold=0.95,  # Higher threshold
        batch_size=500,  # Smaller batches
        use_semantic_similarity=True,
        use_phonetic_matching=False,  # Disable phonetic for higher precision
        enable_caching=True
    )
    
    authors = test_data['authors']
    author_work_map = test_data['author_work_map']
    
    # Run with conservative settings
    result_graph = matcher.consolidate_authors(authors, author_work_map)
    
    return result_graph


def run_comprehensive_benchmark(data_file: str, 
                               sample_sizes: List[int] = None,
                               output_dir: str = "benchmarking_results"):
    """
    Run comprehensive benchmarking across multiple algorithms and dataset sizes.
    
    Args:
        data_file: Path to the test data file
        sample_sizes: List of sample sizes to test
        output_dir: Directory to save results
    """
    if sample_sizes is None:
        sample_sizes = [100, 500, 1000, 2000]
    
    logger.info("🏁 Starting Comprehensive Author Matcher Benchmarking")
    logger.info(f"   Data file: {data_file}")
    logger.info(f"   Sample sizes: {sample_sizes}")
    logger.info(f"   Output directory: {output_dir}")
    
    # Initialize performance analyzer
    analyzer = PerformanceAnalyzer(output_dir)
    
    # Algorithms to benchmark
    algorithms = [
        ("Traditional Matcher", benchmark_traditional_matcher),
        ("Enhanced Matcher", benchmark_enhanced_matcher),
        ("Enhanced Optimized", benchmark_enhanced_optimized),
        ("Enhanced Conservative", benchmark_enhanced_conservative),
    ]
    
    # Run benchmarks for each sample size
    for sample_size in sample_sizes:
        logger.info(f"\n{'='*60}")
        logger.info(f"BENCHMARKING WITH {sample_size} AUTHORS")
        logger.info(f"{'='*60}")
        
        # Load test data for this sample size
        test_data = load_test_data(data_file, sample_size)
        
        # Run each algorithm
        for algo_name, algo_func in algorithms:
            try:
                logger.info(f"\n📊 Benchmarking: {algo_name} (n={sample_size})")
                
                # Create algorithm name with sample size
                full_algo_name = f"{algo_name}_n{sample_size}"
                
                # Benchmark the algorithm
                result = analyzer.benchmark_algorithm(
                    algorithm_func=lambda data: algo_func(data),
                    algorithm_name=full_algo_name,
                    test_data=test_data,
                    run_count=3
                )
                
                # Assess quality
                quality = analyzer.assess_quality(
                    result=algo_func(test_data),  # Re-run for quality assessment
                    algorithm_name=full_algo_name,
                    test_data=test_data
                )
                
                logger.info(f"✅ Completed: {algo_name} (n={sample_size})")
                
            except Exception as e:
                logger.error(f"❌ Error benchmarking {algo_name} (n={sample_size}): {e}")
                continue
    
    # Generate comprehensive report
    logger.info(f"\n{'='*60}")
    logger.info("GENERATING REPORTS")
    logger.info(f"{'='*60}")
    
    # Generate text report
    report_text = analyzer.generate_report()
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)
    print(report_text)
    
    # Generate comparison plots
    try:
        analyzer.plot_comparison()
        logger.info("📊 Comparison plots generated")
    except Exception as e:
        logger.warning(f"Could not generate plots: {e}")
    
    # Export results in multiple formats
    try:
        json_file = analyzer.export_results('json')
        csv_file = analyzer.export_results('csv')
        excel_file = analyzer.export_results('excel')
        
        logger.info(f"📁 Results exported:")
        logger.info(f"   JSON: {json_file}")
        logger.info(f"   CSV: {csv_file}")
        logger.info(f"   Excel: {excel_file}")
        
    except Exception as e:
        logger.warning(f"Could not export results: {e}")
    
    logger.info("🎉 Comprehensive benchmarking completed!")


def run_scalability_test(data_file: str, 
                        max_authors: int = 5000,
                        step_size: int = 500,
                        output_dir: str = "scalability_results"):
    """
    Run scalability testing to understand performance characteristics.
    
    Args:
        data_file: Path to the test data file
        max_authors: Maximum number of authors to test
        step_size: Step size for increasing dataset size
        output_dir: Directory to save results
    """
    logger.info("📈 Starting Scalability Testing")
    logger.info(f"   Max authors: {max_authors}")
    logger.info(f"   Step size: {step_size}")
    
    analyzer = PerformanceAnalyzer(output_dir)
    
    # Test only the best performing algorithms for scalability
    algorithms = [
        ("Enhanced Optimized", benchmark_enhanced_optimized),
        ("Traditional Matcher", benchmark_traditional_matcher),
    ]
    
    sample_sizes = list(range(step_size, max_authors + 1, step_size))
    
    for sample_size in sample_sizes:
        logger.info(f"\n🔬 Testing scalability with {sample_size} authors")
        
        test_data = load_test_data(data_file, sample_size)
        
        for algo_name, algo_func in algorithms:
            try:
                full_algo_name = f"{algo_name}_scalability_n{sample_size}"
                
                result = analyzer.benchmark_algorithm(
                    algorithm_func=lambda data: algo_func(data),
                    algorithm_name=full_algo_name,
                    test_data=test_data,
                    run_count=1  # Single run for scalability testing
                )
                
                logger.info(f"   {algo_name}: {result.authors_per_second:.1f} authors/s, "
                          f"{result.memory_peak_mb:.1f}MB")
                
            except Exception as e:
                logger.error(f"❌ Scalability test failed for {algo_name} (n={sample_size}): {e}")
    
    # Generate scalability report
    analyzer.generate_report()
    analyzer.plot_comparison()
    analyzer.export_results('json')
    
    logger.info("📈 Scalability testing completed!")


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Author Matcher Benchmarking Suite"
    )
    
    parser.add_argument(
        '--data-file',
        type=str,
        default='data/openalex_data.json',
        help='Path to the test data file'
    )
    
    parser.add_argument(
        '--benchmark-type',
        choices=['comprehensive', 'scalability', 'quick'],
        default='comprehensive',
        help='Type of benchmark to run'
    )
    
    parser.add_argument(
        '--sample-sizes',
        nargs='+',
        type=int,
        default=[100, 500, 1000],
        help='Sample sizes to test for comprehensive benchmarking'
    )
    
    parser.add_argument(
        '--max-authors',
        type=int,
        default=5000,
        help='Maximum number of authors for scalability testing'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='benchmarking_results',
        help='Directory to save benchmark results'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Verify data file exists
    if not os.path.exists(args.data_file):
        logger.error(f"❌ Data file not found: {args.data_file}")
        sys.exit(1)
    
    try:
        if args.benchmark_type == 'comprehensive':
            run_comprehensive_benchmark(
                data_file=args.data_file,
                sample_sizes=args.sample_sizes,
                output_dir=args.output_dir
            )
            
        elif args.benchmark_type == 'scalability':
            run_scalability_test(
                data_file=args.data_file,
                max_authors=args.max_authors,
                output_dir=args.output_dir
            )
            
        elif args.benchmark_type == 'quick':
            # Quick benchmark with small sample
            run_comprehensive_benchmark(
                data_file=args.data_file,
                sample_sizes=[100],
                output_dir=args.output_dir
            )
        
    except KeyboardInterrupt:
        logger.info("🛑 Benchmarking interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Benchmarking failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
