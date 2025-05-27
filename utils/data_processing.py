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
    try:
        with open(authors_file, "r", encoding="utf-8") as f:
            authors_data = json.load(f)
        
        if not isinstance(authors_data, dict):
            logger.error("Authors data is not a dictionary")
            return {}, {}
            
        logger.info(f"✅ Loaded {len(authors_data)} authors")
    except Exception as e:
        logger.error(f"Failed to load authors file {authors_file}: {e}")
        return {}, {}

    # Load works data  
    logger.info("📄 Loading works data...")
    try:
        with open(works_file, "r", encoding="utf-8") as f:
            works_raw = json.load(f)
        
        # Handle both list and dict formats
        if isinstance(works_raw, list):
            logger.info("🔄 Converting works list to dictionary format...")
            works_data = {}
            for i, work in enumerate(tqdm(works_raw, desc="Processing works")):
                if not isinstance(work, dict):
                    logger.warning(f"Skipping non-dict work at index {i}")
                    continue
                    
                # Extract work ID safely
                work_id = None
                if "id" in work and isinstance(work["id"], str):
                    work_id = work["id"].split("/")[-1]
                elif "work_id" in work:
                    work_id = str(work["work_id"])
                
                if not work_id:
                    work_id = f"work_{len(works_data)}"
                    logger.warning(f"Generated ID {work_id} for work at index {i}")
                
                works_data[work_id] = work
        elif isinstance(works_raw, dict):
            works_data = works_raw
        else:
            logger.error("Works data is neither a list nor a dictionary")
            return authors_data, {}
            
        logger.info(f"✅ Loaded {len(works_data)} works")
    except Exception as e:
        logger.error(f"Failed to load works file {works_file}: {e}")
        return authors_data, {}

    logger.info(f"✅ Data loaded successfully: {len(authors_data)} authors, {len(works_data)} articles")
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
    
    processed_works = 0
    skipped_works = 0
    
    for work_id, work in tqdm(works_data.items(), desc="Building author-work map"):
        if not isinstance(work, dict):
            skipped_works += 1
            logger.warning(f"Skipping work {work_id}: not a dictionary")
            continue
            
        # Get authorships safely
        authorships = work.get("authorships", [])
        if not isinstance(authorships, list):
            skipped_works += 1
            logger.warning(f"Skipping work {work_id}: authorships is not a list")
            continue
        
        # Extract clean work ID
        try:
            work_id_field = work.get("id", work_id)
            if isinstance(work_id_field, str):
                clean_work_id = work_id_field.split("/")[-1]
            else:
                clean_work_id = str(work_id)
        except Exception as e:
            clean_work_id = str(work_id)
            logger.warning(f"Error extracting work ID for {work_id}: {e}")
        
        # Process each authorship
        for authorship in authorships:
            if not isinstance(authorship, dict):
                continue
                
            try:
                author_info = authorship.get("author", {})
                if not isinstance(author_info, dict):
                    continue
                    
                author_id_field = author_info.get("id", "")
                if isinstance(author_id_field, str) and author_id_field:
                    author_id = author_id_field.split("/")[-1]
                    if author_id:
                        author_work_map[author_id].append(clean_work_id)
            except Exception as e:
                logger.warning(f"Error processing authorship in work {work_id}: {e}")
                continue
        
        processed_works += 1
    
    logger.info(f"✅ Author-work map built: {len(author_work_map)} authors mapped")
    logger.info(f"   📊 Processed: {processed_works} works, Skipped: {skipped_works} works")
    
    # Log some statistics
    if author_work_map:
        work_counts = [len(works) for works in author_work_map.values()]
        logger.info(f"   📚 Works per author: min={min(work_counts)}, max={max(work_counts)}, avg={sum(work_counts)/len(work_counts):.1f}")
    
    return dict(author_work_map)


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
            
            # Ensure author exists in graph
            if author_id not in G.nodes:
                logger.warning(f"Author {author_id} not found in graph, skipping")
                continue
                
            try:
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
                    "last_known_institutions": G.nodes[author_id].get("last_known_institutions", []),
                }
            except Exception as e:
                logger.error(f"Error processing single author {author_id}: {e}")
            continue

        # Filter out authors not in graph
        valid_authors = [a for a in component_list if a in G.nodes]
        if not valid_authors:
            logger.warning(f"No valid authors found in component of size {len(component_list)}")
            continue
            
        component_list = valid_authors

        try:
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
                "max_works": max(works_counts) if works_counts else 0,
                "min_works": min(works_counts) if works_counts else 0,
                "authors": component_list,
            }
            component_stats.append(stats)

            all_alt_names = []
            main_author_name = G.nodes[main_author].get("name", "")

            for a in component_list:
                try:
                    author_name = G.nodes[a].get("name", "")
                    if author_name and author_name != main_author_name:
                        all_alt_names.append(author_name)

                    alt_names = G.nodes[a].get("alt_names", [])
                    if isinstance(alt_names, list):
                        for alt_name in alt_names:
                            if alt_name and alt_name != main_author_name:
                                all_alt_names.append(alt_name)
                except Exception as e:
                    logger.warning(f"Error processing alt names for author {a}: {e}")

            unique_alt_names = []
            seen_names = set()
            for name in all_alt_names:
                if name and name not in seen_names:
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

            # Safely collect additional data
            try:
                combined["affiliations"] = collect_unique_affiliations(G, component_list)
                combined["topics"] = collect_unique_topics(G, component_list)
                combined["x_concepts"] = collect_unique_concepts(G, component_list)
            except Exception as e:
                logger.warning(f"Error collecting additional data for component {main_author}: {e}")
                combined["affiliations"] = []
                combined["topics"] = []
                combined["x_concepts"] = []

            try:
                all_institutions = set()
                for a in component_list:
                    institutions = G.nodes[a].get("last_known_institutions", [])
                    if isinstance(institutions, list):
                        for inst in institutions:
                            if isinstance(inst, str) and inst:
                                all_institutions.add(inst)
                combined["last_known_institutions"] = list(all_institutions)
            except Exception as e:
                logger.warning(f"Error collecting institutions for component {main_author}: {e}")
                combined["last_known_institutions"] = []

            try:
                combined["h_index"] = max(G.nodes[a].get("h_index", 0) for a in component_list)
            except Exception as e:
                logger.warning(f"Error calculating h_index for component {main_author}: {e}")
                combined["h_index"] = 0

            consolidated[main_author] = combined
            
        except Exception as e:
            logger.error(f"Error processing component of size {len(component_list)}: {e}")
            continue

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
        try:
            if a not in G.nodes:
                continue
            affiliations = G.nodes[a].get("affiliations", [])
            if isinstance(affiliations, list):
                for affil in affiliations:
                    if isinstance(affil, dict):
                        all_affiliations.append(affil)
        except Exception as e:
            logger.warning(f"Error collecting affiliations for author {a}: {e}")

    unique_affiliations = []
    seen_affil_tuples = set()
    for affil in all_affiliations:
        try:
            hashable_items = []
            for k, v in sorted(affil.items()):
                if isinstance(v, list):
                    v = tuple(v)
                elif isinstance(v, dict):
                    # Convert nested dict to tuple of sorted items
                    v = tuple(sorted(v.items()))
                hashable_items.append((k, v))

            affil_items = tuple(hashable_items)
            if affil_items not in seen_affil_tuples:
                seen_affil_tuples.add(affil_items)
                unique_affiliations.append(affil)
        except Exception as e:
            logger.warning(f"Error processing affiliation {affil}: {e}")

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
        try:
            if a not in G.nodes:
                continue
            topics = G.nodes[a].get("topics", [])
            if isinstance(topics, list):
                for topic in topics:
                    if isinstance(topic, dict):
                        all_topics.append(topic)
        except Exception as e:
            logger.warning(f"Error collecting topics for author {a}: {e}")

    unique_topics = []
    seen_topic_tuples = set()
    for topic in all_topics:
        try:
            hashable_items = []
            for k, v in sorted(topic.items()):
                if isinstance(v, list):
                    v = tuple(v)
                elif isinstance(v, dict):
                    v = tuple(sorted(v.items()))
                hashable_items.append((k, v))

            topic_items = tuple(hashable_items)
            if topic_items not in seen_topic_tuples:
                seen_topic_tuples.add(topic_items)
                unique_topics.append(topic)
        except Exception as e:
            logger.warning(f"Error processing topic {topic}: {e}")

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
        try:
            if a not in G.nodes:
                continue
            concepts = G.nodes[a].get("x_concepts", [])
            if isinstance(concepts, list):
                for concept in concepts:
                    if isinstance(concept, dict):
                        all_concepts.append(concept)
        except Exception as e:
            logger.warning(f"Error collecting concepts for author {a}: {e}")

    unique_concepts = []
    seen_concept_tuples = set()
    for concept in all_concepts:
        try:
            hashable_items = []
            for k, v in sorted(concept.items()):
                if isinstance(v, list):
                    v = tuple(v)
                elif isinstance(v, dict):
                    v = tuple(sorted(v.items()))
                hashable_items.append((k, v))

            concept_items = tuple(hashable_items)
            if concept_items not in seen_concept_tuples:
                seen_concept_tuples.add(concept_items)
                unique_concepts.append(concept)
        except Exception as e:
            logger.warning(f"Error processing concept {concept}: {e}")

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
    
    if len(authors_data) > 0:
        reduction = (1 - len(consolidated)/len(authors_data))*100
        logger.info(f"Reduction: {reduction:.1f}%")
    else:
        logger.info("Reduction: N/A (no original authors)")

    if not component_stats:
        logger.info("No multi-author components found")
        return

    component_sizes = [
        c["num_authors"] for c in component_stats if c["num_authors"] > 1
    ]
    
    if component_sizes:
        size_dist = Counter(component_sizes)
        logger.info("\n📦 Component size distribution:")
        for size, count in sorted(size_dist.items()):
            logger.info(f" - Components with {size} authors: {count}")

        logger.info("\n🏆 Top 5 largest components:")
        sorted_components = sorted(
            component_stats, key=lambda x: x["num_authors"], reverse=True
        )[:5]
        
        for comp in sorted_components:
            try:
                main_author_id = comp["main_author"]
                if main_author_id in G.nodes:
                    main_name = G.nodes[main_author_id].get("name", "Unknown")
                else:
                    main_name = "Unknown (not in graph)"
                    
                logger.info(f" - {main_name} (ID: {main_author_id}):")
                logger.info(f"   👥 Authors: {comp['num_authors']}")
                logger.info(f"   📚 Total articles: {comp['total_works']}")
                logger.info(f"   🎯 Article range: {comp['min_works']}-{comp['max_works']}")
            except Exception as e:
                logger.warning(f"Error displaying component stats: {e}")
    else:
        logger.info("No multi-author components found")


