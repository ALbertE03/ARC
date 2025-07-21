from itertools import combinations
import networkx as nx
import os
def load_keyword_graph(path):
    """Carga el grafo de palabras clave """
    if not os.path.exists(path):
        return None
    try:
        g = nx.read_graphml(path)
        for node, data in g.nodes(data=True):
            if 'frequency' in data:
                data['frequency'] = int(data['frequency'])
        for u, v, data in g.edges(data=True):
            if 'weight' in data:
                data['weight'] = int(data['weight'])
        return g
    except Exception as e:
      
        return None

def project_to_author_collaboration_graph(_mixed_graph):
    """
    Proyecta un grafo mixto (autor-keyword) a un grafo de colaboración autor-autor.
    Una arista entre dos autores significa que comparten al menos una palabra clave.
    El peso de la arista cuenta cuántas palabras clave comparten.
    """
    G_authors = nx.Graph()
    author_nodes = {n for n, d in _mixed_graph.nodes(data=True) if d.get('type') == 'author'}
    keyword_nodes = {n for n, d in _mixed_graph.nodes(data=True) if d.get('type') == 'keyword'}


    for author in author_nodes:
        if not G_authors.has_node(author):
            G_authors.add_node(author, **_mixed_graph.nodes[author])

    for keyword in keyword_nodes:
        authors_using_keyword = [n for n in _mixed_graph.neighbors(keyword) if n in author_nodes]
        
        for author1, author2 in combinations(authors_using_keyword, 2):
            if G_authors.has_edge(author1, author2):
                G_authors[author1][author2]['weight'] += 1
            else:
                G_authors.add_edge(author1, author2, weight=1)
                
    return G_authors
def save_graph(graph, filename):
        """Guarda el grafo en formato GraphML"""

        graph_copy = graph.copy()
        
        for node_id, node_data in graph_copy.nodes(data=True):
            if 'all_names' in node_data and isinstance(node_data['all_names'], list):
                node_data['all_names'] = '|'.join(str(name) for name in node_data['all_names'])
            if 'papers' in node_data and isinstance(node_data['papers'], list):
                node_data['papers'] = '|'.join(str(paper) for paper in node_data['papers'])
        
        for u, v, edge_data in graph_copy.edges(data=True):
            if 'papers' in edge_data and isinstance(edge_data['papers'], list):
                flattened_papers = []
                for paper in edge_data['papers']:
                    if isinstance(paper, list):
                        flattened_papers.extend(str(p) for p in paper)
                    else:
                        flattened_papers.append(str(paper))
                edge_data['papers'] = '|'.join(flattened_papers)
        
        nx.write_graphml(graph_copy, filename)
        print(f"Grafo guardado en {filename}")
        
PATH_TO_KEYWORD_GRAPH = './graph/keywords_graph.graphml'
keyword_graph = load_keyword_graph(PATH_TO_KEYWORD_GRAPH)
author_collab_graph = project_to_author_collaboration_graph(keyword_graph)
save_graph(author_collab_graph, './graph/author_collaboration_graph_keywords.graphml')
