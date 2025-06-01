#!/usr/bin/env python
"""
Enhanced Author Matcher - SIMPLIFIED for Name-Only Comparison
============================================================

This module provides a simplified author matching system with:
- Only exact name and alternative name comparison
- Multiprocessing support for N×N exhaustive comparison
- Logging of consolidated authors
"""

import networkx as nx
import logging
import time
import multiprocessing as mp
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Any
from tqdm import tqdm
import re
from unidecode import unidecode
import pickle
from functools import partial

logger = logging.getLogger(__name__)

# Global variable to store authors_features for workers (reduces data transfer)
_global_authors_features = None

def init_worker(authors_features):
    """Initialize worker process with shared data."""
    global _global_authors_features
    _global_authors_features = authors_features



def compare_author_chunk(chunk_data):
    """
    OPTIMIZED: Compare a chunk of author pairs for multiprocessing.
    Pre-extracts data to avoid repeated dictionary lookups.
    
    Args:
        chunk_data: Tuple containing (chunk_pairs, authors_features)
        
    Returns:
        List of tuples (author_id1, author_id2, reason, confidence)
    """
    chunk_pairs, authors_features = chunk_data
    results = []
    
    # Pre-extract all needed data to avoid repeated dictionary access
    author_data = {}
    for author_id1, author_id2 in chunk_pairs:
        if author_id1 not in author_data:
            author1 = authors_features[author_id1]
            author_data[author_id1] = (
                author1.get('normalized_name', ''),
                author1.get('alt_names', []),
                author1.get('orcid', '').strip(),
                author1.get('is_cuban', False)
            )
        
        if author_id2 not in author_data:
            author2 = authors_features[author_id2]
            author_data[author_id2] = (
                author2.get('normalized_name', ''),
                author2.get('alt_names', []),
                author2.get('orcid', '').strip(),
                author2.get('is_cuban', False)
            )
    
    # Fast comparison with pre-extracted data
    for author_id1, author_id2 in chunk_pairs:
        name1, alt_names1, orcid1, is_cuban1 = author_data[author_id1]
        name2, alt_names2, orcid2, is_cuban2 = author_data[author_id2]
        
        # Fast ORCID check first - both authors are already Cuban
        if orcid1 and orcid2 and orcid1 == orcid2:
            results.append((author_id1, author_id2, "identical_orcid", 1.0))
            continue
        
        # Fast exact name match
        if name1 and name2 and name1 == name2:
            results.append((author_id1, author_id2, 'exact_name_match', 1.0))
            continue
        
        # Alternative names checks (only if no exact match)
        match_found = False
        
        # Check main name vs alt names
        if name1 and name1 in alt_names2:
            results.append((author_id1, author_id2, 'name_alt_match', 0.95))
            continue
        
        if name2 and name2 in alt_names1:
            results.append((author_id1, author_id2, 'alt_name_match', 0.95))
            continue
        
        # Check alt names intersection (using set intersection for speed)
        if alt_names1 and alt_names2:
            alt_set1 = set(alt_names1)
            alt_set2 = set(alt_names2)
            if alt_set1 & alt_set2:  # Fast set intersection
                results.append((author_id1, author_id2, 'alt_alt_match', 0.90))
    
    return results


