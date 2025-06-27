import networkx as nx
import streamlit as st
import pandas as pd
import json
import re
import unicodedata

def normalize_name(name):
    """Normaliza un nombre eliminando espacios extra, caracteres especiales y unificando formato"""
    if not name or pd.isna(name):
        return None
    
    name = str(name)
    
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[^\w\s\-\.]', '', name)  
    name = name.strip().lower() 
    
    name = re.sub(r'\bdr\b\.?', 'dr', name)  
    name = re.sub(r'\bphd\b\.?', 'phd', name)  
    name = name.replace('-'," ")
    return name if name else None


print("Cargando datos...")
df = pd.read_json("data/openalex_data.json")
df2 = pd.read_json("data/openalex_authors_complete.json")
df2 = df2.T

G = nx.Graph()

for i, row in df.iterrows():
        
    original_article_name = row.get('display_name') or row.get('title') or row.get("id")
   
    article_data = row.to_dict()
    article_data['node_type'] = 'article'
    G.add_node(original_article_name, **article_data)
    for authors in row['authorships']:
        author_ = authors.get("author", {}).get("id", "")
        if not author_:
            continue
        __author =  author_.split("/")[-1]
        try:
            author_row = df2.loc[__author].to_dict()
            author_id = author_row['id'].split('/')[-1]
            author_row['node_type']='author'   
            G.add_node(author_id,**author_row)
            if not G.has_edge(original_article_name,author_id):
                G.add_edge(original_article_name,author_id)
        except:
            pass
        


for n, d in G.nodes(data=True):
    for k, v in list(d.items()):
        if v is None:
            d[k] = ""
        elif isinstance(v, (dict, list)):
            d[k] = json.dumps(v)

for u, v, d in G.edges(data=True):
    for k, v2 in list(d.items()):
        if v2 is None:
            d[k] = ""
        elif isinstance(v2, (dict, list)):
            d[k] = json.dumps(v2)


nx.write_graphml(G, "data/subgrafo_con_articulos.graphml")

print('finalizado')