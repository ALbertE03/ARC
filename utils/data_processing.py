import json
import logging
from typing import Dict, List, Tuple, Set
from collections import defaultdict, Counter
import networkx as nx
from tqdm import tqdm

logger = logging.getLogger(__name__)


def load_data(authors_file: str, works_file: str) -> Tuple[Dict, Dict]:
    """Load author and work data from JSON files.

    Args:
        authors_file: Path to the authors JSON file
        works_file: Path to the works JSON file

    Returns:
        Tuple containing authors data and works data dictionaries
    """
    logger.info("Loading data...")
    
    # Load authors data
    logger.info("📚 Loading authors data...")
    with open(authors_file, "r", encoding="utf-8") as f:
        authors_data = json.load(f)

    # Load works data  
    logger.info("📄 Loading works data...")
    with open(works_file, "r", encoding="utf-8") as f:
        works_list = json.load(f)
    
    # Convert works list to dictionary for consistent access
    logger.info("🔄 Converting works to dictionary format...")
    works_data = {}
    for work in tqdm(works_list, desc="Processing works"):
        work_id = work.get("id", "").split("/")[-1]
        if work_id:
            works_data[work_id] = work

    logger.info(
        f"✅ Data loaded: {len(authors_data)} authors, {len(works_data)} articles"
    )
    return authors_data, works_data


def build_author_work_map(works_data: Dict) -> Dict[str, List[str]]:
    """Create a mapping from author_id to a list of work_ids.

    Args:
        works_data: Dictionary containing work data

    Returns:
        Dictionary mapping author IDs to lists of work IDs
    """
    logger.info("🔗 Building author-work mapping...")
    author_work_map = defaultdict(list)
    
    for work_id, work in tqdm(works_data.items(), desc="Building author-work map"):
        for authorship in work.get("authorships", []):
            author_id = authorship.get("author", {}).get("id", "").split("/")[-1]
            if author_id:
                author_work_map[author_id].append(work_id)
    
    logger.info(f"✅ Author-work map built: {len(author_work_map)} authors mapped")
    return author_work_map


def consolidate_authors(G: nx.Graph, authors_data: Dict, components: List[Set]) -> Dict:
    """Consolidate author information based on connected components in the graph.

    Args:
        G: NetworkX graph containing author nodes
        authors_data: Original authors data dictionary
        components: List of connected components from the graph

    Returns:
        Dictionary of consolidated authors
    """
    logger.info("\nConsolidating authors...")
    consolidated = {}
    component_stats = []

    for component in tqdm(components, desc="Components"):
        component_list = list(component)

        if len(component_list) == 1:
            author_id = component_list[0]
            consolidated[author_id] = {
                "id": author_id,
                "display_name": G.nodes[author_id].get("name", ""),
                "works_count": G.nodes[author_id].get("works_count", 0),
                "cited_by_count": G.nodes[author_id].get("cited_by_count", 0),
                "alias_ids": [],
                "display_name_alternatives": G.nodes[author_id].get("alt_names", []),
                "original_data": authors_data.get(author_id, {}),
                "orcid": G.nodes[author_id].get("orcid", ""),
                "affiliations": G.nodes[author_id].get("affiliations", []),
                "topics": G.nodes[author_id].get("topics", []),
                "x_concepts": G.nodes[author_id].get("x_concepts", []),
                "h_index": G.nodes[author_id].get("h_index", 0),
                "last_known_institutions": G.nodes[author_id].get(
                    "last_known_institutions", []
                ),
            }
            continue

        main_author = max(
            component_list,
            key=lambda x: (
                G.nodes[x].get("works_count", 0) * 0.7
                + G.nodes[x].get("cited_by_count", 0) * 0.3
            ),
        )

        works_counts = [G.nodes[a].get("works_count", 0) for a in component_list]
        stats = {
            "main_author": main_author,
            "num_authors": len(component_list),
            "total_works": sum(works_counts),
            "max_works": max(works_counts),
            "min_works": min(works_counts),
            "authors": component_list,
        }
        component_stats.append(stats)

        all_alt_names = []
        main_author_name = G.nodes[main_author].get("name", "")

        for a in component_list:
            author_name = G.nodes[a].get("name", "")
            if author_name and author_name != main_author_name:
                all_alt_names.append(author_name)

            alt_names = G.nodes[a].get("alt_names", [])
            if alt_names:
                for alt_name in alt_names:
                    if alt_name and alt_name != main_author_name:
                        all_alt_names.append(alt_name)

        unique_alt_names = []
        seen_names = set()
        for name in all_alt_names:
            if name not in seen_names:
                seen_names.add(name)
                unique_alt_names.append(name)

        combined = {
            "id": main_author,
            "display_name": G.nodes[main_author].get("name", ""),
            "works_count": stats["total_works"],
            "cited_by_count": sum(
                G.nodes[a].get("cited_by_count", 0) for a in component_list
            ),
            "alias_ids": [a for a in component_list if a != main_author],
            "display_name_alternatives": unique_alt_names,
            "original_data": authors_data.get(main_author, {}),
            "orcid": G.nodes[main_author].get("orcid", ""),
        }

        combined["affiliations"] = collect_unique_affiliations(G, component_list)

        combined["topics"] = collect_unique_topics(G, component_list)

        combined["x_concepts"] = collect_unique_concepts(G, component_list)

        all_institutions = set()
        for a in component_list:
            for inst in G.nodes[a].get("last_known_institutions", []):
                if isinstance(inst, str):
                    all_institutions.add(inst)

        combined["last_known_institutions"] = list(all_institutions)

        combined["h_index"] = max(G.nodes[a].get("h_index", 0) for a in component_list)

        consolidated[main_author] = combined

    return consolidated, component_stats


