import json
import logging
import networkx as nx
from tqdm import tqdm
from typing import Dict, List, Tuple, Set
from collections import defaultdict

from db.db_connection import Neo4jConnection

logger = logging.getLogger(__name__)


def save_to_neo4j(G: nx.Graph, consolidated_authors: Dict, works_data: Dict) -> None:
    """Save the graph data to Neo4j database.

    Args:
        G: NetworkX graph containing authors and works
        consolidated_authors: Dictionary of consolidated authors
        works_data: Dictionary of work data
    """
    logger.info("\nInitiating Neo4j database save...")

    try:
        neo4j_conn = Neo4jConnection()
        logger.info("✅ Neo4j connection established")

        logger.info("Cleaning existing database...")
        neo4j_conn.execute_query("MATCH (n) DETACH DELETE n", return_data=False)

        setup_database_constraints(neo4j_conn)

        author_nodes, work_nodes, concept_nodes, relationships = prepare_data(G)

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
        raise


def setup_database_constraints(neo4j_conn: Neo4jConnection) -> None:
    """Set up database constraints and indexes.

    Args:
        neo4j_conn: Neo4j database connection
    """
    logger.info("Dropping existing constraints and indexes...")
    try:

        constraints = neo4j_conn.execute_query("SHOW CONSTRAINTS")
        for constraint in constraints:
            constraint_name = constraint.get("name")
            if constraint_name:
                neo4j_conn.execute_query(
                    f"DROP CONSTRAINT {constraint_name} IF EXISTS", return_data=False
                )

        indexes = neo4j_conn.execute_query("SHOW INDEXES")
        for index in indexes:
            index_name = index.get("name")
            if index_name and not index_name.startswith("constraint_"):
                neo4j_conn.execute_query(
                    f"DROP INDEX {index_name} IF EXISTS", return_data=False
                )

        logger.info("✅ Existing constraints and indexes dropped successfully")
    except Exception as e:
        logger.error(f"❌ Error dropping constraints and indexes: {e}")

    logger.info("Creating new constraints and indexes...")
    try:
        neo4j_conn.execute_query(
            "CREATE CONSTRAINT constraint_author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
            return_data=False,
        )
        neo4j_conn.execute_query(
            "CREATE CONSTRAINT constraint_work_id IF NOT EXISTS FOR (w:Work) REQUIRE w.id IS UNIQUE",
            return_data=False,
        )

        neo4j_conn.execute_query(
            "CREATE CONSTRAINT constraint_concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
            return_data=False,
        )
        neo4j_conn.execute_query(
            "CREATE INDEX index_country IF NOT EXISTS FOR (i:Institution) ON (i.country_code)",
            return_data=False,
        )
        logger.info("✅ New constraints and indexes created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating constraints and indexes: {e}")


def prepare_data(G: nx.Graph) -> Tuple[List, List, List, List]:
    """Prepare data from the graph for insertion into Neo4j.

    Args:
        G: NetworkX graph containing authors and works

    Returns:
        Tuple containing author nodes, work nodes, concept nodes, and relationships
    """
    author_nodes = []
    work_nodes = []
    concept_nodes = []
    concept_ids_seen = set()
    relationships = []

    logger.info("Preparing authors for insertion...")
    for node_id, node_data in G.nodes(data=True):
        if node_data.get("type_node") == "Author":
            author_nodes.append((node_id, node_data))

            for concept in node_data.get("x_concepts", []):
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
        if node_data.get("type_node") == "Work":

            biblio_data = node_data.get("biblio", {})
            clean_biblio = {}

            if isinstance(biblio_data, dict):
                for key, value in biblio_data.items():
                    if isinstance(value, dict):
                        clean_biblio[key + "_json"] = json.dumps(value)
                    elif isinstance(value, (str, int, float, bool)) or value is None:
                        clean_biblio[key] = value
                    elif isinstance(value, list):
                        clean_biblio[key + "_json"] = json.dumps(value)

            node_data_copy = dict(node_data)
            node_data_copy["biblio"] = clean_biblio

            work_nodes.append((node_id, node_data_copy))

            for concept in node_data.get("concepts", []):
                concept_id = concept["id"]
                if concept_id not in concept_ids_seen:
                    concept_ids_seen.add(concept_id)
                    concept_dict = {
                        "id": concept["id"],
                        "display_name": concept.get("display_name", ""),
                        "level": concept.get("level", 0),
                        "score": concept.get("score", 0.0),
                    }
                    concept_nodes.append(
                        (concept_id, concept_dict)
                    )  # Append to list instead of adding to set

    logger.info("Preparing relationships for insertion...")
    relation_log = defaultdict(list)
    for author_id, work_id, edge_data in G.edges(data=True):
        if edge_data.get("type") == "authored":
            relationships.append({"author_id": author_id, "work_id": work_id})
            relation_log[author_id].append(work_id)

    return author_nodes, work_nodes, concept_nodes, relationships


