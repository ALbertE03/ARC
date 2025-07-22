import networkx as nx 
import json


with open("./data/extract_result.json",'r') as f:
    data = json.load(f)


G = nx.Graph()
for pdf_key,d in data.items():
    keywords = d.get("keywords",[])
    title = d.get('title')[0] if d.get('title') else pdf_key
    if not G.has_node(title):
        G.add_node(title,type='papers')

    for j in keywords:
        if  not G.has_node(j):
            G.add_node(j,type = 'keywords')
        
        if not G.has_edge(j,title):
            G.add_edge(j,title,weight=1)
        else:
            G[j][title]['weight'] += 1


nx.write_graphml(G, "./graph/article_keywords_graph.graphml")