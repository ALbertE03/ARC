import networkx as nx
import json
from tqdm import tqdm
from pyvis.network import Network

G = nx.Graph()


with open("data/openalex_data.json", "r") as f:
    data = json.load(f)
i = 0
for work in tqdm(data, desc="Procesando publicaciones"):

    G.add_node(
        work["id"].split("/")[-1] if work["id"].split("/")[-1] else i,
        label=work["title"] if work["title"] else "unknown",
        type="work",
        year=work["publication_year"] if work["publication_year"] else "unknown",
    )

    for authorship in work["authorships"]:
        author_id = authorship["author"]["id"]
        author_name = authorship["author"]["display_name"]
        if not author_id or not author_name:
            continue
        if not G.has_node(author_id):
            G.add_node(
                author_id,
                label=author_name if author_name else "",
                type="author",
                orcid=(
                    authorship["author"]["orcid"].split("/")[-1]
                    if authorship["author"]["orcid"]
                    else "unknown"
                ),
            )

        G.add_edge(
            author_id, work["id"].split("/")[-1] if work["id"].split("/")[-1] else i
        )
    i += 1


print("nodos:", G.number_of_nodes())
print("aristas:", G.number_of_edges())
net = Network(height="800px", notebook=True, cdn_resources="in_line")
net.from_nx(G)
net.show("grafo.html")
print("Visualización guardada en grafo.html")