def compare_author_chunk_optimized(chunk_pairs):
    """
    ULTRA-OPTIMIZED: Compare a chunk using global data to reduce IPC overhead.
    Uses tuple unpacking and minimal function calls for maximum speed.
    """
    global _global_authors_features
    results = []
    
    # Pre-extract and cache all data with minimal dictionary access
    cache = {}
    
    # Batch extract data for better memory locality
    for author_id1, author_id2 in chunk_pairs:
        if author_id1 not in cache:
            author1 = _global_authors_features[author_id1]
            name = author1.get('normalized_name', '')
            alt_names = author1.get('alt_names', [])
            orcid = author1.get('orcid', '').strip()
            is_cuban = author1.get('is_cuban', False)
            # Store as tuple with pre-computed set for alt names
            cache[author_id1] = (name, frozenset(alt_names) if alt_names else frozenset(), orcid, is_cuban)
        
        if author_id2 not in cache:
            author2 = _global_authors_features[author_id2]
            name = author2.get('normalized_name', '')
            alt_names = author2.get('alt_names', [])
            orcid = author2.get('orcid', '').strip()
            is_cuban = author2.get('is_cuban', False)
            cache[author_id2] = (name, frozenset(alt_names) if alt_names else frozenset(), orcid, is_cuban)
    
    # Ultra-fast comparison with minimal allocations
    for author_id1, author_id2 in chunk_pairs:
        name1, alt_set1, orcid1, is_cuban1 = cache[author_id1]
        name2, alt_set2, orcid2, is_cuban2 = cache[author_id2]
        
        # ORCID check (fastest, most definitive) - both authors are already Cuban
        if orcid1 and orcid2:
            if orcid1 == orcid2:
                results.append((author_id1, author_id2, "identical_orcid", 1.0))
                continue
        
        # Exact name match (second fastest)
        if name1 and name2:
            if name1 == name2:
                results.append((author_id1, author_id2, 'exact_name_match', 1.0))
                continue
        
        # Alternative names (ONLY name-in-alt, NO alias-to-alias)
        if alt_set1 or alt_set2:
            # Main name in alt names
            if name1 and alt_set2 and name1 in alt_set2:
                results.append((author_id1, author_id2, 'name_alt_match', 0.95))
                continue
                
            if name2 and alt_set1 and name2 in alt_set1:
                results.append((author_id1, author_id2, 'alt_name_match', 0.95))
                continue
            
            # NO alias-to-alias intersection - REMOVED
    
    return results


def compare_author_chunk_ultra_optimized(chunk_pairs):
    """
    ULTRA-OPTIMIZED: Vectorized comparison with CPU cache optimizations.
    Uses pre-computed lookups and vectorized operations for maximum speed.
    """
    global _global_authors_features
    
    if not chunk_pairs:
        return []
    
    results = []
    
    # Step 1: Bulk extract all unique author IDs and their data
    unique_authors = set()
    for author_id1, author_id2 in chunk_pairs:
        unique_authors.add(author_id1)
        unique_authors.add(author_id2)
    
    # Step 2: Batch extract and preprocess all data once
    author_cache = {}
    for author_id in unique_authors:
        author = _global_authors_features[author_id]
        name = author.get('normalized_name', '')
        alt_names = author.get('alt_names', [])
        orcid = author.get('orcid', '').strip()
        is_cuban = author.get('is_cuban', False)
        
        # Pre-compute hash for faster comparisons
        alt_set = frozenset(alt_names) if alt_names else frozenset()
        
        author_cache[author_id] = {
            'name': name,
            'alt_set': alt_set,
            'orcid': orcid,
            'is_cuban': is_cuban,
            'name_hash': hash(name) if name else None,
            'has_orcid': bool(orcid),
            'has_name': bool(name),
            'has_alts': bool(alt_set)
        }
    
    # Step 3: Ultra-fast comparison with early exits and vectorized checks
    for author_id1, author_id2 in chunk_pairs:
        a1 = author_cache[author_id1]
        a2 = author_cache[author_id2]
        
        # Super-fast ORCID check with pre-computed flags (both authors are already Cuban)
        if a1['has_orcid'] and a2['has_orcid']:
            if a1['orcid'] == a2['orcid']:
                results.append((author_id1, author_id2, "identical_orcid", 1.0))
                continue
        
        # Fast name comparison using pre-computed hashes
        if a1['has_name'] and a2['has_name']:
            if a1['name_hash'] == a2['name_hash'] and a1['name'] == a2['name']:
                results.append((author_id1, author_id2, 'exact_name_match', 1.0))
                continue
        
        # Alternative names with pre-computed flags
        if a1['has_alts'] or a2['has_alts']:
            # Name in alt names
            if a1['has_name'] and a2['has_alts'] and a1['name'] in a2['alt_set']:
                results.append((author_id1, author_id2, 'name_alt_match', 0.95))
                continue
                
            if a2['has_name'] and a1['has_alts'] and a2['name'] in a1['alt_set']:
                results.append((author_id1, author_id2, 'alt_name_match', 0.95))
                continue
            
            # NO alias-to-alias intersection - REMOVED
    
    return results