def insert_concepts(neo4j_conn: Neo4jConnection, concept_nodes: List) -> None:
    """Insert concept nodes into Neo4j.

    Args:
        neo4j_conn: Neo4j database connection
        concept_nodes: List of concept nodes to insert
    """
    logger.info(f"Inserting {len(concept_nodes)} concepts...")
    concept_batches = [
        concept_nodes[i : i + 500] for i in range(0, len(concept_nodes), 500)
    ]

    for batch in tqdm(concept_batches, desc="Inserting concepts"):
        query = """
        UNWIND $concepts AS concept
        MERGE (c:Concept {id: concept.id})
        ON CREATE SET 
            c.display_name = concept.display_name,
            c.level = concept.level,
            c.score = concept.score
        """
        params = {"concepts": [c[1] for c in batch]}
        neo4j_conn.execute_query(query, params, return_data=False)


def insert_authors(neo4j_conn: Neo4jConnection, author_nodes: List) -> None:
    """Insert author nodes into Neo4j.

    Args:
        neo4j_conn: Neo4j database connection
        author_nodes: List of author nodes to insert
    """
    batch_size = 100
    logger.info(f"Inserting authors (batch size: {batch_size})...")
    author_batches = [
        author_nodes[i : i + batch_size]
        for i in range(0, len(author_nodes), batch_size)
    ]

    for batch in tqdm(author_batches, desc="Inserting authors"):
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
        params = {
            "authors": [
                {
                    "id": author_id,
                    "data": {
                        "display_name": data.get("display_name", ""),
                        "works_count": data.get("works_count", 0),
                        "cited_by_count": data.get("cited_by_count", 0),
                        "display_name_alternatives": data.get(
                            "display_name_alternatives", []
                        ),
                        "alias_ids": data.get("alias_ids", []),
                        "orcid": data.get("orcid", ""),
                        "h_index": data.get("h_index", 0),
                        "last_known_institutions": data.get(
                            "last_known_institutions", []
                        ),
                        "x_concepts": [
                            {"id": c["id"], "score": c.get("score", 0.0)}
                            for c in data.get("x_concepts", [])
                        ],
                    },
                }
                for author_id, data in batch
            ]
        }
        neo4j_conn.execute_query(query, params, return_data=False)


def insert_works(neo4j_conn: Neo4jConnection, work_nodes: List) -> None:
    """Insert work nodes into Neo4j.

    Args:
        neo4j_conn: Neo4j database connection
        work_nodes: List of work nodes to insert
    """
    batch_size = 100
    logger.info(f"Inserting articles (batch size: {batch_size})...")
    work_batches = [
        work_nodes[i : i + batch_size] for i in range(0, len(work_nodes), batch_size)
    ]

    for batch in tqdm(work_batches, desc="Inserting articles"):
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

        works_params = []
        for work_id, data in batch:
            work_param = {
                "id": work_id,
                "title": data.get("title", ""),
                "publication_year": data.get("publication_year", None),
                "publication_date": data.get("publication_date", ""),
                "cited_by_count": data.get("cited_by_count", 0),
                "is_oa": data.get("is_oa", False),
                "referenced_works_count": data.get("referenced_works_count", 0),
                "concepts": [
                    {"id": c["id"], "score": c.get("score", 0.0)}
                    for c in data.get("concepts", [])
                ],
            }

            for key, value in data.get("biblio", {}).items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    work_param["biblio_" + key] = value

            works_params.append(work_param)

        params = {"works": works_params}
        neo4j_conn.execute_query(query, params, return_data=False)


def insert_author_work_relationships(
    neo4j_conn: Neo4jConnection, relationships: List[Dict], G: nx.Graph
) -> None:
    """Insert author-work relationships into Neo4j.

    Args:
        neo4j_conn: Neo4j database connection
        relationships: List of author-work relationships to insert
        G: NetworkX graph for retrieving node data
    """
    batch_size = 100
    logger.info(f"Inserting relationships (batch size: {batch_size})...")
    rel_batches = [
        relationships[i : i + batch_size]
        for i in range(0, len(relationships), batch_size)
    ]

    for batch_num, batch in enumerate(
        tqdm(rel_batches, desc="Inserting relationships"), 1
    ):
        if batch_num == 1:
            logger.info("\n📝 Relationship examples from first batch:")
            for rel in batch[:3]:
                author_id = rel["author_id"]
                work_id = rel["work_id"]
                author_name = G.nodes[author_id].get("display_name", "Unknown")
                work_title = G.nodes[work_id].get("title", "No title")[:50] + "..."
                logger.info(f"   - {author_name} (ID: {author_id}) -> {work_title}")
                logger.info("    - ..................................................")

        query = """
        UNWIND $relationships AS rel
        MATCH (a:Author {id: rel.author_id})
        MATCH (w:Work {id: rel.work_id})
        MERGE (a)-[r:AUTHORED]->(w)
        """
        neo4j_conn.execute_query(query, {"relationships": batch}, return_data=False)