def build_full_graph(
    consolidated_authors: Dict, works_data: Dict
) -> Tuple[nx.Graph, Dict]:
    """Build the complete graph with consolidated authors and articles.

    Args:
        consolidated_authors: Dictionary of consolidated authors (author_id -> author_data)
        works_data: Dictionary of work data (work_id -> work_data)

    Returns:
        NetworkX graph containing authors and works with relationships,
        and a dictionary of relations for logging
    """
    logger.info("\nBuilding complete graph...")
    
    # Validate input data
    if not isinstance(consolidated_authors, dict):
        logger.error(f"consolidated_authors must be a dictionary, got {type(consolidated_authors)}")
        return nx.Graph(), {}
        
    if not isinstance(works_data, dict):
        logger.error(f"works_data must be a dictionary, got {type(works_data)}")
        return nx.Graph(), {}
    
    logger.info(f"📊 Input validation: {len(consolidated_authors)} authors, {len(works_data)} works")
    
    G = nx.Graph()

    logger.info("Adding consolidated authors...")
    authors_added = 0
    authors_skipped = 0
    
    for author_id, author_data in tqdm(consolidated_authors.items(), desc="Authors"):
        try:
            # Validate author_id
            if not isinstance(author_id, str) or not author_id.strip():
                authors_skipped += 1
                logger.warning(f"Skipping invalid author ID: {author_id}")
                continue
                
            # Validate author_data
            if not isinstance(author_data, dict):
                authors_skipped += 1
                logger.warning(f"Skipping author {author_id}: data is not a dictionary")
                continue
                
            # Add node with safe data extraction
            node_attrs = dict(author_data)  # Make a copy
            node_attrs["type_node"] = "Author"
            
            G.add_node(author_id, **node_attrs)
            authors_added += 1
            
        except Exception as e:
            authors_skipped += 1
            logger.error(f"Error adding author {author_id}: {e}")
            
    logger.info(f"✅ Authors added: {authors_added}, skipped: {authors_skipped}")

    logger.info("Adding articles...")
    articles_added = 0
    articles_skipped = 0
    
    for work_id, work in tqdm(works_data.items(), desc="Articles"):
        # Ensure work is a dictionary
        if not isinstance(work, dict):
            articles_skipped += 1
            logger.warning(f"Skipping work {work_id}: not a dictionary")
            continue
            
        # Validate work_id
        if not isinstance(work_id, str) or not work_id.strip():
            articles_skipped += 1
            logger.warning(f"Skipping work with invalid ID: {work_id}")
            continue
            
        # Extract clean work ID (remove URL prefix if present)
        try:
            work_id_field = work.get("id", work_id)
            if isinstance(work_id_field, str) and work_id_field.strip():
                clean_work_id = work_id_field.split("/")[-1]
            else:
                clean_work_id = str(work_id)
        except (AttributeError, IndexError, TypeError) as e:
            logger.warning(f"Error extracting work ID for {work_id}: {e}")
            clean_work_id = str(work_id)
            
        # Skip if clean_work_id is empty
        if not clean_work_id.strip():
            articles_skipped += 1
            logger.warning(f"Skipping work with empty clean ID: {work_id}")
            continue
            
        # Extract concepts safely
        concepts = []
        try:
            concepts_data = work.get("concepts", [])
            if isinstance(concepts_data, list):
                for concept in concepts_data:
                    if isinstance(concept, dict):
                        concept_clean = {
                            "id": str(concept.get("id", "")),
                            "display_name": str(concept.get("display_name", "")),
                            "level": int(concept.get("level", 0)) if isinstance(concept.get("level"), (int, float)) else 0,
                            "score": float(concept.get("score", 0.0)) if isinstance(concept.get("score"), (int, float)) else 0.0,
                        }
                        concepts.append(concept_clean)
        except Exception as e:
            logger.warning(f"Error processing concepts for work {clean_work_id}: {e}")

        # Add node with error handling and safe data extraction
        try:
            # Extract and validate fields safely
            title = str(work.get("title", "")) if work.get("title") is not None else ""
            
            # Handle publication_year - could be int, string, or None
            pub_year = work.get("publication_year")
            if isinstance(pub_year, (int, float)):
                pub_year = int(pub_year)
            elif isinstance(pub_year, str) and pub_year.isdigit():
                pub_year = int(pub_year)
            else:
                pub_year = None
                
            # Handle cited_by_count - ensure it's an integer
            cited_count = work.get("cited_by_count", 0)
            if isinstance(cited_count, (int, float)):
                cited_count = int(cited_count)
            else:
                cited_count = 0
                
            # Handle is_oa - ensure it's a boolean
            is_oa = work.get("is_oa", False)
            if not isinstance(is_oa, bool):
                is_oa = bool(is_oa) if is_oa is not None else False
                
            # Handle referenced_works_count
            ref_works_count = work.get("referenced_works_count", 0)
            if isinstance(ref_works_count, (int, float)):
                ref_works_count = int(ref_works_count)
            else:
                ref_works_count = 0
            
            G.add_node(
                clean_work_id,
                title=title,
                publication_year=pub_year,
                publication_date=str(work.get("publication_date", "")),
                cited_by_count=cited_count,
                is_oa=is_oa,
                type_node="Work",
                concepts=concepts,
                primary_topic=work.get("primary_topic", {}) if isinstance(work.get("primary_topic"), dict) else {},
                topics=work.get("topics", []) if isinstance(work.get("topics"), list) else [],
                keywords=work.get("keywords", []) if isinstance(work.get("keywords"), list) else [],
                open_access=work.get("open_access", {}) if isinstance(work.get("open_access"), dict) else {},
                biblio=work.get("biblio", {}) if isinstance(work.get("biblio"), dict) else {},
                referenced_works_count=ref_works_count,
                related_works=work.get("related_works", []) if isinstance(work.get("related_works"), list) else [],
                abstract_inverted_index=work.get("abstract_inverted_index", {}) if isinstance(work.get("abstract_inverted_index"), dict) else {},
            )
            articles_added += 1
        except Exception as e:
            articles_skipped += 1
            logger.error(f"Error adding work node {clean_work_id}: {e}")
            continue
            
    logger.info(f"✅ Articles added: {articles_added}, skipped: {articles_skipped}")

    logger.info("Adding author-article relationships...")
    relation_counter = Counter()
    author_work_pairs = set()
    relationships_added = 0
    relationships_skipped = 0

    for work_id, work in tqdm(works_data.items(), desc="Relationships"):
        # Ensure work is a dictionary
        if not isinstance(work, dict):
            relationships_skipped += 1
            logger.debug(f"Skipping work {work_id}: not a dictionary")
            continue
            
        # Validate work_id
        if not isinstance(work_id, str) or not work_id.strip():
            relationships_skipped += 1
            logger.debug(f"Skipping work with invalid ID: {work_id}")
            continue
            
        # Extract clean work ID (remove URL prefix if present)
        try:
            work_id_field = work.get("id", work_id)
            if isinstance(work_id_field, str) and work_id_field.strip():
                clean_work_id = work_id_field.split("/")[-1]
            else:
                clean_work_id = str(work_id)
        except (AttributeError, IndexError, TypeError) as e:
            logger.warning(f"Error extracting work ID for {work_id}: {e}")
            clean_work_id = str(work_id)
            
        # Skip if clean_work_id is empty or not in graph
        if not clean_work_id.strip():
            relationships_skipped += 1
            continue
            
        if clean_work_id not in G:
            relationships_skipped += 1
            logger.debug(f"Work {clean_work_id} not found in graph")
            continue

        # Ensure authorships is a list
        authorships = work.get("authorships", [])
        if not isinstance(authorships, list):
            relationships_skipped += 1
            logger.warning(f"Authorships for work {clean_work_id} is not a list")
            continue

        for authorship in authorships:
            if not isinstance(authorship, dict):
                logger.debug(f"Skipping invalid authorship in work {clean_work_id}")
                continue
                
            # Extract author ID safely
            try:
                author_info = authorship.get("author", {})
                if not isinstance(author_info, dict):
                    continue
                    
                author_id_field = author_info.get("id", "")
                if isinstance(author_id_field, str) and author_id_field.strip():
                    original_author_id = author_id_field.split("/")[-1]
                else:
                    continue
            except (AttributeError, IndexError, TypeError) as e:
                logger.debug(f"Error extracting author ID in work {clean_work_id}: {e}")
                continue
                
            if not original_author_id or not original_author_id.strip():
                continue

            # Find consolidated author ID
            consolidated_author_id = None
            try:
                for author_id, data in consolidated_authors.items():
                    if not isinstance(data, dict):
                        continue
                        
                    # Check if this is the main author or an alias
                    if original_author_id == author_id:
                        consolidated_author_id = author_id
                        break
                    elif original_author_id in data.get("alias_ids", []):
                        consolidated_author_id = author_id
                        break
            except Exception as e:
                logger.debug(f"Error finding consolidated author for {original_author_id}: {e}")
                continue

            # Add edge if valid relationship found
            if (
                consolidated_author_id
                and isinstance(consolidated_author_id, str)
                and consolidated_author_id.strip()
                and consolidated_author_id in G  # Ensure author exists in graph
                and (consolidated_author_id, clean_work_id) not in author_work_pairs
            ):
                try:
                    G.add_edge(consolidated_author_id, clean_work_id, type="authored")
                    author_work_pairs.add((consolidated_author_id, clean_work_id))
                    relation_counter[consolidated_author_id] += 1
                    relationships_added += 1
                except Exception as e:
                    relationships_skipped += 1
                    logger.warning(f"Error adding edge {consolidated_author_id} -> {clean_work_id}: {e}")
            else:
                relationships_skipped += 1

    logger.info(f"✅ Relationships added: {relationships_added}, skipped: {relationships_skipped}")
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
    try:
        logger.info("\n📊 RELATIONSHIP REPORT")
        logger.info(f"Total author-article relationships: {len(author_work_pairs)}")

        if relation_counter and len(relation_counter) > 0:
            top_authors = relation_counter.most_common(5)
            logger.info("\n🏆 Top 5 authors with most articles:")
            for author_id, count in top_authors:
                try:
                    if author_id in G.nodes:
                        author_name = G.nodes[author_id].get("display_name", "Unknown")
                        # Ensure name is a string
                        if not isinstance(author_name, str):
                            author_name = str(author_name) if author_name is not None else "Unknown"
                    else:
                        author_name = "Unknown (not in graph)"
                    logger.info(f" - {author_name} (ID: {author_id}): {count} articles")
                except Exception as e:
                    logger.warning(f"Error displaying author {author_id}: {e}")
        else:
            logger.info("No relationships found")
            
        # Additional graph statistics
        try:
            author_nodes = [n for n, d in G.nodes(data=True) if d.get("type_node") == "Author"]
            work_nodes = [n for n, d in G.nodes(data=True) if d.get("type_node") == "Work"]
            
            logger.info(f"\n📈 Graph statistics:")
            logger.info(f" - Total nodes: {G.number_of_nodes()}")
            logger.info(f" - Author nodes: {len(author_nodes)}")
            logger.info(f" - Work nodes: {len(work_nodes)}")
            logger.info(f" - Total edges: {G.number_of_edges()}")
            
            if G.number_of_nodes() > 0:
                density = G.number_of_edges() / (G.number_of_nodes() * (G.number_of_nodes() - 1) / 2)
                logger.info(f" - Graph density: {density:.6f}")
                
        except Exception as e:
            logger.warning(f"Error calculating graph statistics: {e}")
            
    except Exception as e:
        logger.error(f"Error in print_relationship_stats: {e}")


