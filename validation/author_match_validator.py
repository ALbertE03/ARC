#!/usr/bin/env python
"""
Author Matching Validation and Quality Assessment
================================================

This module provides tools for validating and assessing the quality
of author matching results.
"""

import json
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Set, Optional, Any
from collections import defaultdict, Counter
from dataclasses import dataclass
import networkx as nx
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Results from author matching validation."""
    total_matches: int
    high_confidence_matches: int
    medium_confidence_matches: int
    low_confidence_matches: int
    potential_false_positives: int
    potential_false_negatives: int
    validation_score: float
    quality_indicators: Dict[str, Any]


class AuthorMatchValidator:
    """
    Comprehensive validator for author matching results.
    
    Provides various validation methods:
    - Statistical validation
    - Heuristic quality checks
    - Cross-validation with external data
    - Manual validation sampling
    """
    
    def __init__(self):
        """Initialize the validator."""
        self.validation_rules = self._initialize_validation_rules()
        logger.info("🔍 Author Match Validator initialized")
    
    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """Initialize validation rules and thresholds."""
        return {
            'name_similarity_threshold': 0.8,
            'institution_overlap_weight': 0.3,
            'country_mismatch_penalty': 0.5,
            'citation_ratio_threshold': 10.0,
            'work_overlap_bonus': 0.2,
            'orcid_match_confidence': 1.0,
            'exact_name_confidence': 0.95,
            'fuzzy_match_confidence': 0.8
        }
    
    def validate_matching_results(self, 
                                 matching_graph: nx.Graph,
                                 authors_data: Dict[str, Any],
                                 author_work_map: Dict[str, List[str]]) -> ValidationResult:
        """
        Comprehensive validation of matching results.
        
        Args:
            matching_graph: NetworkX graph with author matches
            authors_data: Original authors data
            author_work_map: Mapping of author IDs to work IDs
            
        Returns:
            ValidationResult with detailed assessment
        """
        logger.info("🔍 Starting comprehensive validation of matching results")
        
        edges = list(matching_graph.edges(data=True))
        total_matches = len(edges)
        
        if total_matches == 0:
            logger.warning("No matches to validate")
            return ValidationResult(
                total_matches=0,
                high_confidence_matches=0,
                medium_confidence_matches=0,
                low_confidence_matches=0,
                potential_false_positives=0,
                potential_false_negatives=0,
                validation_score=0.0,
                quality_indicators={}
            )
        
        logger.info(f"   Validating {total_matches} matches...")
        
        # Initialize counters
        high_confidence = 0
        medium_confidence = 0
        low_confidence = 0
        potential_false_positives = 0
        
        quality_indicators = {
            'match_types': Counter(),
            'confidence_distribution': [],
            'suspicious_matches': [],
            'validation_details': []
        }
        
        # Validate each match
        for author1_id, author2_id, edge_data in edges:
            validation_result = self._validate_single_match(
                author1_id, author2_id, edge_data,
                authors_data, author_work_map
            )
            
            # Count by confidence level
            confidence = validation_result['confidence']
            quality_indicators['confidence_distribution'].append(confidence)
            
            if confidence >= 0.9:
                high_confidence += 1
            elif confidence >= 0.7:
                medium_confidence += 1
            else:
                low_confidence += 1
            
            # Track match types
            match_type = validation_result['match_type']
            quality_indicators['match_types'][match_type] += 1
            
            # Check for potential issues
            if validation_result['is_suspicious']:
                potential_false_positives += 1
                quality_indicators['suspicious_matches'].append({
                    'author1': author1_id,
                    'author2': author2_id,
                    'reason': validation_result['suspicious_reason'],
                    'confidence': confidence
                })
            
            quality_indicators['validation_details'].append(validation_result)
        
        # Estimate false negatives (very rough)
        potential_false_negatives = self._estimate_false_negatives(
            matching_graph, authors_data, author_work_map
        )
        
        # Calculate overall validation score
        validation_score = self._calculate_validation_score(
            high_confidence, medium_confidence, low_confidence,
            potential_false_positives, total_matches
        )
        
        result = ValidationResult(
            total_matches=total_matches,
            high_confidence_matches=high_confidence,
            medium_confidence_matches=medium_confidence,
            low_confidence_matches=low_confidence,
            potential_false_positives=potential_false_positives,
            potential_false_negatives=potential_false_negatives,
            validation_score=validation_score,
            quality_indicators=quality_indicators
        )
        
        logger.info("✅ Validation completed")
        logger.info(f"   High confidence matches: {high_confidence}")
        logger.info(f"   Medium confidence matches: {medium_confidence}")
        logger.info(f"   Low confidence matches: {low_confidence}")
        logger.info(f"   Potential false positives: {potential_false_positives}")
        logger.info(f"   Validation score: {validation_score:.3f}")
        
        return result
    
    def _validate_single_match(self,
                              author1_id: str,
                              author2_id: str,
                              edge_data: Dict[str, Any],
                              authors_data: Dict[str, Any],
                              author_work_map: Dict[str, List[str]]) -> Dict[str, Any]:
        """Validate a single author match."""
        
        author1 = authors_data.get(author1_id, {})
        author2 = authors_data.get(author2_id, {})
        
        # Basic information
        name1 = author1.get('display_name', '')
        name2 = author2.get('display_name', '')
        reason = edge_data.get('reason', '')
        original_confidence = edge_data.get('confidence', 0.0)
        
        # Calculate independent validation score
        validation_score = self._calculate_independent_confidence(
            author1, author2, author_work_map.get(author1_id, []),
            author_work_map.get(author2_id, [])
        )
        
        # Determine match type
        match_type = self._classify_match_type(reason, author1, author2)
        
        # Check for suspicious patterns
        is_suspicious, suspicious_reason = self._check_suspicious_patterns(
            author1, author2, edge_data
        )
        
        return {
            'author1_id': author1_id,
            'author2_id': author2_id,
            'author1_name': name1,
            'author2_name': name2,
            'original_confidence': original_confidence,
            'confidence': validation_score,
            'match_type': match_type,
            'reason': reason,
            'is_suspicious': is_suspicious,
            'suspicious_reason': suspicious_reason,
            'validation_notes': self._generate_validation_notes(author1, author2)
        }
    
    def _calculate_independent_confidence(self,
                                        author1: Dict[str, Any],
                                        author2: Dict[str, Any],
                                        works1: List[str],
                                        works2: List[str]) -> float:
        """Calculate confidence score independent of the original algorithm."""
        
        score = 0.0
        
        # Name similarity
        name1 = author1.get('display_name', '').lower().strip()
        name2 = author2.get('display_name', '').lower().strip()
        
        if name1 and name2:
            name_sim = fuzz.ratio(name1, name2) / 100.0
            score += name_sim * 0.4
            
            # Exact match bonus
            if name1 == name2:
                score += 0.3
        
        # ORCID match
        orcid1 = author1.get('ids', {}).get('orcid', '')
        orcid2 = author2.get('ids', {}).get('orcid', '')
        
        if orcid1 and orcid2 and orcid1 == orcid2:
            score = 1.0  # Perfect confidence for ORCID match
            return score
        
        # Institution overlap
        institutions1 = set()
        institutions2 = set()
        
        for affil in author1.get('affiliations', []):
            inst = affil.get('institution', {})
            if inst.get('id'):
                institutions1.add(inst['id'])
        
        for affil in author2.get('affiliations', []):
            inst = affil.get('institution', {})
            if inst.get('id'):
                institutions2.add(inst['id'])
        
        if institutions1 and institutions2:
            overlap = len(institutions1.intersection(institutions2))
            union = len(institutions1.union(institutions2))
            if union > 0:
                score += (overlap / union) * 0.2
        
        # Country similarity
        countries1 = set(author1.get('countries', []))
        countries2 = set(author2.get('countries', []))
        
        if countries1 and countries2:
            if countries1.intersection(countries2):
                score += 0.1
            else:
                score -= 0.1  # Penalty for different countries
        
        # Work overlap
        works_set1 = set(works1)
        works_set2 = set(works2)
        common_works = works_set1.intersection(works_set2)
        
        if common_works:
            # Bonus for shared works
            overlap_ratio = len(common_works) / max(len(works_set1), len(works_set2))
            score += overlap_ratio * 0.3
        
        # Citation count similarity
        citations1 = author1.get('cited_by_count', 0)
        citations2 = author2.get('cited_by_count', 0)
        
        if citations1 > 0 and citations2 > 0:
            ratio = min(citations1, citations2) / max(citations1, citations2)
            if ratio < 0.1:  # Very different citation counts
                score -= 0.1
            elif ratio > 0.5:  # Similar citation counts
                score += 0.05
        
        return min(1.0, max(0.0, score))
    
    def _classify_match_type(self, reason: str, author1: Dict, author2: Dict) -> str:
        """Classify the type of match."""
        if 'orcid' in reason.lower():
            return 'ORCID'
        elif 'identical' in reason.lower() or 'exact' in reason.lower():
            return 'Exact Name'
        elif 'institution' in reason.lower():
            return 'Institution'
        elif 'works' in reason.lower():
            return 'Work Overlap'
        elif 'fuzzy' in reason.lower() or 'similar' in reason.lower():
            return 'Fuzzy Match'
        else:
            return 'Other'
    
    def _check_suspicious_patterns(self,
                                  author1: Dict[str, Any],
                                  author2: Dict[str, Any],
                                  edge_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check for patterns that might indicate false positives."""
        
        # Very different citation counts
        citations1 = author1.get('cited_by_count', 0)
        citations2 = author2.get('cited_by_count', 0)
        
        if citations1 > 0 and citations2 > 0:
            ratio = max(citations1, citations2) / min(citations1, citations2)
            if ratio > self.validation_rules['citation_ratio_threshold']:
                return True, f"Very different citation counts: {citations1} vs {citations2}"
        
        # Different countries with low confidence
        countries1 = set(author1.get('countries', []))
        countries2 = set(author2.get('countries', []))
        
        if (countries1 and countries2 and 
            not countries1.intersection(countries2) and
            edge_data.get('confidence', 0) < 0.8):
            return True, f"Different countries with low confidence: {countries1} vs {countries2}"
        
        # Very different names with medium confidence
        name1 = author1.get('display_name', '').lower()
        name2 = author2.get('display_name', '').lower()
        
        if name1 and name2:
            name_sim = fuzz.ratio(name1, name2) / 100.0
            if (name_sim < 0.6 and 
                edge_data.get('confidence', 0) > 0.7):
                return True, f"Very different names: '{name1}' vs '{name2}'"
        
        return False, ""
    
    def _generate_validation_notes(self, author1: Dict, author2: Dict) -> List[str]:
        """Generate validation notes for the match."""
        notes = []
        
        # Name comparison
        name1 = author1.get('display_name', '')
        name2 = author2.get('display_name', '')
        if name1 and name2:
            similarity = fuzz.ratio(name1, name2)
            notes.append(f"Name similarity: {similarity}%")
        
        # Institution overlap
        institutions1 = [affil.get('institution', {}).get('display_name', '') 
                        for affil in author1.get('affiliations', [])]
        institutions2 = [affil.get('institution', {}).get('display_name', '') 
                        for affil in author2.get('affiliations', [])]
        
        common_institutions = set(institutions1).intersection(set(institutions2))
        if common_institutions:
            notes.append(f"Shared institutions: {', '.join(common_institutions)}")
        
        # Citation comparison
        citations1 = author1.get('cited_by_count', 0)
        citations2 = author2.get('cited_by_count', 0)
        notes.append(f"Citations: {citations1} vs {citations2}")
        
        return notes
    
    def _estimate_false_negatives(self,
                                 matching_graph: nx.Graph,
                                 authors_data: Dict[str, Any],
                                 author_work_map: Dict[str, List[str]]) -> int:
        """Estimate the number of false negatives (missed matches)."""
        
        # This is a very rough estimation
        # In practice, this would require ground truth data
        
        total_authors = len(authors_data)
        matches_found = len(matching_graph.edges())
        
        # Look for obvious missed matches
        missed_matches = 0
        
        # Check for exact name matches that weren't caught
        name_groups = defaultdict(list)
        for author_id, author_data in authors_data.items():
            name = author_data.get('display_name', '').lower().strip()
            if name:
                name_groups[name].append(author_id)
        
        for name, author_ids in name_groups.items():
            if len(author_ids) > 1:
                # Check if all pairs are connected in the graph
                for i, author1 in enumerate(author_ids):
                    for author2 in author_ids[i+1:]:
                        if not matching_graph.has_edge(author1, author2):
                            missed_matches += 1
        
        return missed_matches
    
    def _calculate_validation_score(self,
                                   high_confidence: int,
                                   medium_confidence: int,
                                   low_confidence: int,
                                   potential_false_positives: int,
                                   total_matches: int) -> float:
        """Calculate an overall validation score."""
        
        if total_matches == 0:
            return 0.0
        
        # Weight by confidence levels
        weighted_score = (
            high_confidence * 1.0 +
            medium_confidence * 0.7 +
            low_confidence * 0.4
        ) / total_matches
        
        # Penalty for false positives
        false_positive_penalty = potential_false_positives / total_matches * 0.5
        
        final_score = max(0.0, weighted_score - false_positive_penalty)
        
        return final_score
    
    def generate_validation_report(self, 
                                  validation_result: ValidationResult,
                                  output_file: Optional[str] = None) -> str:
        """Generate a detailed validation report."""
        
        lines = [
            "=" * 80,
            "AUTHOR MATCHING VALIDATION REPORT",
            "=" * 80,
            f"Generated: {pd.Timestamp.now()}",
            "",
            "SUMMARY STATISTICS",
            "-" * 40,
            f"Total matches validated: {validation_result.total_matches:,}",
            f"High confidence matches: {validation_result.high_confidence_matches:,} "
            f"({validation_result.high_confidence_matches/validation_result.total_matches*100:.1f}%)",
            f"Medium confidence matches: {validation_result.medium_confidence_matches:,} "
            f"({validation_result.medium_confidence_matches/validation_result.total_matches*100:.1f}%)",
            f"Low confidence matches: {validation_result.low_confidence_matches:,} "
            f"({validation_result.low_confidence_matches/validation_result.total_matches*100:.1f}%)",
            f"Potential false positives: {validation_result.potential_false_positives:,}",
            f"Potential false negatives: {validation_result.potential_false_negatives:,}",
            f"Overall validation score: {validation_result.validation_score:.3f}",
            "",
            "MATCH TYPE BREAKDOWN",
            "-" * 40
        ]
        
        # Add match type statistics
        match_types = validation_result.quality_indicators.get('match_types', {})
        for match_type, count in match_types.most_common():
            percentage = count / validation_result.total_matches * 100
            lines.append(f"{match_type}: {count:,} ({percentage:.1f}%)")
        
        lines.extend([
            "",
            "CONFIDENCE DISTRIBUTION",
            "-" * 40
        ])
        
        # Add confidence distribution
        confidences = validation_result.quality_indicators.get('confidence_distribution', [])
        if confidences:
            lines.extend([
                f"Mean confidence: {np.mean(confidences):.3f}",
                f"Median confidence: {np.median(confidences):.3f}",
                f"Standard deviation: {np.std(confidences):.3f}",
                f"Min confidence: {np.min(confidences):.3f}",
                f"Max confidence: {np.max(confidences):.3f}"
            ])
        
        # Add suspicious matches
        suspicious = validation_result.quality_indicators.get('suspicious_matches', [])
        if suspicious:
            lines.extend([
                "",
                "SUSPICIOUS MATCHES (POTENTIAL FALSE POSITIVES)",
                "-" * 40
            ])
            
            for i, match in enumerate(suspicious[:10]):  # Show first 10
                lines.append(f"{i+1}. Authors {match['author1']} <-> {match['author2']}")
                lines.append(f"   Reason: {match['reason']}")
                lines.append(f"   Confidence: {match['confidence']:.3f}")
                lines.append("")
        
        report_text = "\n".join(lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"📋 Validation report saved to: {output_file}")
        
        return report_text
    
    def export_validation_results(self,
                                 validation_result: ValidationResult,
                                 format: str = 'json',
                                 output_file: Optional[str] = None) -> str:
        """Export validation results in specified format."""
        
        if output_file is None:
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"validation_results_{timestamp}.{format}"
        
        if format.lower() == 'json':
            export_data = {
                'validation_summary': {
                    'total_matches': validation_result.total_matches,
                    'high_confidence_matches': validation_result.high_confidence_matches,
                    'medium_confidence_matches': validation_result.medium_confidence_matches,
                    'low_confidence_matches': validation_result.low_confidence_matches,
                    'potential_false_positives': validation_result.potential_false_positives,
                    'potential_false_negatives': validation_result.potential_false_negatives,
                    'validation_score': validation_result.validation_score
                },
                'quality_indicators': validation_result.quality_indicators,
                'export_timestamp': pd.Timestamp.now().isoformat()
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
        
        elif format.lower() == 'csv':
            # Export validation details to CSV
            details = validation_result.quality_indicators.get('validation_details', [])
            if details:
                df = pd.DataFrame(details)
                df.to_csv(output_file, index=False)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"📁 Validation results exported to: {output_file}")
        return output_file