def insert_work_references(neo4j_conn: Neo4jConnection, works_data: Dict) -> None:
    """Insert work references into Neo4j.

    Args:
        neo4j_conn: Neo4j database connection
        works_data: Dictionary of work data
    """
    logger.info("Inserting work references...")
    referenced_works = []
    for work in works_data:
        work_id = work.get("id", "").split("/")[-1]
        for ref_work in work.get("referenced_works", []):
            ref_id = ref_work.split("/")[-1]
            referenced_works.append({"source": work_id, "target": ref_id})

    ref_batches = [
        referenced_works[i : i + 500] for i in range(0, len(referenced_works), 500)
    ]
    for batch in tqdm(ref_batches, desc="Inserting references"):
        query = """
        UNWIND $refs AS ref
        MATCH (source:Work {id: ref.source})
        MATCH (target:Work {id: ref.target})
        MERGE (source)-[r:REFERENCES]->(target)
        """
        neo4j_conn.execute_query(query, {"refs": batch}, return_data=False)


def insert_author_affiliations(
    neo4j_conn: Neo4jConnection, consolidated_authors: Dict
) -> None:
    """Insert author affiliations into Neo4j.

    Args:
        neo4j_conn: Neo4j database connection
        consolidated_authors: Dictionary of consolidated authors
    """
    logger.info("Inserting author affiliations...")
    affiliation_data = []
    for author_id, data in consolidated_authors.items():
        for affil in data.get("affiliations", []):
            affiliation_data.append(
                {
                    "author_id": author_id,
                    "institution_id": affil.get("institution_id", ""),
                    "institution_name": affil.get("institution_name", ""),
                    "country_code": affil.get("country_code", ""),
                    "years": affil.get("years", []),
                }
            )

    affil_batches = [
        affiliation_data[i : i + 500] for i in range(0, len(affiliation_data), 500)
    ]
    for batch in tqdm(affil_batches, desc="Inserting affiliations"):
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


def insert_author_topics(
    neo4j_conn: Neo4jConnection, consolidated_authors: Dict
) -> None:
    """Insert author topics into Neo4j.

    Args:
        neo4j_conn: Neo4j database connection
        consolidated_authors: Dictionary of consolidated authors
    """
    logger.info("Inserting author research topics...")
    topic_data = []
    for author_id, data in consolidated_authors.items():
        for topic in data.get("topics", []):
            topic_data.append(
                {
                    "author_id": author_id,
                    "topic_id": topic.get("id", ""),
                    "topic_name": topic.get("name", ""),
                }
            )

    topic_batches = [topic_data[i : i + 500] for i in range(0, len(topic_data), 500)]
    for batch in tqdm(topic_batches, desc="Inserting topics"):
        query = """
        UNWIND $topics AS topic
        MATCH (a:Author {id: topic.author_id})
        MERGE (t:Topic {id: topic.topic_id})
        ON CREATE SET t.name = topic.topic_name
        MERGE (a)-[r:RESEARCHES]->(t)
        """
        neo4j_conn.execute_query(query, {"topics": batch}, return_data=False)


def print_database_stats(
    neo4j_conn: Neo4jConnection, G: nx.Graph, relationships: List
) -> None:
    """Print statistics about the Neo4j database.

    Args:
        neo4j_conn: Neo4j database connection
        G: NetworkX graph
        relationships: List of relationships
    """
    author_count = neo4j_conn.execute_query(
        "MATCH (a:Author) RETURN count(a) AS count"
    )[0]["count"]
    work_count = neo4j_conn.execute_query("MATCH (w:Work) RETURN count(w) AS count")[0][
        "count"
    ]
    rel_count = neo4j_conn.execute_query(
        "MATCH ()-[r:AUTHORED]->() RETURN count(r) AS count"
    )[0]["count"]
    concept_count = neo4j_conn.execute_query(
        "MATCH (c:Concept) RETURN count(c) AS count"
    )[0]["count"]
    ref_count = neo4j_conn.execute_query(
        "MATCH ()-[r:REFERENCES]->() RETURN count(r) AS count"
    )[0]["count"]

    logger.info("\n🎉 Neo4j database updated successfully:")
    logger.info(f"- Authors: {author_count:,}")
    logger.info(f"- Articles: {work_count:,}")
    logger.info(f"- Concepts: {concept_count:,}")
    logger.info(f"- AUTHORED relationships: {rel_count:,}")
    logger.info(f"- REFERENCES relationships: {ref_count:,}")

    logger.info("\n📊 DETAILED RELATIONSHIP REPORT")
    relation_log = defaultdict(list)
    for rel in relationships:
        relation_log[rel["author_id"]].append(rel["work_id"])

    top_authors = sorted(relation_log.items(), key=lambda x: len(x[1]), reverse=True)[
        :10
    ]

    for author_id, works in top_authors:
        author_name = G.nodes[author_id].get("display_name", "Unknown")
        logger.info(f"\nAuthor: {author_name} (ID: {author_id})")
        logger.info(f"Total articles: {len(works)}")
        logger.info(f"h-index: {G.nodes[author_id].get('h_index', 0)}")

        for work_id in works[:3]:
            work_title = G.nodes[work_id].get("title", "No title")
            logger.info(f"   - {work_title[:60]}... ({work_id})")
        if len(works) > 3:
            logger.info(f"   + {len(works)-3} more articles...")