def collect_unique_affiliations(G: nx.Graph, component_list: List[str]) -> List[Dict]:
    """Collect and deduplicate affiliations from a component list.

    Args:
        G: NetworkX graph containing author nodes
        component_list: List of author IDs in a component

    Returns:
        List of unique affiliations
    """
    all_affiliations = []
    for a in component_list:
        for affil in G.nodes[a].get("affiliations", []):
            if isinstance(affil, dict):
                all_affiliations.append(affil)

    unique_affiliations = []
    seen_affil_tuples = set()
    for affil in all_affiliations:
        hashable_items = []
        for k, v in sorted(affil.items()):
            if isinstance(v, list):
                v = tuple(v)
            hashable_items.append((k, v))

        affil_items = tuple(hashable_items)
        if affil_items not in seen_affil_tuples:
            seen_affil_tuples.add(affil_items)
            unique_affiliations.append(affil)

    return unique_affiliations


def collect_unique_topics(G: nx.Graph, component_list: List[str]) -> List[Dict]:
    """Collect and deduplicate topics from a component list.

    Args:
        G: NetworkX graph containing author nodes
        component_list: List of author IDs in a component

    Returns:
        List of unique topics
    """
    all_topics = []
    for a in component_list:
        for topic in G.nodes[a].get("topics", []):
            if isinstance(topic, dict):
                all_topics.append(topic)

    unique_topics = []
    seen_topic_tuples = set()
    for topic in all_topics:
        hashable_items = []
        for k, v in sorted(topic.items()):
            if isinstance(v, list):
                v = tuple(v)
            hashable_items.append((k, v))

        topic_items = tuple(hashable_items)
        if topic_items not in seen_topic_tuples:
            seen_topic_tuples.add(topic_items)
            unique_topics.append(topic)

    return unique_topics


def collect_unique_concepts(G: nx.Graph, component_list: List[str]) -> List[Dict]:
    """Collect and deduplicate concepts from a component list.

    Args:
        G: NetworkX graph containing author nodes
        component_list: List of author IDs in a component

    Returns:
        List of unique concepts
    """
    all_concepts = []
    for a in component_list:
        for concept in G.nodes[a].get("x_concepts", []):
            if isinstance(concept, dict):
                all_concepts.append(concept)

    unique_concepts = []
    seen_concept_tuples = set()
    for concept in all_concepts:
        hashable_items = []
        for k, v in sorted(concept.items()):
            if isinstance(v, list):
                v = tuple(v)
            hashable_items.append((k, v))

        concept_items = tuple(hashable_items)
        if concept_items not in seen_concept_tuples:
            seen_concept_tuples.add(concept_items)
            unique_concepts.append(concept)

    return unique_concepts


