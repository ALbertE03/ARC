#!/usr/bin/env python
"""
Analyze Enhanced Author Matcher Results
=======================================

This script analyzes the results and performance of the enhanced author matcher.
"""

import json
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_results(results_file="benchmark_results.json", metrics_file="test_enhanced_matcher_metrics.json"):
    """Load benchmark and metrics results."""
    results = {}
    metrics = {}
    
    if os.path.exists(results_file):
        with open(results_file, 'r') as f:
            results = json.load(f)
        logger.info(f"✅ Loaded benchmark results from {results_file}")
    else:
        logger.warning(f"⚠️ Benchmark results file not found: {results_file}")
    
    if os.path.exists(metrics_file):
        with open(metrics_file, 'r') as f:
            metrics = json.load(f)
        logger.info(f"✅ Loaded metrics from {metrics_file}")
    else:
        logger.warning(f"⚠️ Metrics file not found: {metrics_file}")
    
    return results, metrics


def analyze_performance(results, metrics):
    """Analyze performance metrics."""
    logger.info("\n🚀 PERFORMANCE ANALYSIS")
    logger.info("=" * 50)
    
    if results:
        enhanced = results.get('enhanced', {})
        baseline = results.get('baseline', {})
        comparison = results.get('comparison', {})
        
        if enhanced and baseline:
            logger.info(f"📊 Dataset Size: {enhanced.get('metrics', {}).get('total_authors', 'N/A')} authors")
            logger.info(f"⏱️  Enhanced Processing Time: {enhanced.get('processing_time', 0):.3f}s")
            logger.info(f"⏱️  Traditional Processing Time: {baseline.get('processing_time', 0):.3f}s")
            logger.info(f"⚡ Speed Improvement: {comparison.get('speedup_factor', 0):.1f}x faster")
            logger.info(f"📈 Time Reduction: {comparison.get('time_improvement_pct', 0):.1f}%")
            
            # Performance rates
            enhanced_rate = enhanced.get('authors_per_second', 0)
            baseline_rate = baseline.get('authors_per_second', 0)
            logger.info(f"🔥 Enhanced Rate: {enhanced_rate:,.0f} authors/second")
            logger.info(f"🐌 Traditional Rate: {baseline_rate:,.0f} authors/second")
    
    if metrics:
        logger.info(f"\n🔍 DETAILED METRICS")
        logger.info(f"   Total Comparisons: {metrics.get('total_comparisons', 0):,}")
        logger.info(f"   Comparison Rate: {metrics.get('comparisons_per_second', 0):.1f}/second")
        logger.info(f"   Memory Usage: {metrics.get('memory_usage_mb', 0):.1f} MB")


def analyze_accuracy(results, metrics):
    """Analyze matching accuracy."""
    logger.info("\n🎯 ACCURACY ANALYSIS")
    logger.info("=" * 50)
    
    if results:
        enhanced = results.get('enhanced', {})
        baseline = results.get('baseline', {})
        
        enhanced_edges = enhanced.get('edges_found', 0)
        baseline_edges = baseline.get('edges_found', 0)
        
        logger.info(f"🔗 Enhanced Matcher: {enhanced_edges} edges found")
        logger.info(f"🔗 Traditional Matcher: {baseline_edges} edges found")
        
        if baseline_edges > 0:
            edge_ratio = enhanced_edges / baseline_edges
            logger.info(f"📊 Edge Ratio: {edge_ratio:.2f} (Enhanced/Traditional)")
            
            if edge_ratio < 1.0:
                logger.info("   → Enhanced matcher is more conservative (fewer potential false positives)")
            elif edge_ratio > 1.0:
                logger.info("   → Enhanced matcher found more matches")
            else:
                logger.info("   → Both matchers found same number of matches")
    
    if metrics:
        logger.info(f"\n📋 MATCH BREAKDOWN:")
        logger.info(f"   • Exact matches: {metrics.get('exact_matches', 0)}")
        logger.info(f"   • ORCID matches: {metrics.get('orcid_matches', 0)}")
        logger.info(f"   • Fuzzy matches: {metrics.get('fuzzy_matches', 0)}")
        logger.info(f"   • Institution matches: {metrics.get('institution_matches', 0)}")
        logger.info(f"   • Work overlap matches: {metrics.get('work_overlap_matches', 0)}")


def analyze_efficiency(results, metrics):
    """Analyze matching efficiency."""
    logger.info("\n⚙️ EFFICIENCY ANALYSIS")
    logger.info("=" * 50)
    
    if metrics:
        total_authors = metrics.get('total_authors', 0)
        total_comparisons = metrics.get('total_comparisons', 0)
        
        if total_authors > 0:
            # Theoretical maximum comparisons for N×N approach
            max_comparisons = (total_authors * (total_authors - 1)) // 2
            comparison_reduction = 1 - (total_comparisons / max_comparisons) if max_comparisons > 0 else 0
            
            logger.info(f"📊 Authors Processed: {total_authors:,}")
            logger.info(f"🔍 Actual Comparisons: {total_comparisons:,}")
            logger.info(f"🔢 Max Possible Comparisons: {max_comparisons:,}")
            logger.info(f"📉 Comparison Reduction: {comparison_reduction:.1%}")
            logger.info(f"⚡ Efficiency Gain: {max_comparisons/total_comparisons:.1f}x fewer comparisons")


def generate_recommendations(results, metrics):
    """Generate recommendations based on results."""
    logger.info("\n💡 RECOMMENDATIONS")
    logger.info("=" * 50)
    
    if results:
        enhanced = results.get('enhanced', {})
        baseline = results.get('baseline', {})
        comparison = results.get('comparison', {})
        
        speedup = comparison.get('speedup_factor', 0)
        edge_ratio = comparison.get('edge_ratio', 0)
        
        if speedup > 10:
            logger.info("✅ Enhanced matcher shows excellent performance improvements")
            logger.info("   → Recommended for production use with large datasets")
        
        if edge_ratio < 0.8:
            logger.info("⚠️ Enhanced matcher is more conservative than traditional")
            logger.info("   → Consider lowering similarity threshold if recall is important")
            logger.info("   → Current threshold may be reducing false positives")
        
        if edge_ratio > 1.2:
            logger.info("📈 Enhanced matcher found more matches")
            logger.info("   → Validate quality of additional matches")
            logger.info("   → Consider if additional precision methods are needed")
    
    if metrics:
        total_comparisons = metrics.get('total_comparisons', 0)
        if total_comparisons < 100:
            logger.info("🔍 Very few comparisons needed")
            logger.info("   → Optimization algorithms are working effectively")
            logger.info("   → Suitable for real-time matching applications")


def main():
    """Main analysis function."""
    logger.info("🔬 Starting Enhanced Author Matcher Results Analysis...")
    
    # Load results
    results, metrics = load_results()
    
    if not results and not metrics:
        logger.error("❌ No results files found. Please run the benchmark first.")
        return
    
    # Run analyses
    analyze_performance(results, metrics)
    analyze_accuracy(results, metrics)
    analyze_efficiency(results, metrics)
    generate_recommendations(results, metrics)
    
    logger.info("\n✅ Analysis completed!")


if __name__ == "__main__":
    main()
