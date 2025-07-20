import os 
import streamlit as st
import networkx as nx
import pandas as pd

@st.cache_data
def load_article_grap(path):
    return nx.read_graphml(path)

@st.cache_resource
def load_author_graph(path):
    """Carga el grafo de colaboración de autores"""
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
        st.error(f"Error al procesar el grafo de autores: {e}")
        return None

@st.cache_resource
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
        st.error(f"Error al procesar el grafo de palabras clave: {e}")
        return None

def save_graph_state(author_graph, keyword_graph):
    """Guarda los grafos en el estado de la sesión."""
    if 'author_graph' not in st.session_state:
        st.session_state['author_graph'] = author_graph
    if 'keyword_graph' not in st.session_state:
        st.session_state['keyword_graph'] = keyword_graph
    return True

def _centrality(g):
      return {
            "betweenness_centrality":nx.betweenness_centrality(g),
            "closeness_centrality":nx.closeness_centrality(g),
            "eigenvector_centrality":nx.eigenvector_centrality(g),
      }
@st.cache_data
def calculate_author_metrics(_author_graph):
    """Calcula y devuelve un diccionario con todas las métricas de autores."""
    metrics = {}
        
    prolific = sorted(_author_graph.nodes(data=True), key=lambda x: x[1].get('paper_count', 0), reverse=True)
    metrics['prolific_authors'] = pd.DataFrame(
        [{'Autor': data['name'], 'Artículos': data.get('paper_count', 0)} for _, data in prolific[:20]]
    )

    degree = sorted(_author_graph.degree(), key=lambda x: x[1], reverse=True)
    metrics['most_collaborative'] = pd.DataFrame(
        [{'Autor': _author_graph.nodes[node_id]['name'], 'Nº Colaboradores': degree_val} for node_id, degree_val in degree[:20]]
    )

    betweenness = nx.betweenness_centrality(_author_graph, weight='weight', k=min(100, _author_graph.number_of_nodes()))
    betweenness_sorted = sorted(betweenness.items(), key=lambda item: item[1], reverse=True)
    metrics['bridge_authors'] = pd.DataFrame(
        [{'Autor': _author_graph.nodes[node_id]['name'], 'Índice de Intermediación': score} for node_id, score in betweenness_sorted[:20]]
    )

    try:
        eigenvector = nx.eigenvector_centrality(_author_graph, weight='weight', max_iter=1000)
        eigenvector_sorted = sorted(eigenvector.items(), key=lambda item: item[1], reverse=True)
        metrics['influential_authors'] = pd.DataFrame(
            [{'Autor': _author_graph.nodes[node_id]['name'], 'Índice de Influencia': score} for node_id, score in eigenvector_sorted[:20]]
        )
    except nx.PowerIterationFailedConvergence:
        metrics['influential_authors'] = pd.DataFrame()

    edges = sorted(_author_graph.edges(data=True), key=lambda x: x[2].get('weight', 0), reverse=True)
    metrics['top_collaborations'] = pd.DataFrame(
        [{'Autor 1': _author_graph.nodes[u]['name'], 'Autor 2': _author_graph.nodes[v]['name'], 'Colaboraciones': data.get('weight', 0)} for u, v, data in edges[:20]]
    )

    return metrics

@st.cache_data
def calculate_keyword_metrics(_keyword_graph):
    """Calcula y devuelve un diccionario con todas las métricas de keywords."""
    metrics = {}
    keyword_nodes = {node: data for node, data in _keyword_graph.nodes(data=True) if data.get('type') == 'keyword'}
    
    freq_sorted = sorted(keyword_nodes.items(), key=lambda item: item[1].get('frequency', 0), reverse=True)
    metrics['top_keywords'] = pd.DataFrame(
        [{'Tema': node, 'Frecuencia (Artículos)': data.get('frequency', 0)} for node, data in freq_sorted[:20]]
    )

    keyword_subgraph = _keyword_graph.subgraph([node for node, data in _keyword_graph.nodes(data=True) if data.get('type') == 'keyword'])
    degree = sorted(keyword_subgraph.degree(weight='weight'), key=lambda x: x[1], reverse=True)
    metrics['central_keywords'] = pd.DataFrame(
        [{'Tema': node, 'Centralidad (Conexiones)': connections} for node, connections in degree[:20]]
    )
    
    return metrics

import json
@st.cache_data
def load_papers_data():
    try:
        with open('./data/extract_result.jsom','r')as f:
            data = json.load(f)
        return data
    except:
        return None

@st.cache_data
def calculate_advanced_author_metrics(_author_graph):
    e = {}
    for n,d in _author_graph.nodes(data=True):
        e[d['name']] =  d['papers']
    """Calcula y devuelve un diccionario con métricas avanzadas y una tabla."""
    communities = list(nx.community.louvain_communities(_author_graph, weight='weight'))
    node_to_community = {node: i for i, comm in enumerate(communities) for node in comm}
    betweenness = nx.betweenness_centrality(_author_graph, weight='weight', k=min(100, len(_author_graph)))
    eigenvector = nx.eigenvector_centrality(_author_graph, weight='weight', max_iter=1000, tol=1e-04)
    pagerank = nx.pagerank(_author_graph, weight='weight')
    clustering = nx.clustering(_author_graph, weight='weight')
    degree = _author_graph.degree()

    master_data = []
    for node_id, data in _author_graph.nodes(data=True):
        master_data.append({
            'Autor': data['name'],
            'Artículos': data.get('paper_count', 0),
            'Nº Colaboradores': degree[node_id],
            'Comunidad ID': node_to_community.get(node_id, -1),
            'Intermediación': betweenness.get(node_id, 0),
            'Influencia (Eigenvector)': eigenvector.get(node_id, 0),
            'Influencia (PageRank)': pagerank.get(node_id, 0),
            'Cohesión (Clustering)': clustering.get(node_id, 0)
        })
    
    master_df = pd.DataFrame(master_data)

    return {
        "master_table": master_df,
        "communities": communities,
        "papers": e
    }


