import json
import logging
import networkx as nx
from tqdm import tqdm
from typing import Dict, List, Tuple
from collections import defaultdict

from db.db_connection import Neo4jConnection

logger = logging.getLogger(__name__)


def save_to_neo4j(G: nx.Graph, consolidated_authors: Dict, works_data: Dict) -> None:
    """Save the graph data to Neo4j database with enhanced error handling.

    Args:
        G: NetworkX graph containing authors and works
        consolidated_authors: Dictionary of consolidated authors
        works_data: Dictionary of work data
    """
    logger.info("\nInitiating Neo4j database save...")
    neo4j_conn = None

    try:
        # Validate input parameters
        if not G or G.number_of_nodes() == 0:
            raise ValueError("Graph G is empty or None")
        if not consolidated_authors:
            raise ValueError("consolidated_authors is empty or None")
        if not works_data:
            raise ValueError("works_data is empty or None")

        logger.info(f"Input validation passed: {G.number_of_nodes():,} nodes, {len(consolidated_authors):,} authors, {len(works_data):,} works")

        neo4j_conn = Neo4jConnection()
        logger.info("✅ Neo4j connection established")

        logger.info("Cleaning existing database...")
        neo4j_conn.execute_query("MATCH (n) DETACH DELETE n", return_data=False)

        setup_database_constraints(neo4j_conn)

        author_nodes, work_nodes, concept_nodes, relationships = prepare_data(G)

        # Validate prepared data
        logger.info(f"Data preparation completed: {len(author_nodes)} authors, {len(work_nodes)} works, {len(concept_nodes)} concepts, {len(relationships)} relationships")

        insert_concepts(neo4j_conn, concept_nodes)

        insert_authors(neo4j_conn, author_nodes)

        insert_works(neo4j_conn, work_nodes)

        insert_author_work_relationships(neo4j_conn, relationships, G)

        insert_work_references(neo4j_conn, works_data)

        insert_author_affiliations(neo4j_conn, consolidated_authors)

        insert_author_topics(neo4j_conn, consolidated_authors)

        print_database_stats(neo4j_conn, G, relationships)

        neo4j_conn.close()
        logger.info("✅ Neo4j connection closed correctly")

    except Exception as e:
        logger.error(f"\n❌ Error saving data to Neo4j: {str(e)}", exc_info=True)
        if neo4j_conn:
            try:
                neo4j_conn.close()
                logger.info("Neo4j connection closed after error")
            except:
                logger.error("Failed to close Neo4j connection after error")
        raise


def setup_database_constraints(neo4j_conn: Neo4jConnection) -> None:
    """Set up database constraints and indexes with improved error handling.

    Args:
        neo4j_conn: Neo4j database connection
    """
    logger.info("Dropping existing constraints and indexes...")
    try:
        # Drop existing constraints
        constraints = neo4j_conn.execute_query("SHOW CONSTRAINTS")
        for constraint in constraints:
            constraint_name = constraint.get("name")
            if constraint_name:
                try:
                    neo4j_conn.execute_query(
                        f"DROP CONSTRAINT {constraint_name} IF EXISTS", return_data=False
                    )
                except Exception as e:
                    logger.warning(f"Could not drop constraint {constraint_name}: {e}")

        # Drop existing indexes
        indexes = neo4j_conn.execute_query("SHOW INDEXES")
        for index in indexes:
            index_name = index.get("name")
            if index_name and not index_name.startswith("constraint_"):
                try:
                    neo4j_conn.execute_query(
                        f"DROP INDEX {index_name} IF EXISTS", return_data=False
                    )
                except Exception as e:
                    logger.warning(f"Could not drop index {index_name}: {e}")

        logger.info("✅ Existing constraints and indexes dropped successfully")
    except Exception as e:
        logger.error(f"❌ Error dropping constraints and indexes: {e}")

    logger.info("Creating new constraints and indexes...")
    try:
        # Create constraints with better error handling
        constraints_queries = [
            "CREATE CONSTRAINT constraint_author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT constraint_work_id IF NOT EXISTS FOR (w:Work) REQUIRE w.id IS UNIQUE", 
            "CREATE CONSTRAINT constraint_concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
            "CREATE INDEX index_country IF NOT EXISTS FOR (i:Institution) ON (i.country_code)"
        ]
        
        for query in constraints_queries:
            try:
                neo4j_conn.execute_query(query, return_data=False)
            except Exception as e:
                logger.warning(f"Could not create constraint/index with query '{query}': {e}")
                
        logger.info("✅ New constraints and indexes created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating constraints and indexes: {e}")