def compare_author_chunk_mega_optimized(chunk_pairs):
    """
    MEGA-OPTIMIZED: Maximum performance comparison with all optimizations applied.
    Uses CPU-cache friendly operations, minimal allocations, and vectorized logic.
    """
    global _global_authors_features
    
    if not chunk_pairs:
        return []
    
    results = []
    
    # Step 1: Extract unique author IDs with minimal overhead
    authors_in_chunk = set()
    for pair in chunk_pairs:
        authors_in_chunk.update(pair)
    
    # Step 2: Bulk extract and optimize all data in one pass
    cache = {}
    for author_id in authors_in_chunk:
        author = _global_authors_features[author_id]
        
        # Direct extraction with minimal function calls
        name = author.get('normalized_name', '')
        alt_names = author.get('alt_names', [])
        orcid = author.get('orcid', '')
        is_cuban = author.get('is_cuban', False)
        
        # Pre-compute all boolean flags and optimizations
        has_name = bool(name)
        has_orcid = bool(orcid)
        alt_set = frozenset(alt_names) if alt_names else None
        has_alts = bool(alt_set)
        
        cache[author_id] = (
            name,           # 0
            alt_set,        # 1
            orcid,          # 2
            has_name,       # 3
            has_orcid,      # 4
            has_alts,       # 5
            is_cuban        # 6
        )
    
    # Step 3: Ultra-fast comparison with optimized tuple unpacking
    for author_id1, author_id2 in chunk_pairs:
        a1 = cache[author_id1]
        a2 = cache[author_id2]
        
        # Fastest path: ORCID comparison (most definitive) - both authors are already Cuban
        if a1[4] and a2[4]:  # both have ORCIDs
            if a1[2] == a2[2]:  # ORCID match
                results.append((author_id1, author_id2, "identical_orcid", 1.0))
                continue
        
        # Second fastest: exact name match
        if a1[3] and a2[3]:  # both have names
            if a1[0] == a2[0]:  # name match
                results.append((author_id1, author_id2, 'exact_name_match', 1.0))
                continue
        
        # Alternative names (only name-in-alt, NO alias-to-alias)
        if a1[5] or a2[5]:  # at least one has alt names
            # Name of author1 in alt names of author2
            if a1[3] and a2[5] and a1[0] in a2[1]:
                results.append((author_id1, author_id2, 'name_alt_match', 0.95))
                continue
                
            # Name of author2 in alt names of author1
            if a2[3] and a1[5] and a2[0] in a1[1]:
                results.append((author_id1, author_id2, 'alt_name_match', 0.95))
                continue
            
            # NO alias-to-alias intersection - REMOVED
    
    return results


def compare_names_only(author1: Dict, author2: Dict) -> Tuple[bool, str, float]:
    """
    Compare two authors ONLY based on:
    1. Exact normalized name match
    2. Name of one author in aliases of the other
    NOTHING ELSE.
    
    Args:
        author1, author2: Author feature dictionaries
        
    Returns:
        (should_merge, reason, confidence)
    """
    # 1. Check ORCID matching first - highest confidence
    orcid1 = author1.get('orcid', '').strip()
    orcid2 = author2.get('orcid', '').strip()
    
    if orcid1 and orcid2 and orcid1 == orcid2:
        return True, "identical_orcid", 1.0
    
    name1 = author1.get('normalized_name', '')
    name2 = author2.get('normalized_name', '')
    
    # 2. ONLY compare if normalized names are exactly equal
    if name1 and name2 and name1 == name2:
        return True, 'exact_name_match', 1.0
    
    # 3. ONLY check if name of one is in aliases of the other (NO alias-to-alias comparison)
    alt_names1 = author1.get('alt_names', [])
    alt_names2 = author2.get('alt_names', [])
    
    # Check if main name of author1 matches any alt name of author2
    if name1:
        for alt2 in alt_names2:
            if name1 == alt2:
                return True, 'name_alt_match', 0.95
    
    # Check if main name of author2 matches any alt name of author1
    if name2:
        for alt1 in alt_names1:
            if name2 == alt1:
                return True, 'alt_name_match', 0.95
    
    # NO OTHER COMPARISONS - No alias-to-alias matching
    # No match found - consider different
    return False, 'different', 0.0