def load_sample_data(file_path: str, sample_size: int = None) -> Dict:
    """
    Load sample data for testing and benchmarking.
    
    Args:
        file_path: Path to the data file
        sample_size: Optional limit on number of authors to load
        
    Returns:
        Dictionary with sampled data
    """
    logger.info(f"📁 Loading sample data from: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        authors = data.get('authors', {})
        works = data.get('works', {})
        
        # Sample data if requested
        if sample_size and len(authors) > sample_size:
            logger.info(f"🎯 Sampling {sample_size} authors from {len(authors)} total")
            author_ids = list(authors.keys())[:sample_size]
            authors = {aid: authors[aid] for aid in author_ids}
        
        logger.info(f"✅ Loaded {len(authors)} authors")
        
        return {
            'authors': authors,
            'works': works
        }
        
    except Exception as e:
        logger.error(f"❌ Error loading sample data: {e}")
        return {'authors': {}, 'works': {}}


def create_test_dataset(authors_data: Dict, works_data: Dict, 
                       target_size: int = 1000) -> Dict:
    """
    Create a test dataset with specific characteristics for benchmarking.
    
    Args:
        authors_data: Full authors data
        works_data: Full works data
        target_size: Target number of authors
        
    Returns:
        Test dataset with authors and works
    """
    logger.info(f"🔧 Creating test dataset with {target_size} authors")
    
    # Select diverse authors for testing
    selected_authors = {}
    author_ids = list(authors_data.keys())
    
    # Try to get a diverse sample
    step = max(1, len(author_ids) // target_size)
    for i in range(0, min(len(author_ids), target_size * step), step):
        if len(selected_authors) >= target_size:
            break
        author_id = author_ids[i]
        selected_authors[author_id] = authors_data[author_id]
    
    # Filter works to only include those by selected authors
    selected_works = {}
    for work_id, work_data in works_data.items():
        for authorship in work_data.get('authorships', []):
            author_id = authorship.get('author', {}).get('id', '').split('/')[-1]
            if author_id in selected_authors:
                selected_works[work_id] = work_data
                break
    
    logger.info(f"✅ Created test dataset: {len(selected_authors)} authors, {len(selected_works)} works")
    
    return {
        'authors': selected_authors,
        'works': selected_works
    }