def prepare_data(G: nx.Graph) -> Tuple[List, List, List, List]:
    """Prepare data from the graph for insertion into Neo4j with validation.

    Args:
        G: NetworkX graph containing authors and works

    Returns:
        Tuple containing author nodes, work nodes, concept nodes, and relationships
    """
    if not G or G.number_of_nodes() == 0:
        logger.warning("Graph is empty or None")
        return [], [], [], []

    author_nodes = []
    work_nodes = []
    concept_nodes = []
    concept_ids_seen = set()
    relationships = []

    logger.info("Preparing authors for insertion...")
    for node_id, node_data in G.nodes(data=True):
        if not node_data:
            logger.warning(f"Node {node_id} has no data, skipping")
            continue
            
        if node_data.get("type_node") == "Author":
            # Validate author data
            if not node_id or not isinstance(node_id, str):
                logger.warning(f"Invalid author ID: {node_id}, skipping")
                continue
                
            author_nodes.append((node_id, node_data))

            # Process author concepts safely
            for concept in node_data.get("x_concepts", []):
                if not isinstance(concept, dict) or "id" not in concept:
                    continue
                    
                concept_id = concept["id"]
                if concept_id not in concept_ids_seen:
                    concept_ids_seen.add(concept_id)
                    concept_dict = {
                        "id": concept["id"],
                        "display_name": concept.get("display_name", ""),
                        "level": concept.get("level", 0),
                        "score": concept.get("score", 0.0),
                    }
                    concept_nodes.append((concept_id, concept_dict))

    logger.info("Preparing articles for insertion...")
    for node_id, node_data in G.nodes(data=True):
        if not node_data:
            continue
            
        if node_data.get("type_node") == "Work":
            # Validate work data
            if not node_id or not isinstance(node_id, str):
                logger.warning(f"Invalid work ID: {node_id}, skipping")
                continue

            # Clean biblio data safely
            biblio_data = node_data.get("biblio", {})
            clean_biblio = {}

            if isinstance(biblio_data, dict):
                for key, value in biblio_data.items():
                    try:
                        if isinstance(value, dict):
                            clean_biblio[key + "_json"] = json.dumps(value)
                        elif isinstance(value, (str, int, float, bool)) or value is None:
                            clean_biblio[key] = value
                        elif isinstance(value, list):
                            clean_biblio[key + "_json"] = json.dumps(value)
                    except Exception as e:
                        logger.warning(f"Error processing biblio field {key}: {e}")

            node_data_copy = dict(node_data)
            node_data_copy["biblio"] = clean_biblio

            work_nodes.append((node_id, node_data_copy))

            # Process work concepts safely
            for concept in node_data.get("concepts", []):
                if not isinstance(concept, dict) or "id" not in concept:
                    continue
                    
                concept_id = concept["id"]
                if concept_id not in concept_ids_seen:
                    concept_ids_seen.add(concept_id)
                    concept_dict = {
                        "id": concept["id"],
                        "display_name": concept.get("display_name", ""),
                        "level": concept.get("level", 0),
                        "score": concept.get("score", 0.0),
                    }
                    concept_nodes.append((concept_id, concept_dict))

    # Prepare relationships safely
    logger.info("Preparing relationships for insertion...")
    for edge in G.edges(data=True):
        if len(edge) != 3:
            continue
            
        node1, node2, edge_data = edge
        
        # Validate nodes exist in graph
        if node1 not in G.nodes or node2 not in G.nodes:
            continue
            
        node1_data = G.nodes[node1]
        node2_data = G.nodes[node2]
        
        # Create author-work relationships
        if (node1_data.get("type_node") == "Author" and 
            node2_data.get("type_node") == "Work"):
            relationships.append({"author_id": node1, "work_id": node2})
        elif (node1_data.get("type_node") == "Work" and 
              node2_data.get("type_node") == "Author"):
            relationships.append({"author_id": node2, "work_id": node1})

    logger.info(f"Data preparation completed: {len(author_nodes)} authors, {len(work_nodes)} works, {len(concept_nodes)} concepts, {len(relationships)} relationships")
    return author_nodes, work_nodes, concept_nodes, relationships


