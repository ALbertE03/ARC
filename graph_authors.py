import networkx as nx
from pyvis.network import Network
import os
from itertools import combinations


def create_author_author_graph(article_author_graph_path, output_path):
    """
    Create an author-author graph from an article-author graph.
    Authors are connected if they co-authored a paper together.

    Args:
        article_author_graph_path: Path to the article-author graphml file
        output_path: Path to save the author-author graphml file
    """
    G = nx.read_graphml(article_author_graph_path)

    author_graph = nx.Graph()

    article_nodes = [
        n for n, attrs in G.nodes(data=True) if attrs.get("type") == "article"
    ]
    for article in article_nodes:
        authors = list(G.predecessors(article))

        for a1, a2 in combinations(authors, 2):
            if not author_graph.has_edge(a1, a2):
                author_graph.add_edge(a1, a2, weight=1)
            else:
                author_graph[a1][a2]["weight"] += 1

    nx.write_graphml(author_graph, output_path)

    return author_graph


def visualize_graph(G, output_path="visu/graph_author_author.html"):
    """
    Visualize the graph using PyVis for an interactive HTML output

    Args:
        G: NetworkX graph object
        title: Title of the graph
        output_path: Path to save the HTML output file
    """

    net = Network(
        notebook=True,
        height="100%",
        width="100%",
        bgcolor="#222222",
        font_color="white",
    )
    net.from_nx(G)
    net.set_options(
        """
        {
            "nodes": {
                "font": {
                    "size": 12,
                    "color": "white"
                }
            },
            "edges": {
                "color": {
                    "inherit": true
                },
                "smooth": false
            },
            "physics": {
                "enabled": true,
                "barnesHut": {
                    "gravitationalConstant": -10000,
                    "centralGravity": 0.5,
                    "springLength": 250,
                    "springConstant": 0.04,
                    "damping": 0.09,
                    "avoidOverlap": 0.1
                },
                "minVelocity": 0.75
            }
        }
        """
    )

    net.show("visu/graph_author_article.html")

    print(f"Interactive graph saved to {output_path}")


if __name__ == "__main__":
    article_author_graph_path = "graph/graph.graphml"
    output_path = "graph/author_author_graph.graphml"

    if not os.path.exists(output_path):
        author_graph = create_author_author_graph(
            article_author_graph_path, output_path
        )
    author_graph = nx.read_graphml("graph/author_author_graph.graphml")
    print(
        f"Created author-author graph with {author_graph.number_of_nodes()} nodes and {author_graph.number_of_edges()} edges"
    )
    print(f"Graph saved to {output_path}")

    visualize_graph(author_graph)
