#!/usr/bin/env python
"""
Performance Analyzer for Author Matching Systems
==============================================

This module provides comprehensive performance analysis and benchmarking
tools for comparing different author matching algorithms.
"""

import time
import json
import psutil
import logging
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    algorithm_name: str
    dataset_size: int
    processing_time: float
    memory_peak_mb: float
    total_comparisons: int
    total_matches: int
    precision_estimate: float
    recall_estimate: float
    f1_score: float
    comparisons_per_second: float
    authors_per_second: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityMetrics:
    """Quality assessment metrics for author matching."""
    exact_name_matches: int = 0
    orcid_matches: int = 0
    institution_overlap_matches: int = 0
    work_overlap_matches: int = 0
    high_confidence_matches: int = 0
    medium_confidence_matches: int = 0
    low_confidence_matches: int = 0
    potential_false_positives: int = 0
    potential_false_negatives: int = 0


class PerformanceAnalyzer:
    """
    Comprehensive performance analyzer for author matching systems.
    
    Provides:
    - Detailed performance benchmarking
    - Quality assessment and validation
    - Comparative analysis between algorithms
    - Memory and speed profiling
    - Statistical analysis and reporting
    """
    
    def __init__(self, output_dir: str = "benchmarking_results"):
        """
        Initialize the performance analyzer.
        
        Args:
            output_dir: Directory to store benchmark results and reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.benchmark_results: List[BenchmarkResult] = []
        self.quality_assessments: Dict[str, QualityMetrics] = {}
        
        logger.info(f"📊 Performance Analyzer initialized. Results will be saved to: {self.output_dir}")
    
    def monitor_system_resources(self) -> Dict[str, float]:
        """Monitor current system resource usage."""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'memory_rss_mb': memory_info.rss / 1024 / 1024,
            'memory_vms_mb': memory_info.vms / 1024 / 1024,
            'cpu_percent': process.cpu_percent(interval=0.1),
            'system_memory_percent': psutil.virtual_memory().percent,
            'system_cpu_percent': psutil.cpu_percent(interval=0.1)
        }
    
    def benchmark_algorithm(self, 
                          algorithm_func,
                          algorithm_name: str,
                          test_data: Dict[str, Any],
                          run_count: int = 3) -> BenchmarkResult:
        """
        Benchmark a specific algorithm with multiple runs.
        
        Args:
            algorithm_func: Function to benchmark
            algorithm_name: Name of the algorithm
            test_data: Test data to process
            run_count: Number of runs to average
            
        Returns:
            BenchmarkResult with averaged metrics
        """
        logger.info(f"🔬 Benchmarking algorithm: {algorithm_name}")
        logger.info(f"   Dataset size: {len(test_data.get('authors', {}))} authors")
        logger.info(f"   Running {run_count} iterations...")
        
        run_results = []
        
        for run_num in range(run_count):
            logger.info(f"   Run {run_num + 1}/{run_count}")
            
            # Monitor initial state
            initial_resources = self.monitor_system_resources()
            start_time = time.perf_counter()
            
            # Run the algorithm
            try:
                result = algorithm_func(test_data)
                
                # Monitor final state
                end_time = time.perf_counter()
                final_resources = self.monitor_system_resources()
                
                processing_time = end_time - start_time
                memory_delta = final_resources['memory_rss_mb'] - initial_resources['memory_rss_mb']
                memory_peak = max(final_resources['memory_rss_mb'], initial_resources['memory_rss_mb'])
                
                # Extract metrics from result
                total_comparisons = getattr(result, 'total_comparisons', 0)
                total_matches = getattr(result, 'total_edges', 0) if hasattr(result, 'total_edges') else len(result.edges()) if hasattr(result, 'edges') else 0
                
                run_results.append({
                    'processing_time': processing_time,
                    'memory_peak_mb': memory_peak,
                    'memory_delta_mb': memory_delta,
                    'total_comparisons': total_comparisons,
                    'total_matches': total_matches,
                    'result': result
                })
                
            except Exception as e:
                logger.error(f"❌ Error in run {run_num + 1}: {e}")
                continue
        
        if not run_results:
            raise RuntimeError(f"All benchmark runs failed for {algorithm_name}")
        
        # Calculate averaged metrics
        avg_time = statistics.mean([r['processing_time'] for r in run_results])
        avg_memory = statistics.mean([r['memory_peak_mb'] for r in run_results])
        avg_comparisons = statistics.mean([r['total_comparisons'] for r in run_results])
        avg_matches = statistics.mean([r['total_matches'] for r in run_results])
        
        dataset_size = len(test_data.get('authors', {}))
        
        # Calculate rates
        comparisons_per_second = avg_comparisons / avg_time if avg_time > 0 else 0
        authors_per_second = dataset_size / avg_time if avg_time > 0 else 0
        
        # Estimate quality metrics (basic heuristics)
        precision_estimate = self._estimate_precision(run_results[-1]['result'], test_data)
        recall_estimate = self._estimate_recall(run_results[-1]['result'], test_data)
        f1_score = 2 * (precision_estimate * recall_estimate) / (precision_estimate + recall_estimate) if (precision_estimate + recall_estimate) > 0 else 0
        
        benchmark_result = BenchmarkResult(
            algorithm_name=algorithm_name,
            dataset_size=dataset_size,
            processing_time=avg_time,
            memory_peak_mb=avg_memory,
            total_comparisons=int(avg_comparisons),
            total_matches=int(avg_matches),
            precision_estimate=precision_estimate,
            recall_estimate=recall_estimate,
            f1_score=f1_score,
            comparisons_per_second=comparisons_per_second,
            authors_per_second=authors_per_second,
            timestamp=datetime.now().isoformat()
        )
        
        self.benchmark_results.append(benchmark_result)
        
        logger.info(f"✅ Benchmark completed for {algorithm_name}")
        logger.info(f"   Processing time: {avg_time:.2f}s")
        logger.info(f"   Memory peak: {avg_memory:.1f}MB")
        logger.info(f"   Matches found: {int(avg_matches)}")
        logger.info(f"   Authors/second: {authors_per_second:.1f}")
        
        return benchmark_result
    
    def _estimate_precision(self, result, test_data) -> float:
        """Estimate precision using heuristics."""
        # This is a simplified estimation
        # In practice, you'd need ground truth data
        if hasattr(result, 'edges'):
            edges = list(result.edges(data=True))
            if not edges:
                return 0.0
            
            high_confidence_matches = sum(1 for _, _, data in edges 
                                        if data.get('confidence', 0) > 0.9)
            return high_confidence_matches / len(edges)
        
        return 0.8  # Default estimate
    
    def _estimate_recall(self, result, test_data) -> float:
        """Estimate recall using heuristics."""
        # This is a simplified estimation
        # In practice, you'd need ground truth data
        authors_count = len(test_data.get('authors', {}))
        if authors_count == 0:
            return 0.0
        
        if hasattr(result, 'edges'):
            matches_count = len(list(result.edges()))
            # Rough estimate: assume 10-20% of authors should be matched
            expected_matches = authors_count * 0.15
            return min(1.0, matches_count / expected_matches) if expected_matches > 0 else 0.0
        
        return 0.7  # Default estimate
    
    def assess_quality(self, result, algorithm_name: str, test_data: Dict[str, Any]) -> QualityMetrics:
        """
        Assess the quality of matching results.
        
        Args:
            result: Algorithm result (usually a NetworkX graph)
            algorithm_name: Name of the algorithm
            test_data: Original test data
            
        Returns:
            QualityMetrics with detailed quality assessment
        """
        logger.info(f"🔍 Assessing quality for {algorithm_name}")
        
        quality = QualityMetrics()
        
        if not hasattr(result, 'edges'):
            logger.warning(f"Result doesn't have edges attribute for quality assessment")
            return quality
        
        edges = list(result.edges(data=True))
        authors_data = test_data.get('authors', {})
        
        for node1, node2, edge_data in edges:
            reason = edge_data.get('reason', '')
            confidence = edge_data.get('confidence', 0.0)
            
            # Categorize by match type
            if reason == 'same_orcid':
                quality.orcid_matches += 1
            elif 'identical_name' in reason or 'exact_match' in reason:
                quality.exact_name_matches += 1
            elif 'institution' in reason:
                quality.institution_overlap_matches += 1
            elif 'common_works' in reason:
                quality.work_overlap_matches += 1
            
            # Categorize by confidence
            if confidence >= 0.9:
                quality.high_confidence_matches += 1
            elif confidence >= 0.7:
                quality.medium_confidence_matches += 1
            else:
                quality.low_confidence_matches += 1
            
            # Check for potential false positives (very different authors)
            author1 = authors_data.get(node1, {})
            author2 = authors_data.get(node2, {})
            
            if self._is_potential_false_positive(author1, author2, edge_data):
                quality.potential_false_positives += 1
        
        # Estimate false negatives (this is very rough)
        quality.potential_false_negatives = self._estimate_false_negatives(result, test_data)
        
        self.quality_assessments[algorithm_name] = quality
        
        logger.info(f"✅ Quality assessment completed for {algorithm_name}")
        logger.info(f"   High confidence matches: {quality.high_confidence_matches}")
        logger.info(f"   ORCID matches: {quality.orcid_matches}")
        logger.info(f"   Exact name matches: {quality.exact_name_matches}")
        logger.info(f"   Potential false positives: {quality.potential_false_positives}")
        
        return quality
    
    def _is_potential_false_positive(self, author1: Dict, author2: Dict, edge_data: Dict) -> bool:
        """Check if a match might be a false positive."""
        # Very basic heuristics - in practice you'd want more sophisticated checks
        
        # Different countries with low confidence
        countries1 = set(author1.get('countries', []))
        countries2 = set(author2.get('countries', []))
        if countries1 and countries2 and not countries1.intersection(countries2):
            if edge_data.get('confidence', 0) < 0.8:
                return True
        
        # Very different citation counts
        citations1 = author1.get('cited_by_count', 0)
        citations2 = author2.get('cited_by_count', 0)
        if citations1 > 0 and citations2 > 0:
            ratio = max(citations1, citations2) / min(citations1, citations2)
            if ratio > 10 and edge_data.get('confidence', 0) < 0.9:
                return True
        
        return False
    
    def _estimate_false_negatives(self, result, test_data: Dict[str, Any]) -> int:
        """Rough estimation of false negatives."""
        # This is a very rough estimate
        # In practice, you'd need ground truth or manual validation
        
        authors_count = len(test_data.get('authors', {}))
        matches_found = len(list(result.edges())) if hasattr(result, 'edges') else 0
        
        # Assume roughly 10-20% of authors should have duplicates
        expected_matches = int(authors_count * 0.15)
        
        return max(0, expected_matches - matches_found)
    
    def compare_algorithms(self) -> pd.DataFrame:
        """
        Compare all benchmarked algorithms.
        
        Returns:
            DataFrame with comparison metrics
        """
        if not self.benchmark_results:
            logger.warning("No benchmark results to compare")
            return pd.DataFrame()
        
        comparison_data = []
        for result in self.benchmark_results:
            comparison_data.append(result.to_dict())
        
        df = pd.DataFrame(comparison_data)
        
        # Add efficiency scores
        if len(df) > 0:
            df['efficiency_score'] = (df['f1_score'] * df['authors_per_second']) / df['memory_peak_mb']
            df['speed_rank'] = df['authors_per_second'].rank(ascending=False)
            df['quality_rank'] = df['f1_score'].rank(ascending=False)
            df['memory_rank'] = df['memory_peak_mb'].rank(ascending=True)  # Lower is better
        
        return df
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        Generate a comprehensive performance report.
        
        Args:
            output_file: Optional file path to save the report
            
        Returns:
            String containing the report
        """
        if output_file is None:
            output_file = self.output_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        report_lines = [
            "=" * 80,
            "AUTHOR MATCHING PERFORMANCE ANALYSIS REPORT",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total algorithms benchmarked: {len(self.benchmark_results)}",
            ""
        ]
        
        if self.benchmark_results:
            comparison_df = self.compare_algorithms()
            
            # Summary statistics
            report_lines.extend([
                "PERFORMANCE SUMMARY",
                "-" * 40,
                f"Fastest algorithm: {comparison_df.loc[comparison_df['authors_per_second'].idxmax(), 'algorithm_name']}",
                f"Most accurate algorithm: {comparison_df.loc[comparison_df['f1_score'].idxmax(), 'algorithm_name']}",
                f"Most efficient algorithm: {comparison_df.loc[comparison_df['efficiency_score'].idxmax(), 'algorithm_name']}",
                ""
            ])
            
            # Detailed results
            report_lines.extend([
                "DETAILED RESULTS",
                "-" * 40
            ])
            
            for result in self.benchmark_results:
                report_lines.extend([
                    f"Algorithm: {result.algorithm_name}",
                    f"  Dataset size: {result.dataset_size:,} authors",
                    f"  Processing time: {result.processing_time:.2f}s",
                    f"  Memory peak: {result.memory_peak_mb:.1f}MB",
                    f"  Total matches: {result.total_matches:,}",
                    f"  Authors/second: {result.authors_per_second:.1f}",
                    f"  F1 Score: {result.f1_score:.3f}",
                    f"  Precision estimate: {result.precision_estimate:.3f}",
                    f"  Recall estimate: {result.recall_estimate:.3f}",
                    ""
                ])
            
            # Quality assessment
            if self.quality_assessments:
                report_lines.extend([
                    "QUALITY ASSESSMENT",
                    "-" * 40
                ])
                
                for algo_name, quality in self.quality_assessments.items():
                    report_lines.extend([
                        f"Algorithm: {algo_name}",
                        f"  ORCID matches: {quality.orcid_matches}",
                        f"  Exact name matches: {quality.exact_name_matches}",
                        f"  Institution matches: {quality.institution_overlap_matches}",
                        f"  Work overlap matches: {quality.work_overlap_matches}",
                        f"  High confidence: {quality.high_confidence_matches}",
                        f"  Medium confidence: {quality.medium_confidence_matches}",
                        f"  Low confidence: {quality.low_confidence_matches}",
                        f"  Potential false positives: {quality.potential_false_positives}",
                        ""
                    ])
        
        report_text = "\n".join(report_lines)
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        logger.info(f"📋 Performance report saved to: {output_file}")
        
        return report_text
    
    def plot_comparison(self, save_path: Optional[str] = None):
        """Create comparison plots for the benchmarked algorithms."""
        if not self.benchmark_results:
            logger.warning("No benchmark results to plot")
            return
        
        df = self.compare_algorithms()
        
        if save_path is None:
            save_path = self.output_dir / f"performance_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        # Create subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Speed comparison
        ax1.bar(df['algorithm_name'], df['authors_per_second'])
        ax1.set_title('Processing Speed (Authors/Second)')
        ax1.set_ylabel('Authors/Second')
        ax1.tick_params(axis='x', rotation=45)
        
        # Memory usage
        ax2.bar(df['algorithm_name'], df['memory_peak_mb'])
        ax2.set_title('Memory Usage (MB)')
        ax2.set_ylabel('Memory (MB)')
        ax2.tick_params(axis='x', rotation=45)
        
        # Quality scores
        ax3.bar(df['algorithm_name'], df['f1_score'])
        ax3.set_title('F1 Score')
        ax3.set_ylabel('F1 Score')
        ax3.tick_params(axis='x', rotation=45)
        
        # Efficiency (composite score)
        ax4.bar(df['algorithm_name'], df['efficiency_score'])
        ax4.set_title('Efficiency Score (F1 * Speed / Memory)')
        ax4.set_ylabel('Efficiency Score')
        ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"📊 Comparison plots saved to: {save_path}")
    
    def export_results(self, format: str = 'json') -> str:
        """
        Export benchmark results in specified format.
        
        Args:
            format: Export format ('json', 'csv', 'excel')
            
        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format.lower() == 'json':
            output_file = self.output_dir / f"benchmark_results_{timestamp}.json"
            
            export_data = {
                'benchmark_results': [result.to_dict() for result in self.benchmark_results],
                'quality_assessments': {k: asdict(v) for k, v in self.quality_assessments.items()},
                'export_timestamp': datetime.now().isoformat()
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
                
        elif format.lower() == 'csv':
            output_file = self.output_dir / f"benchmark_results_{timestamp}.csv"
            df = self.compare_algorithms()
            df.to_csv(output_file, index=False)
            
        elif format.lower() == 'excel':
            output_file = self.output_dir / f"benchmark_results_{timestamp}.xlsx"
            df = self.compare_algorithms()
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Benchmark Results', index=False)
                
                if self.quality_assessments:
                    quality_df = pd.DataFrame([
                        {'algorithm': k, **asdict(v)} 
                        for k, v in self.quality_assessments.items()
                    ])
                    quality_df.to_excel(writer, sheet_name='Quality Assessment', index=False)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"📁 Results exported to: {output_file}")
        return str(output_file)