def insert_concepts(neo4j_conn: Neo4jConnection, concept_nodes: List) -> None:
    """Insert concept nodes into Neo4j with error handling.

    Args:
        neo4j_conn: Neo4j database connection
        concept_nodes: List of concept nodes to insert
    """
    if not concept_nodes:
        logger.info("No concepts to insert")
        return
        
    logger.info(f"Inserting {len(concept_nodes)} concepts...")
    concept_batches = [
        concept_nodes[i : i + 500] for i in range(0, len(concept_nodes), 500)
    ]

    for batch_num, batch in enumerate(tqdm(concept_batches, desc="Inserting concepts"), 1):
        try:
            query = """
            UNWIND $concepts AS concept
            MERGE (c:Concept {id: concept.id})
            ON CREATE SET 
                c.display_name = concept.display_name,
                c.level = concept.level,
                c.score = concept.score
            """
            
            # Validate batch data
            valid_concepts = []
            for c in batch:
                if len(c) == 2 and isinstance(c[1], dict) and "id" in c[1]:
                    valid_concepts.append(c[1])
                else:
                    logger.warning(f"Invalid concept in batch {batch_num}: {c}")
                    
            if valid_concepts:
                params = {"concepts": valid_concepts}
                neo4j_conn.execute_query(query, params, return_data=False)
            else:
                logger.warning(f"No valid concepts in batch {batch_num}")
                
        except Exception as e:
            logger.error(f"Error inserting concept batch {batch_num}: {e}")
            # Continue with next batch instead of failing completely
            continue


