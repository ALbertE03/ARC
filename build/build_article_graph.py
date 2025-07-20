import networkx as nx
import json 
import os
def load_author_graph(path):
    """Carga el grafo de colaboración de autores y lo procesa."""
    if not os.path.exists(path):
        return None
    try:
        g = nx.read_graphml(path)
        for node, data in g.nodes(data=True):
            if 'all_names' in data and isinstance(data['all_names'], str):
                data['all_names'] = data['all_names'].split('|')
            if 'papers' in data and isinstance(data['papers'], str):
                data['papers'] = data['papers'].split('|')
            if 'paper_count' in data:
                data['paper_count'] = int(data['paper_count'])
        for u, v, data in g.edges(data=True):
            if 'weight' in data:
                data['weight'] = int(data['weight'])
        return g
    except Exception as e:
        print(f"Error al procesar el grafo de autores: {e}")
        return None
with open("./data/extract_result.json",'r') as f:
        data = json.load(f)
grap = load_author_graph("./graph/author_collaboration_graph.graphml")
print('cargado')

g =nx.Graph()
for node,d in grap.nodes(data=True):
    if not g.has_node(d['name'],type='author'):
          g.add_node(d['name'])
    for i in d['papers']:
        try:
            title = data[i]['title'][0]
            if not g.has_node(title): 
                g.add_node(title,type = 'papers')
            if not g.has_edge(title,d['name']):
                g.add_edge(title,d['name'])
        except:
            pass

nx.write_graphml(g,'./graph/articles_graph.graphml')
