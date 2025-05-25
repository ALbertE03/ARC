#!/usr/bin/env python
"""
Test GCN with a small subset of data to verify functionality
"""

import os
import sys
import logging
import json
import random

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

from models.GCN import create_gcn_matcher
from models.author_matcher import SmartAuthorMatcher
from utils.data_processing import load_data, build_author_work_map

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def test_gcn_small_subset():
    """Test GCN with a small subset of data."""
    logger.info("🧪 Testing GCN with small data subset")
    
    # Load full data
    authors_file = "data/openalex_authors_complete.json"
    works_file = "data/openalex_data.json"
    
    authors_data, works_data = load_data(authors_file, works_file)
    author_work_map = build_author_work_map(works_data)
    
    # Create small subset (500 authors, enough for GCN but small enough to complete quickly)
    author_ids = list(authors_data.keys())
    sample_size = min(500, len(author_ids))
    sampled_author_ids = random.sample(author_ids, sample_size)
    
    # Filter authors and works to subset
    subset_authors = {aid: authors_data[aid] for aid in sampled_author_ids}
    
    # Filter works to only include those with sampled authors
    subset_works = {}
    for work_id, work_data in works_data.items():
        work_authors = [auth.get('id', '') for auth in work_data.get('authorships', [])]
        # Also check 'authors' field as fallback
        if not work_authors:
            work_authors = [auth.get('id', '') for auth in work_data.get('authors', [])]
        
        if any(auth_id in sampled_author_ids for auth_id in work_authors if auth_id):
            subset_works[work_id] = work_data
    
    # If still no works, just take the first N works
    if not subset_works:
        logger.info("🔧 No works found with sampled authors, taking first 100 works")
        work_ids = list(works_data.keys())[:100]
        subset_works = {wid: works_data[wid] for wid in work_ids}
    
    logger.info(f"📊 Testing with {len(subset_authors)} authors and {len(subset_works)} works")
    
    # Initialize GCN
    gcn_matcher = create_gcn_matcher()
    
    # Extract features
    traditional_matcher = SmartAuthorMatcher(similarity_threshold=0.95)
    authors_features = {}
    
    for author_id, author_data in subset_authors.items():
        authors_features[author_id] = traditional_matcher.extract_features(
            author_id, author_data, author_work_map
        )
    
    # Run GCN
    logger.info("🧠 Running GCN on subset...")
    G = gcn_matcher.find_candidates(authors_features, author_work_map, subset_works)
    
    # Results
    logger.info(f"✅ GCN completed successfully!")
    logger.info(f"   Authors processed: {len(subset_authors)}")
    logger.info(f"   Works processed: {len(subset_works)}")
    logger.info(f"   Edges found: {G.number_of_edges()}")
    logger.info(f"   Nodes in graph: {G.number_of_nodes()}")
    
    return True

if __name__ == "__main__":
    test_gcn_small_subset()