def insert_authors(neo4j_conn: Neo4jConnection, author_nodes: List) -> None:
    """Insert author nodes into Neo4j with enhanced validation.

    Args:
        neo4j_conn: Neo4j database connection
        author_nodes: List of author nodes to insert
    """
    if not author_nodes:
        logger.info("No authors to insert")
        return
        
    batch_size = 100
    logger.info(f"Inserting {len(author_nodes)} authors (batch size: {batch_size})...")
    author_batches = [
        author_nodes[i : i + batch_size]
        for i in range(0, len(author_nodes), batch_size)
    ]

    for batch_num, batch in enumerate(tqdm(author_batches, desc="Inserting authors"), 1):
        try:
            query = """
            UNWIND $authors AS author
            MERGE (a:Author {id: author.id})
            ON CREATE SET 
                a.display_name = author.data.display_name,
                a.works_count = author.data.works_count,
                a.cited_by_count = author.data.cited_by_count,
                a.display_name_alternatives = author.data.display_name_alternatives,
                a.alias_ids = author.data.alias_ids,
                a.orcid = author.data.orcid,
                a.h_index = author.data.h_index,
                a.last_known_institutions = author.data.last_known_institutions
            ON MATCH SET 
                a.display_name = author.data.display_name,
                a.works_count = author.data.works_count,
                a.cited_by_count = author.data.cited_by_count,
                a.display_name_alternatives = author.data.display_name_alternatives,
                a.alias_ids = author.data.alias_ids,
                a.orcid = author.data.orcid,
                a.h_index = author.data.h_index,
                a.last_known_institutions = author.data.last_known_institutions
            WITH a, author
            UNWIND author.data.x_concepts AS concept
            MATCH (c:Concept {id: concept.id})
            MERGE (a)-[r:HAS_CONCEPT]->(c)
            ON CREATE SET r.score = concept.score
            """
            
            # Validate and prepare batch data
            valid_authors = []
            for author_id, data in batch:
                if not author_id or not isinstance(data, dict):
                    logger.warning(f"Invalid author data: {author_id}")
                    continue
                    
                try:
                    author_param = {
                        "id": author_id,
                        "data": {
                            "display_name": data.get("display_name", ""),
                            "works_count": max(0, data.get("works_count", 0)),
                            "cited_by_count": max(0, data.get("cited_by_count", 0)),
                            "display_name_alternatives": data.get("display_name_alternatives", []) if isinstance(data.get("display_name_alternatives"), list) else [],
                            "alias_ids": data.get("alias_ids", []) if isinstance(data.get("alias_ids"), list) else [],
                            "orcid": str(data.get("orcid", "")),
                            "h_index": max(0, data.get("h_index", 0)),
                            "last_known_institutions": data.get("last_known_institutions", []) if isinstance(data.get("last_known_institutions"), list) else [],
                            "x_concepts": [
                                {"id": c["id"], "score": max(0.0, c.get("score", 0.0))}
                                for c in data.get("x_concepts", [])
                                if isinstance(c, dict) and "id" in c
                            ],
                        },
                    }
                    valid_authors.append(author_param)
                except Exception as e:
                    logger.warning(f"Error processing author {author_id}: {e}")
                    continue
                    
            if valid_authors:
                params = {"authors": valid_authors}
                neo4j_conn.execute_query(query, params, return_data=False)
            else:
                logger.warning(f"No valid authors in batch {batch_num}")
                
        except Exception as e:
            logger.error(f"Error inserting author batch {batch_num}: {e}")
            continue


def insert_works(neo4j_conn: Neo4jConnection, work_nodes: List) -> None:
    """Insert work nodes into Neo4j with enhanced validation.

    Args:
        neo4j_conn: Neo4j database connection
        work_nodes: List of work nodes to insert
    """
    if not work_nodes:
        logger.info("No works to insert")
        return
        
    batch_size = 100
    logger.info(f"Inserting {len(work_nodes)} articles (batch size: {batch_size})...")
    work_batches = [
        work_nodes[i : i + batch_size] for i in range(0, len(work_nodes), batch_size)
    ]

    for batch_num, batch in enumerate(tqdm(work_batches, desc="Inserting articles"), 1):
        try:
            query = """
            UNWIND $works AS work
            MERGE (w:Work {id: work.id})
            ON CREATE SET 
                w.title = work.title,
                w.publication_year = work.publication_year,
                w.publication_date = work.publication_date,
                w.cited_by_count = work.cited_by_count,
                w.is_oa = work.is_oa,
                w.referenced_works_count = work.referenced_works_count
            ON MATCH SET 
                w.title = work.title,
                w.publication_year = work.publication_year,
                w.publication_date = work.publication_date,
                w.cited_by_count = work.cited_by_count,
                w.is_oa = work.is_oa,
                w.referenced_works_count = work.referenced_works_count
            WITH w, work
            UNWIND work.concepts AS concept
            MATCH (c:Concept {id: concept.id})
            MERGE (w)-[r:HAS_CONCEPT]->(c)
            ON CREATE SET r.score = concept.score
            """

            # Validate and prepare batch data
            valid_works = []
            for work_id, data in batch:
                if not work_id or not isinstance(data, dict):
                    logger.warning(f"Invalid work data: {work_id}")
                    continue
                    
                try:
                    work_param = {
                        "id": work_id,
                        "title": str(data.get("title", "")).strip() or "Untitled",
                        "publication_year": data.get("publication_year") if isinstance(data.get("publication_year"), int) and data.get("publication_year") > 0 else None,
                        "publication_date": str(data.get("publication_date", "")),
                        "cited_by_count": max(0, data.get("cited_by_count", 0)),
                        "is_oa": bool(data.get("is_oa", False)),
                        "referenced_works_count": max(0, data.get("referenced_works_count", 0)),
                        "concepts": [
                            {"id": c["id"], "score": max(0.0, c.get("score", 0.0))}
                            for c in data.get("concepts", [])
                            if isinstance(c, dict) and "id" in c
                        ],
                    }

                    # Add biblio fields safely
                    for key, value in data.get("biblio", {}).items():
                        if isinstance(value, (str, int, float, bool)) or value is None:
                            work_param["biblio_" + key] = value

                    valid_works.append(work_param)
                except Exception as e:
                    logger.warning(f"Error processing work {work_id}: {e}")
                    continue

            if valid_works:
                params = {"works": valid_works}
                neo4j_conn.execute_query(query, params, return_data=False)
            else:
                logger.warning(f"No valid works in batch {batch_num}")
                
        except Exception as e:
            logger.error(f"Error inserting work batch {batch_num}: {e}")
            continue


