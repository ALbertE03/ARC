#!/usr/bin/env python

import os
import sys
import logging
import networkx as nx
import time
from tqdm import tqdm

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from models.author_matcher import SmartAuthorMatcher

try:
    from models.GCN import GCNAuthorMatcher, create_gcn_matcher
    GCN_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("🧠 GCN functionality available - using advanced neural approach")
except ImportError as e:
    GCN_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ GCN not available, falling back to traditional approach: {e}")

from utils.data_processing import (
    load_data,
    build_author_work_map,
    print_consolidation_stats,
    build_full_graph,
    consolidate_authors
)
from db.db_operations import save_to_neo4j

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("author_consolidation.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def consolidate_authors_gcn(authors_data, author_work_map, works_data):
    """Consolidate duplicate authors using GCN-based approach (primary method)."""
    logger.info("\n🧠 Starting GCN-Based Author Consolidation")
    logger.info("=" * 70)
    
    start_time = time.time()
    
    if not GCN_AVAILABLE:
        logger.warning("🔄 GCN not available, falling back to traditional approach...")
        return consolidate_authors_traditional(authors_data, author_work_map)
    
    try:
        # Check PyTorch and setup device
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"🖥️ Using device: {device}")
        
        # Memory and performance optimizations
        if device == 'cuda':
            logger.info(f"💾 GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        
        # Dataset size checks for optimization
        num_authors = len(authors_data)
        num_works = len(works_data)
        
        logger.info(f"📊 Dataset size: {num_authors} authors, {num_works} works")
        
        # Adjust parameters based on dataset size
        if num_authors > 10000:
            logger.info("⚡ Large dataset detected - using optimized parameters")
            embedding_dim = 256  # Reduced for large datasets
            hidden_dims = [128, 64]
            batch_size = 64
        elif num_authors > 5000:
            logger.info("📊 Medium dataset detected - using balanced parameters")
            embedding_dim = 300
            hidden_dims = [128, 64]
            batch_size = 32
        else:
            logger.info("🔬 Small dataset detected - using full parameters")
            embedding_dim = 300
            hidden_dims = [256, 128]
            batch_size = 16
        
        # Initialize GCN matcher with optimized parameters
        gcn_matcher = create_gcn_matcher(
            embedding_dim=embedding_dim,
            hidden_dims=hidden_dims,
            learning_rate=0.01,
            margin=1.0,
            device=device
        )
        
        # Extract traditional features first (for compatibility)
        logger.info("📝 Extracting author features...")
        traditional_matcher = SmartAuthorMatcher(similarity_threshold=0.95)
        authors_features = {}
        
        for author_id, author_data in tqdm(authors_data.items(), desc="Extracting author features"):
            authors_features[author_id] = traditional_matcher.extract_features(
                author_id, author_data, author_work_map
            )
        
        # Use GCN to find consolidation candidates
        logger.info("🧠 Training GCN and finding consolidation candidates...")
        logger.info(f"   Training will use {device} with batch size {batch_size}")
        
        G = gcn_matcher.find_candidates(authors_features, author_work_map, works_data)
        
        # Get connected components
        logger.info("🔍 Identifying connected components...")
        components = list(nx.connected_components(G))
        logger.info(f"   Found {len(components)} connected components")
        logger.info(f"   Total edges found: {G.number_of_edges()}")
        
        # Performance metrics
        component_sizes = [len(comp) for comp in components]
        if component_sizes:
            logger.info(f"   Largest component: {max(component_sizes)} authors")
            logger.info(f"   Average component size: {sum(component_sizes)/len(component_sizes):.1f}")
        
        # Perform final consolidation
        logger.info("🔄 Consolidating authors...")
        consolidated, component_stats = consolidate_authors(G, authors_data, components)
        
        end_time = time.time()
        
        # Print detailed statistics
        print_consolidation_stats(consolidated, authors_data, component_stats, G)
        
        # Performance summary
        total_time = end_time - start_time
        authors_per_second = len(authors_data) / total_time if total_time > 0 else 0
        
        logger.info(f"✅ GCN consolidation completed in {total_time:.2f} seconds")
        logger.info(f"📊 Consolidated {len(authors_data)} → {len(consolidated)} authors")
        logger.info(f"⚡ Performance: {authors_per_second:.1f} authors/second")
        logger.info(f"💾 Memory peak: {device.upper()} optimized")
        
        return consolidated, G
        
    except Exception as e:
        logger.error(f"❌ GCN approach failed: {str(e)}")
        logger.info("🔄 Falling back to traditional approach...")
        return consolidate_authors_traditional(authors_data, author_work_map)


def consolidate_authors_traditional(authors_data, author_work_map):
    """Fallback traditional consolidation method."""
    logger.info("\n🔍 Using Traditional Rule-Based Consolidation")
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

    # Find candidates using traditional N×N approach
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


def consolidate_authors_traditional_sampled(authors_data, author_work_map):
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


def consolidate_authors_ml(authors_data, author_work_map, works_data=None):
    """Main consolidation function - ALWAYS uses GCN when available."""
    
    # Decision logic for method selection - FORCE GCN USAGE
    use_gcn = False
    reason = ""
    
    if not GCN_AVAILABLE:
        reason = "GCN dependencies not available (PyTorch missing)"
    elif not works_data:
        reason = "Works data not provided (required for GCN)"
    else:
        use_gcn = True
        reason = f"🧠 FORCING GCN approach for dataset with {len(authors_data):,} authors"
    
    logger.info(f"🎯 Method selection: {reason}")
    
    if use_gcn:
        logger.info("🧠 Using GCN-based consolidation (FORCED - preferred method)")
        try:
            return consolidate_authors_gcn(authors_data, author_work_map, works_data)
        except Exception as e:
            logger.error(f"❌ GCN failed unexpectedly: {str(e)}")
            logger.info("🔄 Graceful fallback to traditional approach")
            return consolidate_authors_traditional(authors_data, author_work_map)
    else:
        if len(authors_data) > 25000:
            logger.info("🔍 Using sampled traditional approach for large dataset")
            return consolidate_authors_traditional_sampled(authors_data, author_work_map)
        else:
            logger.info("🔍 Using traditional rule-based consolidation")
            return consolidate_authors_traditional(authors_data, author_work_map)


def main():
    """Main function to execute the GCN-enhanced author-article graph creation workflow."""
    logger.info("🚀 Starting Author Resolution and Consolidation (ARC) System")
    logger.info("=" * 80)
    
    # System information
    import platform
    logger.info(f"🖥️ System: {platform.system()} {platform.release()}")
    logger.info(f"🐍 Python: {platform.python_version()}")
    
    # Check available approaches
    if GCN_AVAILABLE:
        import torch
        torch_version = torch.__version__
        device_info = "CUDA available" if torch.cuda.is_available() else "CPU only"
        logger.info(f"🧠 PyTorch {torch_version} ({device_info}) - GCN approach available")
    else:
        logger.info("🔍 Traditional approach only - GCN dependencies not available")
    
    try:
        # Load data files
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

        # Load data
        logger.info("📚 Loading data...")
        authors_data, works_data = load_data(authors_file, works_file)
        author_work_map = build_author_work_map(works_data)
        
        logger.info(f"📊 Loaded {len(authors_data)} authors and {len(works_data)} works")
        
        # Data quality checks
        total_authorship_records = sum(len(works) for works in author_work_map.values())
        avg_works_per_author = total_authorship_records / len(authors_data) if authors_data else 0
        avg_authors_per_work = sum(len(work.get('authorships', [])) for work in works_data.values()) / len(works_data) if works_data else 0
        
        logger.info(f"📈 Average works per author: {avg_works_per_author:.1f}")
        logger.info(f"📈 Average authors per work: {avg_authors_per_work:.1f}")

        # Perform consolidation using the best available method (GCN FORCED)
        approach = "GCN-based (FORCED - advanced neural)" if GCN_AVAILABLE else "Traditional rule-based (fallback only)"
        logger.info(f"🎯 Selected approach: {approach}")
            
        consolidated_authors, author_graph = consolidate_authors_ml(
            authors_data, author_work_map, works_data
        )

        # Graph analysis
        logger.info("📊 Analyzing consolidation results...")
        reduction_percentage = ((len(authors_data) - len(consolidated_authors)) / len(authors_data) * 100) if authors_data else 0
        consolidation_rate = author_graph.number_of_edges() / len(authors_data) if authors_data else 0
        
        logger.info(f"   Reduction: {reduction_percentage:.1f}% ({len(authors_data)} → {len(consolidated_authors)})")
        logger.info(f"   Consolidation edges: {author_graph.number_of_edges()}")
        logger.info(f"   Edge density: {consolidation_rate:.3f}")

        # Build full graph for Neo4j
        logger.info("🏗️ Building full knowledge graph...")
        full_graph, graph_stats = build_full_graph(consolidated_authors, works_data)
        
        logger.info(f"   Knowledge graph nodes: {full_graph.number_of_nodes()}")
        logger.info(f"   Knowledge graph edges: {full_graph.number_of_edges()}")
        
        # Save to Neo4j database
        logger.info("💾 Saving to Neo4j database...")
        save_to_neo4j(full_graph, consolidated_authors, works_data)

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
        logger.info(f"   • Method used: {'GCN-based (FORCED)' if GCN_AVAILABLE and works_data and len(authors_data) >= 1 else 'Traditional'}")
        logger.info("💾 Data successfully saved to Neo4j database")
        
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