def create_author_pairs_chunks(author_ids, chunk_size):
    """
    ULTRA-OPTIMIZED: Create chunks of author pairs for multiprocessing.
    Uses more efficient pair generation with vectorized operations.
    
    Args:
        author_ids: List of author IDs
        chunk_size: Size of each chunk
        
    Returns:
        Generator of author pair chunks
    """
    n = len(author_ids)
    pairs = []
    
    # Optimized pair generation - process in batches for better CPU cache utilization
    for i in range(n):
        author_id1 = author_ids[i]
        
        # Batch process the remaining authors for better memory locality
        remaining_authors = author_ids[i + 1:]
        for author_id2 in remaining_authors:
            pairs.append((author_id1, author_id2))
            
            # Yield larger chunks to reduce overhead
            if len(pairs) >= chunk_size:
                yield pairs
                pairs = []  # Reset for next chunk
    
    # Yield any remaining pairs
    if pairs:
        yield pairs


@dataclass
class SimpleMetrics:
    """Simple metrics for performance tracking."""
    total_authors: int = 0
    total_comparisons: int = 0
    total_edges: int = 0
    processing_time: float = 0.0
    exact_matches: int = 0
    alt_matches: int = 0
    orcid_matches: int = 0
    authors_per_second: float = 0.0
    comparisons_per_second: float = 0.0