def insert_author_work_relationships(
    neo4j_conn: Neo4jConnection, relationships: List[Dict], G: nx.Graph
) -> None:
    """Insert author-work relationships into Neo4j with validation.

    Args:
        neo4j_conn: Neo4j database connection
        relationships: List of author-work relationships to insert
        G: NetworkX graph for retrieving node data
    """
    if not relationships:
        logger.info("No relationships to insert")
        return
        
    batch_size = 100
    logger.info(f"Inserting {len(relationships)} relationships (batch size: {batch_size})...")
    rel_batches = [
        relationships[i : i + batch_size]
        for i in range(0, len(relationships), batch_size)
    ]

    for batch_num, batch in enumerate(tqdm(rel_batches, desc="Inserting relationships"), 1):
        try:
            if batch_num == 1:
                logger.info("\n📝 Relationship examples from first batch:")
                for rel in batch[:3]:
                    author_id = rel.get("author_id")
                    work_id = rel.get("work_id")
                    if author_id and work_id and author_id in G.nodes and work_id in G.nodes:
                        author_name = G.nodes[author_id].get("display_name", "Unknown")
                        work_title = G.nodes[work_id].get("title", "No title")[:50] + "..."
                        logger.info(f"   - {author_name} (ID: {author_id}) -> {work_title}")
                logger.info("    - ..................................................")

            # Validate relationships
            valid_relationships = []
            for rel in batch:
                if (isinstance(rel, dict) and 
                    "author_id" in rel and "work_id" in rel and
                    rel["author_id"] and rel["work_id"]):
                    valid_relationships.append(rel)
                else:
                    logger.warning(f"Invalid relationship in batch {batch_num}: {rel}")

            if valid_relationships:
                query = """
                UNWIND $relationships AS rel
                MATCH (a:Author {id: rel.author_id})
                MATCH (w:Work {id: rel.work_id})
                MERGE (a)-[r:AUTHORED]->(w)
                """
                neo4j_conn.execute_query(query, {"relationships": valid_relationships}, return_data=False)
            else:
                logger.warning(f"No valid relationships in batch {batch_num}")
                
        except Exception as e:
            logger.error(f"Error inserting relationship batch {batch_num}: {e}")
            continue


