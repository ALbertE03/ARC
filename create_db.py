from neo4j import GraphDatabase
from tqdm import tqdm
import networkx as nx
import json
import os

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "12345678"


def build_graph():
    G = nx.Graph()
    with open("data/openalex_data.json", "r") as f:
        data = json.load(f)

    for i, work in enumerate(tqdm(data, desc="Procesando publicaciones")):
        work_id = work["id"].split("/")[-1] or f"work_{i}"
        G.add_node(
            work_id,
            label=work.get("title", "unknown"),
            type="Work",
            year=str(work.get("publication_year", "unknown")),
        )

        for authorship in work.get("authorships", []):
            author = authorship.get("author", {})
            author_id = author.get("id", "").split("/")[-1]
            if not author_id:
                continue

            clean_author_id = author_id.split("/")[-1]

            if not G.has_node(clean_author_id):
                G.add_node(
                    clean_author_id,
                    label=author.get("display_name", ""),
                    type="Author",
                    orcid=(
                        author.get("orcid", "").split("/")[-1]
                        if author.get("orcid")
                        else "unknown"
                    ),
                )

            G.add_edge(clean_author_id, work_id)
    return G


def save_to_neo4j(graph):
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    try:
        with driver.session() as session:
            session.run(
                "CREATE CONSTRAINT unique_author IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT unique_work IF NOT EXISTS FOR (w:Work) REQUIRE w.id IS UNIQUE"
            )

            nodes = list(graph.nodes(data=True))
            for node_id, attrs in tqdm(nodes, desc="Insertando nodos"):
                label = "Author" if attrs.get("type") == "Author" else "Work"
                query = f"""
                MERGE (n:{label} {{id: $id}})
                SET n += $attrs
                """
                session.run(
                    query,
                    {
                        "id": node_id,
                        "attrs": {k: v for k, v in attrs.items() if k != "type"},
                    },
                )
            edges = list(graph.edges())
            for src, tgt in tqdm(edges, desc="Insertando relaciones"):
                src_type = graph.nodes[src].get("type")
                tgt_type = graph.nodes[tgt].get("type")

                if src_type == "Author" and tgt_type == "Work":
                    query = """
                    MATCH (a:Author {id: $author_id}), (w:Work {id: $work_id})
                    MERGE (a)-[:AUTHORED]->(w)
                    """
                    session.run(query, {"author_id": src, "work_id": tgt})
                elif src_type == "Work" and tgt_type == "Author":
                    query = """
                    MATCH (a:Author {id: $author_id}), (w:Work {id: $work_id})
                    MERGE (a)-[:AUTHORED]->(w)
                    """
                    session.run(query, {"author_id": tgt, "work_id": src})

    except Exception as e:
        print(f"Error durante la inserción: {str(e)}")
        raise
    finally:
        driver.close()


if __name__ == "__main__":
    print("Construyendo grafo...")
    G = build_graph()
    print(f"Grafo construido: {len(G.nodes())} nodos, {len(G.edges())} aristas")

    print("Guardando en Neo4j...")
    save_to_neo4j(G)
    print("Proceso completado!")
