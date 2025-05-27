#!/usr/bin/env python
"""
Enhanced Author Matcher with Performance Metrics and Improved Algorithms
========================================================================

This module provides an advanced author matching system with:
- Multiple similarity algorithms
- Performance benchmarking and metrics
- Optimized processing strategies
- Comprehensive evaluation tools
"""

import networkx as nx
import logging
import itertools
import time
import json
import hashlib
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Set, Optional, Any
from tqdm import tqdm
from rapidfuzz import fuzz, process
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
import spacy
from spacy.lang.en.stop_words import STOP_WORDS

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Data class to store performance metrics."""
    total_authors: int = 0
    total_comparisons: int = 0
    total_edges: int = 0
    processing_time: float = 0.0
    memory_usage_mb: float = 0.0
    
    # Algorithm-specific metrics
    exact_matches: int = 0
    fuzzy_matches: int = 0
    orcid_matches: int = 0
    institution_matches: int = 0
    work_overlap_matches: int = 0
    
    # Quality metrics
    precision_estimate: float = 0.0
    recall_estimate: float = 0.0
    f1_score_estimate: float = 0.0
    
    # Processing efficiency
    comparisons_per_second: float = 0.0
    authors_per_second: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for easy serialization."""
        return asdict(self)


class EnhancedAuthorMatcher:
    """
    Enhanced Author Matcher with advanced algorithms and comprehensive metrics.
    
    Features:
    - Multiple similarity algorithms (fuzzy, semantic, phonetic)
    - Performance monitoring and benchmarking
    - Optimized batch processing
    - Comprehensive evaluation metrics
    - Memory-efficient processing for large datasets
    """

    def __init__(self, 
                 similarity_threshold: float = 0.95,  # Reduced from 0.90 to be more inclusive
                 batch_size: int = 1000,
                 use_semantic_similarity: bool = True,
                 use_phonetic_matching: bool = True,
                 enable_caching: bool = True,
                 exhaustive_comparison: bool = True,  # Changed: Enable N×N comparison by default
                 hyphen_aware_matching: bool = True):  # New: Enhanced hyphen handling
        """
        Initialize the enhanced author matcher.
        
        Args:
            similarity_threshold: Minimum similarity score for matching (default: 0.75)
            batch_size: Size of batches for processing
            use_semantic_similarity: Enable TF-IDF based semantic matching
            use_phonetic_matching: Enable phonetic matching algorithms
            enable_caching: Enable caching of computed similarities
            exhaustive_comparison: If True, compare all pairs (N×N), slower but more complete
            hyphen_aware_matching: Enhanced matching for names with hyphens and variations
        """
        logger.info("🚀 Initializing Enhanced Author Matcher...")
        
        self.similarity_threshold = similarity_threshold
        self.batch_size = batch_size
        self.use_semantic_similarity = use_semantic_similarity
        self.use_phonetic_matching = use_phonetic_matching
        self.enable_caching = enable_caching
        self.exhaustive_comparison = exhaustive_comparison
        self.hyphen_aware_matching = hyphen_aware_matching
        
        # Initialize vectorizers for semantic similarity
        if self.use_semantic_similarity:
            self.char_vectorizer = TfidfVectorizer(
                analyzer="char_wb", 
                ngram_range=(2, 4), 
                min_df=1, 
                max_df=0.8,
                max_features=5000
            )
            
            self.word_vectorizer = TfidfVectorizer(
                analyzer="word", 
                ngram_range=(1, 2), 
                min_df=1, 
                max_df=0.8,
                max_features=5000
            )
        
        # Caching systems
        self.similarity_cache = {} if enable_caching else None
        self.name_normalization_cache = {} if enable_caching else None
        
        # Initialize spaCy and phonetic components
        self._init_nlp_components()
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        self.start_time = None
        
        # Phonetic matching patterns
        if self.use_phonetic_matching:
            self._init_phonetic_patterns()
        
        logger.info("✅ Enhanced Author Matcher initialized successfully")
        logger.info(f"   Semantic similarity: {use_semantic_similarity}")
        logger.info(f"   Phonetic matching: {use_phonetic_matching}")
        logger.info(f"   Caching enabled: {enable_caching}")
        logger.info(f"   Similarity threshold: {similarity_threshold}")
        logger.info(f"   Exhaustive comparison: {exhaustive_comparison}")
        logger.info(f"   Hyphen-aware matching: {hyphen_aware_matching}")

    def _init_nlp_components(self):
        """Initialize spaCy NLP components for advanced phonetic processing."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✅ spaCy English model loaded successfully")
        except OSError:
            logger.warning("⚠️  spaCy English model not found, falling back to basic patterns")
            self.nlp = None
    
    def _init_phonetic_patterns(self):
        """Initialize phonetic matching patterns for better name matching."""
        # Enhanced phonetic substitutions with more comprehensive coverage
        self.phonetic_substitutions = {
            'ph': 'f', 'gh': 'f', 'ck': 'k', 'qu': 'kw', 'x': 'ks', 'z': 's',
            'c': 'k',  # Context-dependent, but common
            'th': 't', 'sh': 's', 'ch': 's',  # Common sound simplifications
            'sch': 's', 'tch': 't',  # German/Dutch influences
            'tion': 'sion', 'sion': 'sion',  # Suffix normalization
        }
        
        # Enhanced vowel simplification patterns
        self.vowel_patterns = {
            'ae': 'e', 'ai': 'e', 'ay': 'e', 'ea': 'e', 'ee': 'e', 'ei': 'e',
            'ey': 'e', 'ie': 'e', 'oe': 'e', 'oo': 'u', 'ou': 'u', 'ow': 'u',
            'ue': 'u', 'ui': 'u', 'au': 'o', 'aw': 'o', 'eu': 'u', 'ew': 'u'
        }
        
        # Common international name variations
        self.international_patterns = {
            'josé': 'jose', 'maría': 'maria', 'joão': 'joao', 'josé': 'jose',
            'müller': 'muller', 'françois': 'francois', 'björn': 'bjorn',
            'josé-antonio': 'jose-antonio', 'jean-claude': 'jean-claude'
        }

    def normalize_name_advanced(self, name: str) -> str:
        """
        Advanced name normalization with caching and multiple strategies.
        
        Args:
            name: Raw name string
            
        Returns:
            Normalized name string
        """
        if not name:
            return ""
        
        # Check cache first
        if self.enable_caching and name in self.name_normalization_cache:
            return self.name_normalization_cache[name]
        
        # Advanced normalization pipeline
        normalized = name.lower().strip()
        
        # Remove common prefixes and suffixes
        prefixes = ['dr.', 'prof.', 'mr.', 'mrs.', 'ms.', 'phd', 'md']
        suffixes = ['jr.', 'sr.', 'ii', 'iii', 'phd', 'md', 'ph.d.', 'm.d.']
        
        words = normalized.split()
        cleaned_words = []
        
        for word in words:
            # Remove punctuation except hyphens
            word = re.sub(r'[^\w\s\-]', '', word)
            
            # Skip prefixes and suffixes
            if word not in prefixes and word not in suffixes:
                cleaned_words.append(word)
        
        normalized = ' '.join(cleaned_words)
        
        # Handle hyphenated names consistently
        normalized = re.sub(r'\s*-\s*', '-', normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Cache result
        if self.enable_caching:
            self.name_normalization_cache[name] = normalized
        
        return normalized

    def _normalize_hyphens(self, name: str) -> str:
        """Enhanced hyphen normalization for better matching."""
        if not name:
            return ""
        
        # Standardize different types of dashes to regular hyphens
        name = re.sub(r'[–—−]', '-', name)
        
        # Normalize spaces around hyphens: "María - José" -> "maría-josé"
        name = re.sub(r'\s*-\s*', '-', name)
        
        # Remove multiple consecutive hyphens
        name = re.sub(r'-+', '-', name)
        
        # Remove leading/trailing hyphens
        name = name.strip('-')
        
        return name
    
    def _apply_phonetic_normalization(self, name: str) -> str:
        """Apply phonetic normalizations for better matching."""
        if not name:
            return ""
        
        # Apply phonetic substitutions
        for pattern, replacement in self.phonetic_substitutions.items():
            name = name.replace(pattern, replacement)
        
        # Apply vowel simplifications
        for pattern, replacement in self.vowel_patterns.items():
            name = name.replace(pattern, replacement)
        
        return name
    
    def phonetic_similarity(self, name1: str, name2: str) -> float:
        """
        Enhanced phonetic similarity using spaCy NLP features.
        
        Args:
            name1, name2: Names to compare
            
        Returns:
            Phonetic similarity score (0.0 to 1.0)
        """
        if not self.use_phonetic_matching or not name1 or not name2:
            return 0.0
        
        # Use spaCy-enhanced phonetic processing if available
        if self.nlp:
            return self._spacy_phonetic_similarity(name1, name2)
        else:
            # Fallback to enhanced pattern-based approach
            return self._pattern_phonetic_similarity(name1, name2)
    
    def _spacy_phonetic_similarity(self, name1: str, name2: str) -> float:
        """spaCy-enhanced phonetic similarity with linguistic analysis."""
        try:
            # Process names with spaCy
            doc1 = self.nlp(name1.lower())
            doc2 = self.nlp(name2.lower())
            
            # Extract linguistic features
            tokens1 = [token.lemma_ for token in doc1 if token.is_alpha]
            tokens2 = [token.lemma_ for token in doc2 if token.is_alpha]
            
            # Apply phonetic transformations to lemmatized tokens
            phon_tokens1 = []
            phon_tokens2 = []
            
            for token in tokens1:
                phon_token = self._apply_enhanced_phonetic_transform(token)
                phon_tokens1.append(phon_token)
            
            for token in tokens2:
                phon_token = self._apply_enhanced_phonetic_transform(token)
                phon_tokens2.append(phon_token)
            
            # Reconstruct phonetic names
            phon_name1 = ' '.join(phon_tokens1)
            phon_name2 = ' '.join(phon_tokens2)
            
            # Calculate multiple similarity scores
            similarities = []
            
            # 1. Token-level similarity (considering word order)
            similarities.append(fuzz.ratio(phon_name1, phon_name2) / 100.0)
            
            # 2. Token set similarity (ignoring order)
            similarities.append(fuzz.token_set_ratio(phon_name1, phon_name2) / 100.0)
            
            # 3. Character-level similarity on concatenated phonetic tokens
            concat1 = ''.join(phon_tokens1)
            concat2 = ''.join(phon_tokens2)
            similarities.append(fuzz.ratio(concat1, concat2) / 100.0)
            
            # 4. Soundex-like similarity (first letter + phonetic core)
            if phon_tokens1 and phon_tokens2:
                core1 = phon_tokens1[0][0] + ''.join(phon_tokens1)[1:] if phon_tokens1[0] else ''
                core2 = phon_tokens2[0][0] + ''.join(phon_tokens2)[1:] if phon_tokens2[0] else ''
                if core1 and core2:
                    similarities.append(fuzz.ratio(core1, core2) / 100.0)
            
            # 5. International name pattern matching
            intl_sim = self._international_name_similarity(name1, name2)
            if intl_sim > 0:
                similarities.append(intl_sim)
            
            # Return weighted average with emphasis on best matches
            if similarities:
                # Weight the highest similarities more heavily
                similarities.sort(reverse=True)
                if len(similarities) >= 3:
                    # Weighted: 50% best, 30% second best, 20% third best
                    return (0.5 * similarities[0] + 
                           0.3 * similarities[1] + 
                           0.2 * similarities[2])
                elif len(similarities) == 2:
                    return 0.7 * similarities[0] + 0.3 * similarities[1]
                else:
                    return similarities[0]
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"spaCy phonetic similarity failed: {e}, falling back to patterns")
            return self._pattern_phonetic_similarity(name1, name2)
    
    def _pattern_phonetic_similarity(self, name1: str, name2: str) -> float:
        """Enhanced pattern-based phonetic similarity (fallback)."""
        def phonetic_transform(name):
            """Enhanced phonetic transformation."""
            name = name.lower()
            
            # Apply international patterns first
            for pattern, replacement in self.international_patterns.items():
                name = name.replace(pattern, replacement)
            
            # Apply phonetic substitutions
            for pattern, replacement in self.phonetic_substitutions.items():
                name = name.replace(pattern, replacement)
            
            # Apply vowel simplifications
            for pattern, replacement in self.vowel_patterns.items():
                name = name.replace(pattern, replacement)
            
            # Remove consecutive duplicate letters
            name = re.sub(r'(.)\1+', r'\1', name)
            
            # Remove silent letters at the end
            name = re.sub(r'[aeiouy]+$', '', name)
            
            return name
        
        phon1 = phonetic_transform(name1)
        phon2 = phonetic_transform(name2)
        
        # Multiple similarity measurements
        ratio_sim = fuzz.ratio(phon1, phon2) / 100.0
        token_sim = fuzz.token_set_ratio(phon1, phon2) / 100.0
        
        # Check international name patterns
        intl_sim = self._international_name_similarity(name1, name2)
        
        # Return best similarity
        return max(ratio_sim, token_sim, intl_sim)
    
    def _apply_enhanced_phonetic_transform(self, token: str) -> str:
        """Apply enhanced phonetic transformation to a single token."""
        if not token:
            return ""
        
        # Start with the token
        phon = token.lower()
        
        # Apply international patterns first
        for pattern, replacement in self.international_patterns.items():
            phon = phon.replace(pattern, replacement)
        
        # Apply phonetic substitutions
        for pattern, replacement in self.phonetic_substitutions.items():
            phon = phon.replace(pattern, replacement)
        
        # Apply vowel simplifications
        for pattern, replacement in self.vowel_patterns.items():
            phon = phon.replace(pattern, replacement)
        
        # Remove consecutive duplicate letters
        phon = re.sub(r'(.)\1+', r'\1', phon)
        
        # Keep first letter, reduce vowels in the middle
        if len(phon) > 1:
            first_char = phon[0]
            rest = phon[1:]
            # Simplify vowel clusters in the middle
            rest = re.sub(r'[aeiouy]+', 'a', rest)
            phon = first_char + rest
        
        return phon
    
    def _international_name_similarity(self, name1: str, name2: str) -> float:
        """Check for international name variations."""
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        # Direct international pattern match
        for pattern, normalized in self.international_patterns.items():
            if pattern in name1_lower and normalized in name2_lower:
                return 0.95
            if pattern in name2_lower and normalized in name1_lower:
                return 0.95
        
        # Common substitutions for accented characters
        accent_map = {
            'á': 'a', 'à': 'a', 'â': 'a', 'ä': 'a', 'ã': 'a',
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
            'ó': 'o', 'ò': 'o', 'ô': 'o', 'ö': 'o', 'õ': 'o',
            'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
            'ñ': 'n', 'ç': 'c', 'ß': 'ss'
        }
        
        # Remove accents and compare
        deaccent1 = name1_lower
        deaccent2 = name2_lower
        
        for accented, plain in accent_map.items():
            deaccent1 = deaccent1.replace(accented, plain)
            deaccent2 = deaccent2.replace(accented, plain)
        
        if deaccent1 == deaccent2 and deaccent1 != name1_lower:
            return 0.90
        
        # Partial accent similarity
        accent_sim = fuzz.ratio(deaccent1, deaccent2) / 100.0
        if accent_sim > 0.85 and (deaccent1 != name1_lower or deaccent2 != name2_lower):
            return accent_sim * 0.9  # Slight penalty for accent differences
        
        return 0.0

    def semantic_similarity(self, names: List[str]) -> np.ndarray:
        """
        Calculate semantic similarity matrix for a list of names.
        
        Args:
            names: List of names to compare
            
        Returns:
            Similarity matrix
        """
        if not self.use_semantic_similarity or len(names) < 2:
            return np.zeros((len(names), len(names)))
        
        try:
            # Character-level similarity
            char_vectors = self.char_vectorizer.fit_transform(names)
            char_similarity = cosine_similarity(char_vectors)
            
            # Word-level similarity
            word_vectors = self.word_vectorizer.fit_transform(names)
            word_similarity = cosine_similarity(word_vectors)
            
            # Combine similarities with weights
            combined_similarity = 0.6 * char_similarity + 0.4 * word_similarity
            
            return combined_similarity
            
        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}")
            return np.zeros((len(names), len(names)))

    def calculate_comprehensive_similarity(self, author1: Dict, author2: Dict) -> Tuple[float, Dict[str, float]]:
        """
        Calculate comprehensive similarity between two authors using multiple algorithms.
        
        Args:
            author1, author2: Author feature dictionaries
            
        Returns:
            Overall similarity score and detailed breakdown
        """
        # Generate cache key
        cache_key = None
        if self.enable_caching:
            key_str = f"{author1['id']}_{author2['id']}"
            cache_key = hashlib.md5(key_str.encode()).hexdigest()
            
            if cache_key in self.similarity_cache:
                return self.similarity_cache[cache_key]
        
        name1 = author1.get('normalized_name', '')
        name2 = author2.get('normalized_name', '')
        
        if not name1 or not name2:
            result = (0.0, {})
            if cache_key:
                self.similarity_cache[cache_key] = result
            return result
        
        similarities = {}
        
        # 1. Exact name matching (including enhanced equivalence)
        similarities['exact_match'] = 1.0 if name1 == name2 else 0.0
        if not similarities['exact_match'] and self.hyphen_aware_matching:
            similarities['exact_match'] = 1.0 if self.are_names_equivalent_enhanced(name1, name2) else 0.0
        
        # 2. Fuzzy string similarities
        similarities['fuzzy_ratio'] = fuzz.ratio(name1, name2) / 100.0
        similarities['token_sort'] = fuzz.token_sort_ratio(name1, name2) / 100.0
        similarities['token_set'] = fuzz.token_set_ratio(name1, name2) / 100.0
        similarities['partial_ratio'] = fuzz.partial_ratio(name1, name2) / 100.0
        
        # 2b. Enhanced hyphen-aware comparisons
        if self.hyphen_aware_matching:
            # Compare with hyphens removed/added
            name1_no_hyphens = name1.replace('-', ' ')
            name2_no_hyphens = name2.replace('-', ' ')
            name1_with_hyphens = name1.replace(' ', '-')
            name2_with_hyphens = name2.replace(' ', '-')
            
            similarities['hyphen_removed'] = max(
                fuzz.ratio(name1_no_hyphens, name2) / 100.0,
                fuzz.ratio(name1, name2_no_hyphens) / 100.0,
                fuzz.ratio(name1_no_hyphens, name2_no_hyphens) / 100.0
            )
            
            similarities['hyphen_added'] = max(
                fuzz.ratio(name1_with_hyphens, name2) / 100.0,
                fuzz.ratio(name1, name2_with_hyphens) / 100.0,
                fuzz.ratio(name1_with_hyphens, name2_with_hyphens) / 100.0
            )
        else:
            similarities['hyphen_removed'] = 0.0
            similarities['hyphen_added'] = 0.0
        
        # 3. Phonetic similarity
        if self.use_phonetic_matching:
            similarities['phonetic'] = self.phonetic_similarity(name1, name2)
        
        # 4. Word overlap similarity
        words1 = set(name1.split())
        words2 = set(name2.split())
        if words1 and words2:
            common_words = words1.intersection(words2)
            similarities['word_overlap'] = len(common_words) / max(len(words1), len(words2))
        else:
            similarities['word_overlap'] = 0.0
        
        # 5. Initial similarity
        initials1 = ''.join(word[0] for word in words1 if word)
        initials2 = ''.join(word[0] for word in words2 if word)
        if initials1 and initials2:
            similarities['initials'] = fuzz.ratio(initials1, initials2) / 100.0
        else:
            similarities['initials'] = 0.0
        
        # 6. Alternative names similarity
        alt_names1 = author1.get('alt_names', [])
        alt_names2 = author2.get('alt_names', [])
        
        max_alt_sim = 0.0
        for alt1 in alt_names1:
            for alt2 in alt_names2:
                if alt1 and alt2:
                    alt_sim = fuzz.ratio(alt1, alt2) / 100.0
                    max_alt_sim = max(max_alt_sim, alt_sim)
        
        # Also check main name vs alt names
        for alt1 in alt_names1:
            if alt1:
                alt_sim = fuzz.ratio(alt1, name2) / 100.0
                max_alt_sim = max(max_alt_sim, alt_sim)
        
        for alt2 in alt_names2:
            if alt2:
                alt_sim = fuzz.ratio(name1, alt2) / 100.0
                max_alt_sim = max(max_alt_sim, alt_sim)
        
        similarities['alt_names'] = max_alt_sim
        
        # Calculate weighted overall similarity
        weights = {
            'exact_match': 0.25,
            'fuzzy_ratio': 0.15,
            'token_sort': 0.12,
            'token_set': 0.08,
            'partial_ratio': 0.04,
            'hyphen_removed': 0.08 if self.hyphen_aware_matching else 0.0,
            'hyphen_added': 0.06 if self.hyphen_aware_matching else 0.0,
            'phonetic': 0.08 if self.use_phonetic_matching else 0.0,
            'word_overlap': 0.05,
            'initials': 0.03,
            'alt_names': 0.06
        }
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v/total_weight for k, v in weights.items()}
        
        overall_similarity = sum(similarities.get(k, 0.0) * w for k, w in weights.items())
        
        result = (overall_similarity, similarities)
        
        # Cache result
        if cache_key:
            self.similarity_cache[cache_key] = result
        
        return result

    def should_consolidate_enhanced(self, author1: Dict, author2: Dict, common_works: Set) -> Tuple[bool, str, float]:
        """
        Enhanced consolidation decision with comprehensive analysis.
        
        Args:
            author1, author2: Author feature dictionaries
            common_works: Set of common work IDs
            
        Returns:
            (should_merge, reason, confidence)
        """
        # 1. ORCID matching - highest confidence
        orcid1 = author1.get('orcid', '').strip()
        orcid2 = author2.get('orcid', '').strip()
        
        if orcid1 and orcid2 and orcid1 == orcid2:
            self.metrics.orcid_matches += 1
            return True, "identical_orcid", 1.0
        
        # 2. Calculate comprehensive similarity
        overall_sim, sim_breakdown = self.calculate_comprehensive_similarity(author1, author2)
        
        # 3. Exact name match
        if sim_breakdown.get('exact_match', 0.0) == 1.0:
            self.metrics.exact_matches += 1
            return True, "identical_normalized_name", 0.98
        
        # 4. High alternative name similarity
        if sim_breakdown.get('alt_names', 0.0) >= 0.95:
            self.metrics.exact_matches += 1
            return True, "identical_alt_name", 0.95
        
        # 5. Shared works analysis
        works_evidence = False
        if common_works:
            # Strong evidence if they share works and have reasonable name similarity
            if overall_sim >= 0.7:
                self.metrics.work_overlap_matches += 1
                works_evidence = True
        
        # 6. Institution overlap analysis
        inst1 = set(author1.get('institution_ids', []))
        inst2 = set(author2.get('institution_ids', []))
        common_institutions = inst1.intersection(inst2)
        
        institution_evidence = False
        if common_institutions and overall_sim >= 0.8:
            self.metrics.institution_matches += 1
            institution_evidence = True
        
        # 7. Geographic evidence
        countries1 = set(author1.get('countries', []))
        countries2 = set(author2.get('countries', []))
        same_country = bool(countries1.intersection(countries2))
        
        # 8. Decision logic with multiple evidence sources
        confidence = overall_sim
        
        # High similarity threshold - REDUCED for more inclusive
        if overall_sim >= 0.85:  # Reduced from 0.95
            self.metrics.fuzzy_matches += 1
            return True, f"high_similarity_{overall_sim:.3f}", confidence
        
        # Medium-high similarity with supporting evidence - REDUCED thresholds
        if overall_sim >= 0.75:  # Reduced from 0.85
            if works_evidence:
                return True, f"shared_works_good_similarity_{overall_sim:.3f}", min(0.9, confidence + 0.05)
            
            if institution_evidence:
                return True, f"same_institution_good_similarity_{overall_sim:.3f}", min(0.9, confidence + 0.03)
        
        # Medium similarity with strong supporting evidence - REDUCED thresholds
        if overall_sim >= 0.65:  # Reduced from 0.75
            evidence_count = sum([works_evidence, institution_evidence, same_country])
            if evidence_count >= 2:
                return True, f"multiple_evidence_medium_similarity_{overall_sim:.3f}", min(0.85, confidence + 0.05)
        
        # Special case: Very high hyphen similarity (for names like María-José vs Maria Jose)
        if self.hyphen_aware_matching and overall_sim >= 0.60:
            hyphen_sim = max(
                sim_breakdown.get('hyphen_removed', 0.0),
                sim_breakdown.get('hyphen_added', 0.0)
            )
            if hyphen_sim >= 0.90:
                return True, f"hyphen_variation_match_{hyphen_sim:.3f}", min(0.88, confidence + 0.03)
        
        # Medium similarity with strong supporting evidence
        if overall_sim >= 0.75:
            evidence_count = sum([works_evidence, institution_evidence, same_country])
            if evidence_count >= 2:
                return True, f"multiple_evidence_medium_similarity_{overall_sim:.3f}", min(0.85, confidence + 0.05)
        
        # Conservative approach - don't merge if not confident
        return False, f"insufficient_confidence_{overall_sim:.3f}", confidence

    def extract_features_enhanced(self, author_id: str, author_data: Dict, author_work_map: Dict) -> Dict:
        """
        Extract enhanced features for an author with better processing.
        
        Args:
            author_id: Author identifier
            author_data: Raw author data
            author_work_map: Mapping of author to works
            
        Returns:
            Enhanced feature dictionary
        """
        # Basic name processing
        name = author_data.get("display_name", "").strip()
        normalized_name = self.normalize_name_advanced(name)
        
        # Alternative names processing
        alt_names = []
        for alt in author_data.get("display_name_alternatives", []):
            if alt and alt.strip():
                normalized_alt = self.normalize_name_advanced(alt.strip())
                if normalized_alt and normalized_alt != normalized_name:
                    alt_names.append(normalized_alt)
        
        # Remove duplicates while preserving order
        alt_names = list(dict.fromkeys(alt_names))
        
        # Work information
        works = author_work_map.get(author_id, [])
        
        # Affiliation processing with temporal information
        affiliations = []
        institution_ids = set()
        countries = set()
        
        for affil in author_data.get("affiliations", []):
            institution = affil.get("institution", {})
            if institution:
                institution_id = institution.get("id", "").split("/")[-1]
                institution_name = institution.get("display_name", "")
                country_code = institution.get("country_code", "")
                
                if institution_id:
                    institution_ids.add(institution_id)
                if country_code:
                    countries.add(country_code)
                
                affiliations.append({
                    "institution_id": institution_id,
                    "institution_name": institution_name,
                    "country_code": country_code,
                    "years": affil.get("years", []),
                })
        
        # Additional country information
        for country in author_data.get("countries", []):
            if country:
                countries.add(country)
        
        # Identifiers
        orcid = author_data.get("ids", {}).get("orcid", "").strip()
        
        # Name analysis
        initials = ""
        if normalized_name:
            words = normalized_name.split()
            initials = "".join(word[0] for word in words if word and word[0].isalpha())
        
        # Research topics
        topics = []
        topic_ids = set()
        for topic in author_data.get("topics", []):
            topic_id = topic.get("id", "").split("/")[-1]
            topic_name = topic.get("display_name", "")
            if topic_id and topic_name:
                topics.append({"id": topic_id, "name": topic_name})
                topic_ids.add(topic_id)
        
        # Concepts
        concepts = []
        for concept in author_data.get("x_concepts", []):
            if concept.get("display_name"):
                concepts.append(concept["display_name"])
        
        return {
            "id": author_id,
            "name": name,
            "normalized_name": normalized_name,
            "alt_names": alt_names,
            "initials": initials,
            "works_count": len(works),
            "cited_by_count": author_data.get("cited_by_count", 0),
            "works": works,
            "orcid": orcid,
            "affiliations": affiliations,
            "institution_ids": list(institution_ids),
            "countries": list(countries),
            "topics": topics,
            "topic_ids": list(topic_ids),
            "concepts": concepts,
            "h_index": author_data.get("summary_stats", {}).get("h_index", 0),
            "last_known_institutions": [
                inst.get("display_name", "")
                for inst in author_data.get("last_known_institutions", [])
                if inst.get("display_name")
            ],
            # Quality indicators
            "has_orcid": bool(orcid),
            "has_affiliations": bool(affiliations),
            "name_quality": len(normalized_name.split()) if normalized_name else 0,
            "alt_names_count": len(alt_names),
        }

    def find_candidates_optimized(self, authors_features: Dict, author_work_map: Dict) -> nx.Graph:
        """
        Optimized candidate finding with performance monitoring.
        
        Args:
            authors_features: Dictionary of author features
            author_work_map: Mapping of authors to works
            
        Returns:
            NetworkX graph with consolidation candidates
        """
        if self.exhaustive_comparison:
            logger.info("🔍 Starting EXHAUSTIVE N×N author candidate finding...")
            return self._find_candidates_exhaustive(authors_features, author_work_map)
        else:
            logger.info("🔍 Starting optimized author candidate finding...")
            return self._find_candidates_batch_optimized(authors_features, author_work_map)
    
    def _find_candidates_exhaustive(self, authors_features: Dict, author_work_map: Dict) -> nx.Graph:
        """
        Exhaustive N×N comparison - more thorough but slower.
        This ensures no potential matches are missed due to batch boundaries.
        """
        logger.info("⚠️  Using exhaustive comparison mode - this will be slower but more complete")
        self.start_time = time.time()
        
        # Initialize metrics
        self.metrics.total_authors = len(authors_features)
        
        # Create graph
        G = nx.Graph()
        
        # Add all authors as nodes
        for author_id, features in authors_features.items():
            G.add_node(author_id, **features)
        
        author_ids = list(authors_features.keys())
        total_pairs = len(author_ids) * (len(author_ids) - 1) // 2
        
        logger.info(f"   Will compare {total_pairs:,} pairs exhaustively")
        
        edges_added = 0
        comparisons_made = 0
        
        # Compare all pairs
        for i, author_id1 in enumerate(tqdm(author_ids, desc="Exhaustive comparison")):
            for j in range(i + 1, len(author_ids)):
                author_id2 = author_ids[j]
                
                author1 = authors_features[author_id1]
                author2 = authors_features[author_id2]
                
                # Calculate works overlap
                works1 = set(author_work_map.get(author_id1, []))
                works2 = set(author_work_map.get(author_id2, []))
                common_works = works1.intersection(works2)
                
                # Quick pre-filtering based on name similarity
                name1 = author1.get('normalized_name', '')
                name2 = author2.get('normalized_name', '')
                
                if name1 and name2:
                    quick_sim = fuzz.ratio(name1, name2) / 100.0
                    
                    # Only do detailed analysis if there's some potential
                    if quick_sim >= 0.6:  # Lower threshold for exhaustive mode
                        should_merge, reason, confidence = self.should_consolidate_enhanced(
                            author1, author2, common_works
                        )
                        
                        if should_merge:
                            G.add_edge(author_id1, author_id2, reason=reason, confidence=confidence)
                            edges_added += 1
                
                comparisons_made += 1
                self.metrics.total_comparisons = comparisons_made
        
        # Update metrics
        self.metrics.total_edges = G.number_of_edges()
        self.metrics.processing_time = time.time() - self.start_time
        
        if self.metrics.processing_time > 0:
            self.metrics.authors_per_second = self.metrics.total_authors / self.metrics.processing_time
            self.metrics.comparisons_per_second = self.metrics.total_comparisons / self.metrics.processing_time
        
        logger.info(f"✅ Exhaustive comparison completed: {edges_added} matches found")
        self._log_performance_summary()
        
        return G
    
    def _find_candidates_batch_optimized(self, authors_features: Dict, author_work_map: Dict) -> nx.Graph:
        """
        Original batch-optimized approach for large datasets.
        """
        self.start_time = time.time()
        
        # Initialize metrics
        self.metrics.total_authors = len(authors_features)
        
        # Create graph
        G = nx.Graph()
        
        # Add all authors as nodes
        for author_id, features in authors_features.items():
            G.add_node(author_id, **features)
        
        # Strategy 1: Exact name grouping for quick wins
        logger.info("📝 Step 1: Finding exact name matches...")
        exact_matches = self._find_exact_matches(authors_features)
        
        edges_added = 0
        for group in exact_matches.values():
            if len(group) > 1:
                for i, a1 in enumerate(group):
                    for a2 in group[i+1:]:
                        if not G.has_edge(a1, a2):
                            G.add_edge(a1, a2, reason="exact_name_match", confidence=0.98)
                            edges_added += 1
                            self.metrics.exact_matches += 1
        
        logger.info(f"   Found {edges_added} exact name matches")
        
        # Strategy 2: ORCID matching
        logger.info("🆔 Step 2: Finding ORCID matches...")
        orcid_edges = self._find_orcid_matches(authors_features)
        
        for a1, a2 in orcid_edges:
            if not G.has_edge(a1, a2):
                G.add_edge(a1, a2, reason="identical_orcid", confidence=1.0)
                edges_added += 1
                self.metrics.orcid_matches += 1
        
        logger.info(f"   Found {len(orcid_edges)} ORCID matches")
        
        # Strategy 3: High-similarity fuzzy matching
        logger.info("🔍 Step 3: Finding high-similarity fuzzy matches...")
        fuzzy_edges = self._find_fuzzy_matches(authors_features, author_work_map)
        
        for a1, a2, reason, confidence in fuzzy_edges:
            if not G.has_edge(a1, a2):
                G.add_edge(a1, a2, reason=reason, confidence=confidence)
                edges_added += 1
                self.metrics.fuzzy_matches += 1
        
        logger.info(f"   Found {len(fuzzy_edges)} fuzzy matches")
        
        # Update metrics
        self.metrics.total_edges = G.number_of_edges()
        self.metrics.processing_time = time.time() - self.start_time
        
        if self.metrics.processing_time > 0:
            self.metrics.authors_per_second = self.metrics.total_authors / self.metrics.processing_time
            self.metrics.comparisons_per_second = self.metrics.total_comparisons / self.metrics.processing_time
        
        self._log_performance_summary()
        
        return G

    def _find_exact_matches(self, authors_features: Dict) -> Dict[str, List[str]]:
        """Find authors with exactly matching normalized names."""
        name_groups = defaultdict(list)
        
        for author_id, features in authors_features.items():
            normalized_name = features.get('normalized_name', '').strip()
            if normalized_name and len(normalized_name) > 2:  # Avoid very short names
                name_groups[normalized_name].append(author_id)
        
        # Only return groups with multiple authors
        return {name: authors for name, authors in name_groups.items() if len(authors) > 1}

    def _find_orcid_matches(self, authors_features: Dict) -> List[Tuple[str, str]]:
        """Find authors with matching ORCID identifiers."""
        orcid_groups = defaultdict(list)
        edges = []
        
        for author_id, features in authors_features.items():
            orcid = features.get('orcid', '').strip()
            if orcid:
                orcid_groups[orcid].append(author_id)
        
        for orcid, authors in orcid_groups.items():
            if len(authors) > 1:
                for i, a1 in enumerate(authors):
                    for a2 in authors[i+1:]:
                        edges.append((a1, a2))
        
        return edges

    def _find_fuzzy_matches(self, authors_features: Dict, author_work_map: Dict) -> List[Tuple[str, str, str, float]]:
        """Find authors with high fuzzy similarity scores."""
        edges = []
        author_ids = list(authors_features.keys())
        
        # Use rapid fuzzy matching for initial filtering
        names = [(aid, authors_features[aid].get('normalized_name', '')) for aid in author_ids]
        names = [(aid, name) for aid, name in names if name and len(name) > 2]
        
        logger.info(f"   Processing {len(names)} authors for fuzzy matching...")
        
        # Process in batches for memory efficiency
        batch_size = min(self.batch_size, 500)  # Limit batch size for fuzzy matching
        
        for i in tqdm(range(0, len(names), batch_size), desc="Fuzzy matching batches"):
            batch = names[i:i + batch_size]
            batch_edges = self._process_fuzzy_batch(batch, authors_features, author_work_map)
            edges.extend(batch_edges)
        
        return edges

    def _process_fuzzy_batch(self, batch: List[Tuple[str, str]], 
                           authors_features: Dict, 
                           author_work_map: Dict) -> List[Tuple[str, str, str, float]]:
        """Process a batch of authors for fuzzy matching."""
        edges = []
        
        for i, (aid1, name1) in enumerate(batch):
            # Use rapidfuzz.process for efficient similarity search
            remaining_names = [(aid2, name2) for aid2, name2 in batch[i+1:]]
            
            if not remaining_names:
                continue
            
            # Get potential matches with rapidfuzz
            name_list = [name for _, name in remaining_names]
            matches = process.extract(name1, name_list, scorer=fuzz.ratio, limit=None)
            
            for match_name, score, idx in matches:
                if score >= 60:  # Reduced threshold for more inclusive matching
                    aid2 = remaining_names[idx][0]
                    
                    # Detailed analysis for high-scoring pairs
                    author1 = authors_features[aid1]
                    author2 = authors_features[aid2]
                    
                    works1 = set(author_work_map.get(aid1, []))
                    works2 = set(author_work_map.get(aid2, []))
                    common_works = works1.intersection(works2)
                    
                    should_merge, reason, confidence = self.should_consolidate_enhanced(
                        author1, author2, common_works
                    )
                    
                    if should_merge:
                        edges.append((aid1, aid2, reason, confidence))
                    
                    self.metrics.total_comparisons += 1
        
        return edges

    def _log_performance_summary(self):
        """Log comprehensive performance summary."""
        logger.info("\n📊 PERFORMANCE METRICS SUMMARY")
        logger.info("=" * 50)
        logger.info(f"📈 Dataset: {self.metrics.total_authors:,} authors")
        logger.info(f"🔗 Edges found: {self.metrics.total_edges:,}")
        logger.info(f"⏱️  Processing time: {self.metrics.processing_time:.2f} seconds")
        logger.info(f"⚡ Performance: {self.metrics.authors_per_second:.1f} authors/sec")
        
        if self.metrics.total_comparisons > 0:
            logger.info(f"🔍 Comparisons: {self.metrics.total_comparisons:,}")
            logger.info(f"📊 Comparison rate: {self.metrics.comparisons_per_second:.1f}/sec")
        
        logger.info(f"\n🎯 MATCH BREAKDOWN:")
        logger.info(f"   • Exact matches: {self.metrics.exact_matches}")
        logger.info(f"   • ORCID matches: {self.metrics.orcid_matches}")
        logger.info(f"   • Fuzzy matches: {self.metrics.fuzzy_matches}")
        logger.info(f"   • Institution matches: {self.metrics.institution_matches}")
        logger.info(f"   • Work overlap matches: {self.metrics.work_overlap_matches}")
        
        # Estimate quality metrics
        if self.metrics.total_authors > 0:
            consolidation_rate = self.metrics.total_edges / self.metrics.total_authors
            logger.info(f"\n📈 QUALITY ESTIMATES:")
            logger.info(f"   • Consolidation rate: {consolidation_rate:.3f}")
            logger.info(f"   • Avg edges per author: {consolidation_rate:.3f}")

    def export_metrics(self, filepath: str):
        """Export performance metrics to JSON file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.metrics.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"📊 Metrics exported to: {filepath}")
        except Exception as e:
            logger.error(f"❌ Failed to export metrics: {e}")

    def benchmark_against_baseline(self, authors_features: Dict, author_work_map: Dict, 
                                 baseline_matcher=None) -> Dict[str, Any]:
        """
        Benchmark enhanced matcher against baseline implementation.
        
        Args:
            authors_features: Author features dictionary
            author_work_map: Author work mapping
            baseline_matcher: Baseline matcher instance (optional)
            
        Returns:
            Comparison results
        """
        logger.info("🏁 Starting benchmark comparison...")
        
        # Enhanced matcher results
        start_time = time.time()
        enhanced_graph = self.find_candidates_optimized(authors_features, author_work_map)
        enhanced_time = time.time() - start_time
        enhanced_edges = enhanced_graph.number_of_edges()
        
        results = {
            'enhanced': {
                'processing_time': enhanced_time,
                'edges_found': enhanced_edges,
                'authors_per_second': len(authors_features) / enhanced_time if enhanced_time > 0 else 0,
                'metrics': self.metrics.to_dict()
            }
        }
        
        # Baseline comparison if provided
        if baseline_matcher:
            logger.info("🔄 Running baseline matcher for comparison...")
            try:
                start_time = time.time()
                baseline_graph = baseline_matcher.find_candidates(authors_features, author_work_map)
                baseline_time = time.time() - start_time
                baseline_edges = baseline_graph.number_of_edges();
                
                results['baseline'] = {
                    'processing_time': baseline_time,
                    'edges_found': baseline_edges,
                    'authors_per_second': len(authors_features) / baseline_time if baseline_time > 0 else 0
                }
                
                # Performance comparison
                speedup = baseline_time / enhanced_time if enhanced_time > 0 else float('inf')
                edge_ratio = enhanced_edges / baseline_edges if baseline_edges > 0 else float('inf')
                
                results['comparison'] = {
                    'speedup_factor': speedup,
                    'edge_ratio': edge_ratio,
                    'time_improvement_pct': ((baseline_time - enhanced_time) / baseline_time * 100) if baseline_time > 0 else 0
                }
                
                logger.info(f"⚡ Enhanced matcher is {speedup:.2f}x faster")
                logger.info(f"🔗 Enhanced matcher found {edge_ratio:.2f}x more edges")
                
            except Exception as e:
                logger.error(f"❌ Baseline comparison failed: {e}")
                results['baseline_error'] = str(e)
        
        return results
    
    def are_names_equivalent_enhanced(self, name1: str, name2: str) -> bool:
        """
        Enhanced name equivalence check with hyphen awareness.
        
        Args:
            name1, name2: Names to compare
            
        Returns:
            True if names are considered equivalent
        """
        if not name1 or not name2:
            return False
        
        # Normalize both names
        norm1 = self.normalize_name_advanced(name1)
        norm2 = self.normalize_name_advanced(name2)
        
        # Direct exact match
        if norm1 == norm2:
            return True
        
        # If hyphen-aware matching is enabled, check additional variations
        if self.hyphen_aware_matching:
            # Normalize hyphens specifically
            hyphen_norm1 = self._normalize_hyphens(norm1)
            hyphen_norm2 = self._normalize_hyphens(norm2)
            
            # Check hyphen-normalized versions
            if hyphen_norm1 == hyphen_norm2:
                return True
            
            # Check with hyphens removed entirely
            no_hyphen1 = hyphen_norm1.replace('-', ' ').replace('  ', ' ').strip()
            no_hyphen2 = hyphen_norm2.replace('-', ' ').replace('  ', ' ').strip()
            
            if no_hyphen1 == no_hyphen2:
                return True
        
        # Apply phonetic normalization and check
        phon1 = self._apply_phonetic_normalization(norm1)
        phon2 = self._apply_phonetic_normalization(norm2)
        
        if phon1 == phon2:
            return True
        
        return False