def insert_work_references(neo4j_conn: Neo4jConnection, works_data: Dict) -> None:
    """Insert work references into Neo4j with enhanced validation.

    Args:
        neo4j_conn: Neo4j database connection
        works_data: Dictionary of work data
    """
    if not works_data:
        logger.info("No works data for references")
        return
        
    logger.info("Inserting work references...")
    referenced_works = []
    
    for work_id, work in works_data.items():
        # Ensure work is a dictionary
        if not isinstance(work, dict):
            logger.warning(f"Skipping work {work_id}: not a dictionary")
            continue
            
        # Extract work ID safely
        try:
            if "id" in work and isinstance(work["id"], str):
                clean_work_id = work["id"].split("/")[-1]
            else:
                clean_work_id = str(work_id).split("/")[-1]
        except Exception as e:
            logger.warning(f"Error processing work ID {work_id}: {e}")
            continue
            
        # Process referenced works
        referenced_works_list = work.get("referenced_works", [])
        if not isinstance(referenced_works_list, list):
            continue
            
        for ref_work in referenced_works_list:
            try:
                if isinstance(ref_work, str) and ref_work.strip():
                    ref_id = ref_work.split("/")[-1]
                    if ref_id.strip():  # Ensure ref_id is not empty
                        referenced_works.append({"source": clean_work_id, "target": ref_id})
            except Exception as e:
                logger.warning(f"Error processing reference {ref_work}: {e}")
                continue

    if not referenced_works:
        logger.info("No valid work references found")
        return

    ref_batches = [
        referenced_works[i : i + 500] for i in range(0, len(referenced_works), 500)
    ]
    
    for batch_num, batch in enumerate(tqdm(ref_batches, desc="Inserting references"), 1):
        try:
            query = """
            UNWIND $refs AS ref
            MATCH (source:Work {id: ref.source})
            MATCH (target:Work {id: ref.target})
            MERGE (source)-[r:REFERENCES]->(target)
            """
            neo4j_conn.execute_query(query, {"refs": batch}, return_data=False)
        except Exception as e:
            logger.error(f"Error inserting reference batch {batch_num}: {e}")
            continue


def insert_author_affiliations(
    neo4j_conn: Neo4jConnection, consolidated_authors: Dict
) -> None:
    """Insert author affiliations into Neo4j with validation.

    Args:
        neo4j_conn: Neo4j database connection
        consolidated_authors: Dictionary of consolidated authors
    """
    if not consolidated_authors:
        logger.info("No authors data for affiliations")
        return
        
    logger.info("Inserting author affiliations...")
    affiliation_data = []
    
    for author_id, data in consolidated_authors.items():
        if not isinstance(data, dict):
            continue
            
        for affil in data.get("affiliations", []):
            if not isinstance(affil, dict):
                continue
                
            try:
                affiliation_entry = {
                    "author_id": str(author_id),
                    "institution_id": str(affil.get("institution_id", "")),
                    "institution_name": str(affil.get("institution_name", "")),
                    "country_code": str(affil.get("country_code", "")),
                    "years": affil.get("years", []) if isinstance(affil.get("years"), list) else [],
                }
                
                # Only add if we have meaningful data
                if affiliation_entry["institution_id"] or affiliation_entry["institution_name"]:
                    affiliation_data.append(affiliation_entry)
                    
            except Exception as e:
                logger.warning(f"Error processing affiliation for author {author_id}: {e}")
                continue

    if not affiliation_data:
        logger.info("No valid affiliations found")
        return

    affil_batches = [
        affiliation_data[i : i + 500] for i in range(0, len(affiliation_data), 500)
    ]
    
    for batch_num, batch in enumerate(tqdm(affil_batches, desc="Inserting affiliations"), 1):
        try:
            query = """
            UNWIND $affiliations AS affil
            MATCH (a:Author {id: affil.author_id})
            MERGE (i:Institution {id: affil.institution_id})
            ON CREATE SET 
                i.name = affil.institution_name,
                i.country_code = affil.country_code
            MERGE (a)-[r:AFFILIATED_WITH]->(i)
            ON CREATE SET r.years = affil.years
            """
            neo4j_conn.execute_query(query, {"affiliations": batch}, return_data=False)
        except Exception as e:
            logger.error(f"Error inserting affiliation batch {batch_num}: {e}")
            continue


