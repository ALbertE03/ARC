import networkx as nx 
import json
from collections import defaultdict

def create_article_to_article_graph(author_article_graph_path="data/subgrafo_con_articulos.graphml"):
    """
    Crea un grafo artículo-artículo donde los artículos están conectados 
    si tienen autores en común. El peso de la arista representa el número 
    de autores en común.
    
    Args:
        author_article_graph_path (str): Ruta al grafo autor-artículo base
    
    Returns:
        networkx.Graph: Grafo artículo-artículo
    """
    print("Cargando grafo autor-artículo...")
    
    try:
        G_base = nx.read_graphml(author_article_graph_path)
        print(f"Grafo cargado con {G_base.number_of_nodes()} nodos y {G_base.number_of_edges()} aristas")
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {author_article_graph_path}")
        return None
    
    G_articles = nx.Graph()
    
    articles = []
    authors = []
    
    for node, data in G_base.nodes(data=True):
        node_type = data.get('node_type', '')
        if node_type == 'article':
            articles.append(node)
        elif node_type == 'author':
            authors.append(node)
    
    print(f"Encontrados {len(articles)} artículos y {len(authors)} autores")
    
    for article in articles:
        article_data = G_base.nodes[article].copy()
        G_articles.add_node(article, **article_data)
    

    author_to_articles = defaultdict(list)
    for article in articles:
        article_authors = []
        for neighbor in G_base.neighbors(article):
            if G_base.nodes[neighbor].get('node_type') == 'author':
                author_to_articles[neighbor].append(article)
                article_authors.append(neighbor)
    
    print("Creando conexiones entre artículos...")
    
    connections_count = 0
    for i, article1 in enumerate(articles):
        if i % 100 == 0:
            print(f"Procesando artículo {i+1}/{len(articles)}")

        authors1 = set()
        for neighbor in G_base.neighbors(article1):
            if G_base.nodes[neighbor].get('node_type') == 'author':
                authors1.add(neighbor)

        for j in range(i+1, len(articles)):
            article2 = articles[j]

            authors2 = set()
            for neighbor in G_base.neighbors(article2):
                if G_base.nodes[neighbor].get('node_type') == 'author':
                    authors2.add(neighbor)
            
            common_authors = authors1.intersection(authors2)
            
            if common_authors:
                weight = len(common_authors)
                if not G_articles.has_edge(article1,article2):
                    G_articles.add_edge(article1, article2, 
                                  weight=weight, 
                                  common_authors=list(common_authors),
                                  common_authors_count=weight)
                    connections_count += 1
    
    print(f"Grafo artículo-artículo creado con {G_articles.number_of_nodes()} nodos y {G_articles.number_of_edges()} aristas")
    
    return G_articles

def save_article_graph(G_articles, output_path="data/grafo_articulo_articulo.graphml"):
    """
    Guarda el grafo artículo-artículo en formato GraphML
    
    Args:
        G_articles (networkx.Graph): Grafo a guardar
        output_path (str): Ruta donde guardar el archivo
    """
    if G_articles is None:
        print("Error: No se puede guardar un grafo vacío")
        return
    
    print(f"Guardando grafo en {output_path}...")
    
    for n, d in G_articles.nodes(data=True):
        for k, v in list(d.items()):
            if v is None:
                d[k] = ""
            elif isinstance(v, (dict, list)):
                d[k] = json.dumps(v)
    
    for u, v, d in G_articles.edges(data=True):
        for k, v2 in list(d.items()):
            if v2 is None:
                d[k] = ""
            elif isinstance(v2, (dict, list)):
                d[k] = json.dumps(v2)
    
    try:
        nx.write_graphml(G_articles, output_path)
        print(f"Grafo guardado exitosamente en {output_path}")
    except Exception as e:
        print(f"Error al guardar el grafo: {e}")


if __name__ == "__main__":
    G_articles = create_article_to_article_graph()
    
    if G_articles is not None:

        save_article_graph(G_articles)
        
        print("\n¡Proceso completado exitosamente!")
    else:
        print("Error: No se pudo crear el grafo artículo-artículo")
