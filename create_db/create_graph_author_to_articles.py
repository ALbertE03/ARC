#!/usr/bin/env python

import os
import sys
import logging
import networkx as nx

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from models.author_matcher import SmartAuthorMatcher
from utils.data_processing import (
    load_data,
    build_author_work_map,
    print_consolidation_stats,
    build_full_graph,
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


def consolidate_authors_ml(authors_data, author_work_map):
    """Consolidate duplicate authors using advanced ML and clustering techniques."""
    logger.info("\nStarting advanced author consolidation with clustering...")

    matcher = SmartAuthorMatcher(similarity_threshold=0.85)

    logger.info("Preparing author features...")
    authors_features = {}
    for author_id, author_data in authors_data.items():
        authors_features[author_id] = matcher.extract_features(
            author_id, author_data, author_work_map
        )

    G = matcher.find_candidates(authors_features, author_work_map)

    logger.info("\nIdentifying connected components...")
    components = list(nx.connected_components(G))
    logger.info(f"Total connected components: {len(components)}")

    from utils.data_processing import consolidate_authors

    consolidated, component_stats = consolidate_authors(G, authors_data, components)

    print_consolidation_stats(consolidated, authors_data, component_stats, G)

    return consolidated, G


def main():
    """Main function to execute the author-article graph creation workflow."""
    try:
        authors_file = os.path.join(project_root, "data/openalex_authors_complete.json")
        works_file = os.path.join(project_root, "data/openalex_data.json")

        authors_data, works_data = load_data(authors_file, works_file)

        author_work_map = build_author_work_map(works_data)

        logger.info("\nUsing clustering approach for author consolidation")
        consolidated_authors, author_graph = consolidate_authors_ml(
            authors_data, author_work_map
        )

        full_graph, _ = build_full_graph(consolidated_authors, works_data)

        save_to_neo4j(full_graph, consolidated_authors, works_data)

        logger.info("\nProcess completed successfully!")

    except Exception as e:
        logger.error(f"\nError in main process: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