def insert_author_topics(
    neo4j_conn: Neo4jConnection, consolidated_authors: Dict
) -> None:
    """Insert author topics into Neo4j with validation.

    Args:
        neo4j_conn: Neo4j database connection
        consolidated_authors: Dictionary of consolidated authors
    """
    if not consolidated_authors:
        logger.info("No authors data for topics")
        return
        
    logger.info("Inserting author research topics...")
    topic_data = []
    
    for author_id, data in consolidated_authors.items():
        if not isinstance(data, dict):
            continue
            
        for topic in data.get("topics", []):
            if not isinstance(topic, dict):
                continue
                
            try:
                topic_entry = {
                    "author_id": str(author_id),
                    "topic_id": str(topic.get("id", "")),
                    "topic_name": str(topic.get("name", "")),
                }
                
                # Only add if we have meaningful data
                if topic_entry["topic_id"] or topic_entry["topic_name"]:
                    topic_data.append(topic_entry)
                    
            except Exception as e:
                logger.warning(f"Error processing topic for author {author_id}: {e}")
                continue

    if not topic_data:
        logger.info("No valid topics found")
        return

    topic_batches = [topic_data[i : i + 500] for i in range(0, len(topic_data), 500)]
    
    for batch_num, batch in enumerate(tqdm(topic_batches, desc="Inserting topics"), 1):
        try:
            query = """
            UNWIND $topics AS topic
            MATCH (a:Author {id: topic.author_id})
            MERGE (t:Topic {id: topic.topic_id})
            ON CREATE SET t.name = topic.topic_name
            MERGE (a)-[r:RESEARCHES]->(t)
            """
            neo4j_conn.execute_query(query, {"topics": batch}, return_data=False)
        except Exception as e:
            logger.error(f"Error inserting topic batch {batch_num}: {e}")
            continue


def print_database_stats(
    neo4j_conn: Neo4jConnection, G: nx.Graph, relationships: List
) -> None:
    """Print database statistics with error handling.

    Args:
        neo4j_conn: Neo4j database connection
        G: NetworkX graph for retrieving node data
        relationships: List of relationships for analysis
    """
    try:
        # Get counts with error handling
        author_count = neo4j_conn.execute_query("MATCH (a:Author) RETURN count(a) as count")[0]["count"]
        work_count = neo4j_conn.execute_query("MATCH (w:Work) RETURN count(w) as count")[0]["count"]
        concept_count = neo4j_conn.execute_query("MATCH (c:Concept) RETURN count(c) as count")[0]["count"]
        rel_count = neo4j_conn.execute_query("MATCH ()-[r:AUTHORED]->() RETURN count(r) as count")[0]["count"]
        ref_count = neo4j_conn.execute_query("MATCH ()-[r:REFERENCES]->() RETURN count(r) as count")[0]["count"]

        logger.info("\n🎉 Neo4j database updated successfully:")
        logger.info(f"- Authors: {author_count:,}")
        logger.info(f"- Articles: {work_count:,}")
        logger.info(f"- Concepts: {concept_count:,}")
        logger.info(f"- AUTHORED relationships: {rel_count:,}")
        logger.info(f"- REFERENCES relationships: {ref_count:,}")

        logger.info("\n📊 DETAILED RELATIONSHIP REPORT")
        relation_log = defaultdict(list)
        for rel in relationships:
            if isinstance(rel, dict) and "author_id" in rel and "work_id" in rel:
                relation_log[rel["author_id"]].append(rel["work_id"])

        top_authors = sorted(relation_log.items(), key=lambda x: len(x[1]), reverse=True)[:10]

        for author_id, works in top_authors:
            try:
                if author_id in G.nodes:
                    author_name = G.nodes[author_id].get("display_name", "Unknown")
                    logger.info(f"\nAuthor: {author_name} (ID: {author_id})")
                    logger.info(f"Total articles: {len(works)}")
                    logger.info(f"h-index: {G.nodes[author_id].get('h_index', 0)}")

                    for work_id in works[:3]:
                        if work_id in G.nodes:
                            work_title = G.nodes[work_id].get("title", "No title")
                            logger.info(f"   - {work_title[:60]}... ({work_id})")
                    if len(works) > 3:
                        logger.info(f"   + {len(works)-3} more articles...")
            except Exception as e:
                logger.warning(f"Error processing author stats for {author_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error generating database statistics: {e}")