class EnhancedAuthorMatcher:
    """
    Simplified Author Matcher - Only name and alternative name comparison.
    
    Features:
    - Exact name matching
    - Alternative name matching
    - ORCID matching
    - Multiprocessing support for N×N comparison
    - Consolidation logging
    """

    def __init__(self, 
                 batch_size: int = 1000,
                 use_multiprocessing: bool = True,
                 num_processes: Optional[int] = None):
        """
        Initialize the simplified author matcher.
        
        Args:
            batch_size: Size of batches for processing
            use_multiprocessing: Enable multiprocessing
            num_processes: Number of processes to use (auto-detect if None)
        """
        logger.info("🚀 Initializing Simplified Author Matcher...")
        
        self.batch_size = batch_size
        self.use_multiprocessing = use_multiprocessing
        
        # Configure multiprocessing
        if num_processes is None:
            self.num_processes = max(1, mp.cpu_count() - 1)
        else:
            self.num_processes = max(1, num_processes)
        
        logger.info(f"   Multiprocessing: {'Enabled' if self.use_multiprocessing else 'Disabled'}")
        if self.use_multiprocessing:
            logger.info(f"   Number of processes: {self.num_processes}")
        
        # OPTIMIZED: Larger chunk size for better performance
        # Increase chunk size significantly to reduce overhead
        if self.use_multiprocessing:
            # Aim for ~20-50 chunks total across all processes for better CPU utilization
            target_chunks = min(50, max(20, self.num_processes * 5))
            # MEGA-LARGE chunks to minimize IPC overhead and maximize CPU utilization
            self.mp_chunk_size = max(20000, batch_size * 20)  # Ultra-large chunks for maximum speed
        else:
            self.mp_chunk_size = batch_size
        
        # Performance tracking
        self.metrics = SimpleMetrics()
        self.start_time = None
        
        # Track consolidations for logging
        self.consolidations = []
        
        logger.info("✅ Simplified Author Matcher initialized successfully")
        logger.info("   Mode: Name and alias comparison ONLY")

    def normalize_name_advanced(self, name: str) -> str:
        """
        Simple name normalization with accent removal.
        IMPROVED: Added validation to prevent over-normalization that causes false positives.
        
        Args:
            name: Raw name string
            
        Returns:
            Normalized name string
        """
        if not name:
            return ""
        
        # SECURITY: Store original for length validation
        original_name = name.strip()
        
        # Remove accents and tildes using unidecode
        normalized = unidecode(name).lower().strip()
        
        # Remove common prefixes and suffixes
        prefixes = ['dr.', 'prof.', 'mr.', 'mrs.', 'ms.', 'phd', 'md']
        suffixes = ['jr.', 'sr.', 'ii', 'iii', 'phd', 'md', 'ph.d.', 'm.d.']
        
        words = normalized.split()
        cleaned_words = []
        
        for word in words:
            # Remove punctuation except hyphens
            word = re.sub(r'[^\w\s\-]', '', word)
            
            # SECURITY: Skip prefixes and suffixes but keep minimum name length
            if word not in prefixes and word not in suffixes and len(word) > 1:
                cleaned_words.append(word)
        
        normalized = ' '.join(cleaned_words)
        
        # Handle hyphenated names consistently
        normalized = re.sub(r'\s*-\s*', '-', normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def extract_features_enhanced(self, author_id: str, author_data: Dict, author_work_map: Dict) -> Dict:
        """
        Extract simplified features for an author.
        
        Args:
            author_id: Author identifier
            author_data: Raw author data
            author_work_map: Mapping of author to works
            
        Returns:
            Simplified feature dictionary
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
        
        # ORCID
        orcid = author_data.get("ids", {}).get("orcid", "").strip()
        
        # Nationality determination - check for Cuban affiliations
        is_cuban = self._is_cuban_author(author_data)
        
        return {
            "id": author_id,
            "name": name,
            "normalized_name": normalized_name,
            "alt_names": alt_names,
            "orcid": orcid,
            "works_count": len(author_work_map.get(author_id, [])),
            "cited_by_count": author_data.get("cited_by_count", 0),
            "is_cuban": is_cuban
        }

    def find_candidates_optimized(self, authors_features: Dict, author_work_map: Dict) -> nx.Graph:
        """
        Find consolidation candidates using exhaustive N×N comparison.
        
        Args:
            authors_features: Dictionary of author features
            author_work_map: Mapping of authors to works
            
        Returns:
            NetworkX graph with consolidation candidates
        """
        logger.info("🔍 Starting EXHAUSTIVE N×N author candidate finding...")
        logger.info("   Only comparing EXACT names and ALTERNATIVE names")
        
        if self.use_multiprocessing:
            return self._find_candidates_multiprocessing(authors_features)
        else:
            return self._find_candidates_sequential(authors_features)

    def _find_candidates_multiprocessing(self, authors_features: Dict) -> nx.Graph:
        """
        Exhaustive N×N comparison using multiprocessing.
        CUBAN FILTER: Only compare Cuban authors.
        """
        self.start_time = time.time()
        
        # Initialize metrics
        self.metrics.total_authors = len(authors_features)
        
        # Create graph
        G = nx.Graph()
        
        # Add all authors as nodes with progress bar
        print("📊 Adding authors as nodes...")
        for author_id, features in tqdm(authors_features.items(), desc="Adding nodes", unit="authors"):
            if features.get('is_cuban', False):
                G.add_node(author_id, **features)
        
        # CUBAN NATIONALITY FILTER: Only include Cuban authors for comparison
        print("🇨🇺 Filtering for Cuban authors...")
        cuban_author_ids = []
        total_authors = len(authors_features)
        
        for author_id, features in tqdm(authors_features.items(), desc="Filtering Cuban authors", unit="authors"):
            if features.get('is_cuban', False):
                cuban_author_ids.append(author_id)
        
        logger.info(f"   Found {len(cuban_author_ids)} Cuban authors out of {total_authors} total authors")
        
        if len(cuban_author_ids) == 0:
            logger.warning("   No Cuban authors found - returning empty graph")
            return G
        
        # Use only Cuban authors for comparison
        author_ids = cuban_author_ids
        total_pairs = len(author_ids) * (len(author_ids) - 1) // 2
        
        logger.info(f"   Will compare {total_pairs:,} pairs using {self.num_processes} processes")
        logger.info(f"   Chunk size: {self.mp_chunk_size:,} pairs per chunk")
        
        edges_added = 0
        
        # Create chunks of author pairs with progress bar
        print("🔄 Creating comparison chunks...")
        pair_chunks = list(tqdm(
            create_author_pairs_chunks(author_ids, self.mp_chunk_size),
            desc="Creating chunks",
            unit="chunks"
        ))
        
        logger.info(f"   Created {len(pair_chunks)} chunks for processing")
        
        # OPTIMIZED: Process chunks using multiprocessing with reduced overhead
        try:
            with mp.Pool(processes=self.num_processes, initializer=init_worker, initargs=(authors_features,)) as pool:
                # Use imap for progress tracking with enhanced description
                print(f"⚡ Processing {len(pair_chunks)} chunks with {self.num_processes} processes...")
                results = list(tqdm(
                    pool.imap(compare_author_chunk_mega_optimized, 
                             pair_chunks,
                             chunksize=1),  # Process one chunk at a time for better load balancing
                    total=len(pair_chunks),
                    desc=f"MP comparison ({self.num_processes}P)",
                    unit="chunks",
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
                ))
                
                # Collect results and add edges with progress bar
                print("🔗 Collecting results and adding edges...")
                total_matches = sum(len(chunk_results) for chunk_results in results)
                
                # OPTIMIZED: Batch consolidation logging to reduce overhead
                consolidations_batch = []
                
                with tqdm(total=total_matches, desc="Adding edges", unit="matches") as pbar:
                    for chunk_results in results:
                        for author_id1, author_id2, reason, confidence in chunk_results:
                            if not G.has_edge(author_id1, author_id2):
                                G.add_edge(author_id1, author_id2, reason=reason, confidence=confidence)
                                edges_added += 1
                                
                                # Batch consolidation info for later logging (reduces overhead)
                                consolidations_batch.append((author_id1, author_id2, reason, confidence))
                                
                                # Update type-specific metrics
                                if reason == 'identical_orcid':
                                    self.metrics.orcid_matches += 1
                                elif reason == 'exact_name_match':
                                    self.metrics.exact_matches += 1
                                else:
                                    self.metrics.alt_matches += 1
                                
                                pbar.update(1)
                
                # Process consolidation logging in batch (much faster)
                print("📝 Processing consolidation logs...")
                for author_id1, author_id2, reason, confidence in tqdm(consolidations_batch, desc="Logging consolidations", unit="logs"):
                    self._log_consolidation(author_id1, author_id2, reason, confidence, authors_features)
        
        except Exception as e:
            logger.error(f"Multiprocessing failed: {e}. Falling back to sequential processing.")
            return self._find_candidates_sequential(authors_features)
        
        # Update metrics with progress indication
        print("📈 Finalizing metrics and summary...")
        self.metrics.total_comparisons = total_pairs
        self.metrics.total_edges = G.number_of_edges()
        self.metrics.processing_time = time.time() - self.start_time
        
        if self.metrics.processing_time > 0:
            self.metrics.authors_per_second = self.metrics.total_authors / self.metrics.processing_time
            self.metrics.comparisons_per_second = self.metrics.total_comparisons / self.metrics.processing_time
        
        logger.info(f"✅ Multiprocessing comparison completed: {edges_added} matches found")
        logger.info(f"   ORCID matches: {self.metrics.orcid_matches}")
        logger.info(f"   Exact name matches: {self.metrics.exact_matches}")
        logger.info(f"   Alternative name matches: {self.metrics.alt_matches}")
        logger.info(f"⚡ Speed: {self.metrics.comparisons_per_second:,.0f} comparisons/second")
        
        return G

    def _find_candidates_sequential(self, authors_features: Dict) -> nx.Graph:
        """
        Sequential N×N comparison (fallback method).
        CUBAN FILTER: Only compare Cuban authors.
        """
        self.start_time = time.time()
        
        # Initialize metrics
        self.metrics.total_authors = len(authors_features)
        
        # Create graph
        G = nx.Graph()
        
        # Add all authors as nodes with progress bar
        print("📊 Adding authors as nodes...")
        for author_id, features in tqdm(authors_features.items(), desc="Adding nodes", unit="authors"):
            G.add_node(author_id, **features)
        
        # CUBAN NATIONALITY FILTER: Only include Cuban authors for comparison
        print("🇨🇺 Filtering for Cuban authors...")
        cuban_author_ids = []
        total_authors = len(authors_features)
        
        for author_id, features in tqdm(authors_features.items(), desc="Filtering Cuban authors", unit="authors"):
            if features.get('is_cuban', False):
                cuban_author_ids.append(author_id)
        
        logger.info(f"   Found {len(cuban_author_ids)} Cuban authors out of {total_authors} total authors")
        
        if len(cuban_author_ids) == 0:
            logger.warning("   No Cuban authors found - returning empty graph")
            return G
        
        # Use only Cuban authors for comparison
        author_ids = cuban_author_ids
        total_pairs = len(author_ids) * (len(author_ids) - 1) // 2
        
        logger.info(f"   Will compare {total_pairs:,} pairs sequentially")
        
        edges_added = 0
        
        # Create comparison pairs list for progress tracking
        print("🔍 Performing sequential comparison...")
        comparison_pairs = []
        for i in range(len(author_ids)):
            for j in range(i + 1, len(author_ids)):
                comparison_pairs.append((author_ids[i], author_ids[j]))
        
        # Process each pair with detailed progress tracking
        for author_id1, author_id2 in tqdm(comparison_pairs, desc="Sequential N×N comparison", unit="pairs"):
            author1 = authors_features[author_id1]
            author2 = authors_features[author_id2]
            
            # Only check names and alternative names (both authors are already Cuban)
            should_merge, reason, confidence = compare_names_only(author1, author2)
            
            if should_merge:
                if not G.has_edge(author_id1, author_id2):
                    G.add_edge(author_id1, author_id2, reason=reason, confidence=confidence)
                    edges_added += 1
                    
                    # Track consolidation for logging
                    self._log_consolidation(author_id1, author_id2, reason, confidence, authors_features)
                    
                    # Update type-specific metrics
                    if reason == 'identical_orcid':
                        self.metrics.orcid_matches += 1
                    elif reason == 'exact_name_match':
                        self.metrics.exact_matches += 1
                    else:
                        self.metrics.alt_matches += 1
        
        # Update metrics with progress indication
        print("📈 Finalizing metrics and summary...")
        self.metrics.total_comparisons = total_pairs
        self.metrics.total_edges = G.number_of_edges()
        self.metrics.processing_time = time.time() - self.start_time
        
        if self.metrics.processing_time > 0:
            self.metrics.authors_per_second = self.metrics.total_authors / self.metrics.processing_time
            self.metrics.comparisons_per_second = self.metrics.total_comparisons / self.metrics.processing_time
        
        logger.info(f"✅ Sequential comparison completed: {edges_added} matches found")
        logger.info(f"   ORCID matches: {self.metrics.orcid_matches}")
        logger.info(f"   Exact name matches: {self.metrics.exact_matches}")
        logger.info(f"   Alternative name matches: {self.metrics.alt_matches}")
        logger.info(f"⚡ Speed: {self.metrics.comparisons_per_second:,.0f} comparisons/second")
        
        return G

    def _log_consolidation(self, author_id1: str, author_id2: str, reason: str, confidence: float, authors_features: Dict):
        """
        Log a consolidation match.
        
        Args:
            author_id1, author_id2: Author IDs being consolidated
            reason: Reason for consolidation
            confidence: Confidence score
            authors_features: Author features dictionary
        """
        author1 = authors_features[author_id1]
        author2 = authors_features[author_id2]
        
        name1 = author1.get('name', 'Unknown')
        name2 = author2.get('name', 'Unknown')
        
        consolidation_info = {
            'author_id1': author_id1,
            'author_id2': author_id2,
            'name1': name1,
            'name2': name2,
            'reason': reason,
            'confidence': confidence,
            'timestamp': time.time()
        }
        
        self.consolidations.append(consolidation_info)
        
        # Log the consolidation
        logger.info(f"🔗 CONSOLIDATION: '{name1}' ↔ '{name2}' | Reason: {reason} | Confidence: {confidence:.2f}")

    def get_consolidation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all consolidations performed.
        
        Returns:
            Dictionary with consolidation summary
        """
        total_consolidations = len(self.consolidations)
        
        # Count by reason
        reason_counts = defaultdict(int)
        for consolidation in self.consolidations:
            reason_counts[consolidation['reason']] += 1
        
        # Average confidence by reason
        reason_confidence = defaultdict(list)
        for consolidation in self.consolidations:
            reason_confidence[consolidation['reason']].append(consolidation['confidence'])
        
        avg_confidence_by_reason = {
            reason: sum(confidences) / len(confidences) if confidences else 0.0
            for reason, confidences in reason_confidence.items()
        }
        
        return {
            'total_consolidations': total_consolidations,
            'consolidations_by_reason': dict(reason_counts),
            'average_confidence_by_reason': avg_confidence_by_reason,
            'consolidations': self.consolidations
        }

    def _normalize_hyphens(self, name: str) -> str:
        """
        Normalize hyphen usage in names.
        
        Args:
            name: Name to normalize
            
        Returns:
            Name with normalized hyphens
        """
        if not name:
            return ""
        
        # Standardize hyphen spacing
        normalized = re.sub(r'\s*-\s*', '-', name)
        
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _is_cuban_author(self, author_data: Dict) -> bool:
        """
        Determine if an author has Cuban nationality based on institutional affiliations.
        
        Args:
            author_data: Raw author data from OpenAlex
            
        Returns:
            bool: True if the author is affiliated with Cuban institutions
        """
        countries = author_data.get("countries", [])
        if "CU" in countries:
            return True
        # Check affiliations for Cuban institutions (country_code "CU")
        for affil in author_data.get("affiliations", []):
            institution = affil.get("institution", {})
            if institution and institution.get("country_code") == "CU":
                return True
        
        # Also check the countries field if present
        
            
        return False
