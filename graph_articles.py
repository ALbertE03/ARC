import networkx as nx
from pyvis.network import Network
import os


def create_article_article_graph(article_author_graph_path, output_path):
    """
    Create an article-article graph where articles are connected if they share authors.
    """
    G = nx.read_graphml(article_author_graph_path)
    article_graph = nx.Graph()

    article_nodes = [
        n for n, attrs in G.nodes(data=True) if attrs.get("type") == "article"
    ]
    for i in article_nodes:
        article_graph.add_node(i)

    aricle_authors = {}
    for article in article_nodes:
        aricle_authors[article] = list(G.neighbors(article))

    for i in aricle_authors:
        for j in aricle_authors:
            if i >= j:
                continue

            common_authors = set(aricle_authors[i]).intersection(set(aricle_authors[j]))
            if common_authors:
                article_graph.add_edge(i, j, weight=len(common_authors))

    nx.write_graphml(article_graph, output_path)
    return article_graph


def visualize_graph(G, output_path="graph_visualization.html"):
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
            "font": {"size": 12, "color": "white"},
            "color": {
                "background": "#4287f5",
                "border": "#2a56c6",
                "highlight": {"background": "#5a9df5", "border": "#2a56c6"},
                "hover": {"background": "#5a9df5", "border": "#2a56c6"}
            }
        },
        "edges": {
            "color": {"inherit": false, "color": "#a0a0a0"},
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
    net.show(output_path)
    print(f"Visualization saved to {output_path}")


if __name__ == "__main__":
    article_author_graph_path = "graph/graph.graphml"
    article_article_output = "graph/article_article_graph.graphml"

    if not os.path.exists(article_article_output):
        article_graph = create_article_article_graph(
            article_author_graph_path, article_article_output
        )
        print(
            f"Article-article graph created with {article_graph.number_of_nodes()} articles and {article_graph.number_of_edges()} shared-author connections"
        )
    visualize_graph(
        nx.read_graphml(article_article_output), "visu/article_article.html"
    )