def print_consolidation_stats(
    consolidated: Dict, authors_data: Dict, component_stats: List[Dict], G: nx.Graph
) -> None:
    """Print statistics about the consolidation process.

    Args:
        consolidated: Dictionary of consolidated authors
        authors_data: Original authors data dictionary
        component_stats: List of component statistics dictionaries
        G: NetworkX graph containing author nodes
    """
    logger.info("\n📊 CONSOLIDATION REPORT")
    logger.info(f"Original authors: {len(authors_data)}")
    logger.info(f"Consolidated authors: {len(consolidated)}")
    logger.info(f"Reduction: {(1 - len(consolidated)/len(authors_data))*100:.1f}%")

    component_sizes = [
        c["num_authors"] for c in component_stats if c["num_authors"] > 1
    ]
    if component_sizes:
        size_dist = Counter(component_sizes)
        logger.info("\n📦 Component size distribution:")
        for size, count in sorted(size_dist.items()):
            logger.info(f" - Components with {size} authors: {count}")

        logger.info("\n🏆 Top 5 largest components:")
        for comp in sorted(
            component_stats, key=lambda x: x["num_authors"], reverse=True
        )[:5]:
            main_name = G.nodes[comp["main_author"]].get("name", "")
            logger.info(f" - {main_name} (ID: {comp['main_author']}):")
            logger.info(f"   👥 Authors: {comp['num_authors']}")
            logger.info(f"   📚 Total articles: {comp['total_works']}")
            logger.info(f"   🎯 Article range: {comp['min_works']}-{comp['max_works']}")


def build_full_graph(
    consolidated_authors: Dict, works_data: Dict
) -> Tuple[nx.Graph, Dict]:
    """Build the complete graph with consolidated authors and articles.

    Args:
        consolidated_authors: Dictionary of consolidated authors
        works_data: Dictionary of work data

    Returns:
        NetworkX graph containing authors and works with relationships,
        and a dictionary of relations for logging
    """
    logger.info("\nBuilding complete graph...")
    G = nx.Graph()

    logger.info("Adding consolidated authors...")
    for author_id, author_data in tqdm(consolidated_authors.items(), desc="Authors"):
        G.add_node(author_id, **author_data, type_node="Author")

    logger.info("Adding articles...")
    for work in tqdm(works_data, desc="Articles"):
        work_id = work.get("id", "").split("/")[-1]
        concepts = [
            {
                "id": concept["id"],
                "display_name": concept["display_name"],
                "level": concept["level"],
                "score": concept["score"],
            }
            for concept in work.get("concepts", [])
        ]

        G.add_node(
            work_id,
            title=work.get("title", ""),
            publication_year=work.get("publication_year", None),
            publication_date=work.get("publication_date", ""),
            cited_by_count=work.get("cited_by_count", 0),
            is_oa=work.get("is_oa", False),
            type_node="Work",
            concepts=concepts,
            primary_topic=work.get("primary_topic", {}),
            topics=work.get("topics", []),
            keywords=work.get("keywords", []),
            open_access=work.get("open_access", {}),
            biblio=work.get("biblio", {}),
            referenced_works_count=work.get("referenced_works_count", 0),
            related_works=work.get("related_works", []),
            abstract_inverted_index=work.get("abstract_inverted_index", {}),
        )

    logger.info("Adding author-article relationships...")
    relation_counter = Counter()
    author_work_pairs = set()

    for work in tqdm(works_data, desc="Relationships"):
        work_id = work.get("id", "").split("/")[-1]
        if work_id not in G:
            continue

        for authorship in work.get("authorships", []):
            original_author_id = (
                authorship.get("author", {}).get("id", "").split("/")[-1]
            )
            if not original_author_id:
                continue

            consolidated_author_id = None
            for author_id, data in consolidated_authors.items():
                if original_author_id == author_id or original_author_id in data.get(
                    "alias_ids", []
                ):
                    consolidated_author_id = author_id
                    break

            if (
                consolidated_author_id
                and (consolidated_author_id, work_id) not in author_work_pairs
            ):
                G.add_edge(consolidated_author_id, work_id, type="authored")
                author_work_pairs.add((consolidated_author_id, work_id))
                relation_counter[consolidated_author_id] += 1

    print_relationship_stats(G, relation_counter, author_work_pairs)

    return G, relation_counter


def print_relationship_stats(
    G: nx.Graph, relation_counter: Counter, author_work_pairs: Set
) -> None:
    """Print statistics about the relationships between authors and works.

    Args:
        G: NetworkX graph containing author and work nodes
        relation_counter: Counter for relations
        author_work_pairs: Set of author-work pairs
    """
    logger.info("\n📊 RELATIONSHIP REPORT")
    logger.info(f"Total author-article relationships: {len(author_work_pairs)}")

    top_authors = relation_counter.most_common(5)
    logger.info("\n🏆 Top 5 authors with most articles:")
    for author_id, count in top_authors:
        author_name = G.nodes[author_id].get("display_name", "Unknown")
        logger.info(f" - {author_name} (ID: {author_id}): {count} articles")
