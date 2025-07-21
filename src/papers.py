import networkx as nx
import streamlit as st
import pandas as pd 
from src.utils import load_article_grap,_centrality
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from networkx.algorithms import community
from collections import defaultdict
import json
def calculate_centrality(_g):
    """Calcula un diccionario con diferentes métricas de centralidad."""
    if _g is None:
        return {}
    return {
        'degree_centrality': nx.degree_centrality(_g),
        'betweenness_centrality': nx.betweenness_centrality(_g, k=min(100, len(_g.nodes)//2)), # k para aproximar
        'pagerank': nx.pagerank(_g, weight='weight')
    }

def detect_author_communities(_g):
    """Detecta comunidades en una proyección del grafo de solo autores."""
    if _g is None:
        return {}
    
    # Crear un grafo que solo contenga autores
    author_nodes = {n for n, d in _g.nodes(data=True) if d.get('type') == 'author'}
    author_graph = nx.Graph()
    
    # Conectar autores si comparten un artículo
    for paper_node, data in _g.nodes(data=True):
        if data.get('type') == 'papers':
            authors_of_paper = [n for n in _g.neighbors(paper_node) if n in author_nodes]
            # Añadir aristas entre todos los autores del paper
            for i in range(len(authors_of_paper)):
                for j in range(i + 1, len(authors_of_paper)):
                    u, v = authors_of_paper[i], authors_of_paper[j]
                    if author_graph.has_edge(u, v):
                        author_graph[u][v]['weight'] += 1
                    else:
                        author_graph.add_edge(u, v, weight=1)

    # Detectar comunidades en el grafo de autores
    communities_list = list(community.louvain_communities(author_graph, weight='weight'))
    # Crear un mapeo de autor -> id de comunidad
    author_to_community = {author: i for i, comm in enumerate(communities_list) for author in comm}
    return author_to_community

@st.cache_data
def load_pdf():
    try:
        with open("./data/extract_result.json",'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("No se encontró el archivo extract_result.json")
        return None
@st.cache_data
def load_key_autor():
    try:
        return nx.read_graphml('./graph/author_collaboration_graph_keywords.graphml')
    except:
        st.error("ruta incorrecta")
        st.stop()


def render_papers_page(author_graph,keyword_graph):
    G_article = load_article_grap('./graph/articles_graph.graphml')
    min_grade = [G_article.degree(x) for x,d in G_article.nodes(data=True) if d and d['type']=='papers']
    paper_nodes = [n for n, d in G_article.nodes(data=True) if d.get('type') == 'papers']
    centrality_metrics = calculate_centrality(G_article)
    author_community_map = detect_author_communities(G_article)
    pdf_data = load_pdf()
    key_autor = load_key_autor()
    communities1 = list(community.louvain_communities(key_autor, weight='weight', seed=42))
    author_community_map = {author: i for i, comm in enumerate(communities1) for author in comm}

    with st.expander("Filtros"):
            col1,col2 = st.columns(2)
            with col1:
                n_art = st.slider("minima cantidad de autores",min_value=min(min_grade),max_value=max(min_grade),value=max(min_grade)//2)
            with col2:
                n = st.slider("Cantidad de articulos",min_value=1,max_value=len(min_grade),value=len(min_grade)//2)

            fig, ax = plt.subplots(figsize=(5, 3))
            P = nx.Graph()
            s= [x for x,d in G_article.nodes(data=True) if d and d['type']=='papers' and G_article.degree(x)>=n_art][:n]
            
            for n in s:
                if not P.has_node(n):
                      P.add_node(n,type='papers')
            for n in s:
                  if P.has_node(n):
                        for i in G_article.neighbors(n):
                                if not P.has_node(i):
                                
                                    P.add_node(i,type='author')
                                P.add_edge(n,i)
            
            pos = nx.spring_layout(P)
            node_colors = []
            node_sizes=[]
            node_labels = {}
            for node,d in P.nodes(data=True):
                if d['type']=='author':
                    node_colors.append(0) 
                    node_sizes.append(10) 
                else:
                    node_colors.append(1) 
                    node_sizes.append(20) 
                node_labels[node] = node 



            edge_x = []
            edge_y = []
            for edge in P.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

            node_x = []
            node_y = []
            node_text = []
            for node in P.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                node_text.append(node)  

            fig = go.Figure(
                data=[
                    go.Scatter(
                        x=edge_x, y=edge_y,
                        line=dict(width=0.5, color='#888'),
                        hoverinfo='none',
                        mode='lines'
                    ),
                    go.Scatter(
                        x=node_x, y=node_y,
                        mode='markers',
                        hoverinfo='text',
                        text=node_text,
                        marker=dict(
                            size=node_sizes,
                            color=node_colors,
                            colorscale='Bluered',  
                            colorbar=dict(
                                title='Node Type',
                                tickvals=[0, 1],
                                ticktext=['Author', 'Article']
                            ),
                            line_width=1)
                    )
                ],
                layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0, l=0, r=0, t=0),
                    title="Network of Authors and Articles"
                )
            )

            st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("Distribución de Autores por Artículo"):
        author_counts = [G_article.degree(p) for p in paper_nodes]
        df_counts = pd.DataFrame(author_counts, columns=['Nº de Autores'])
        
        fig = px.histogram(df_counts, x="Nº de Autores",
                           title="Frecuencia del Número de Autores por Artículo",
                           labels={'x': 'Número de Autores', 'y': 'Cantidad de Artículos'},
                           nbins=max(author_counts))
        st.plotly_chart(fig, use_container_width=True)
        col1,col2,col3 = st.columns(3)
        with col1:
            st.metric("Promedio de autores por artículo:",round(df_counts['Nº de Autores'].mean()))
        with col2:
            st.metric("Máximo de autores:",round(df_counts['Nº de Autores'].max(),2))
        with col3:
            st.metric("Artículos con un solo autor:",len(df_counts[df_counts['Nº de Autores'] == 1]))

    with st.expander("Artículos Clave"):
        tabs = st.tabs(["Puentes entre Comunidades", "Más Autores", "Más Temas"])

        with tabs[0]:
            paper_bridges = defaultdict(set)
            for author_id, comm_idx in author_community_map.items():
                author_id = author_id.replace("author_", "").strip()
                papers = author_graph.nodes[author_id].get('papers', [])
                for paper in papers:
                    paper_bridges[paper].add(comm_idx)

            if paper_bridges:
                df_bridge = pd.DataFrame({
                    'ID Artículo': paper_bridges.keys(),
                    'Comunidades Conectadas': [len(v) for v in paper_bridges.values()]
                }).sort_values('Comunidades Conectadas', ascending=False)

                df_bridge['Título'] = df_bridge['ID Artículo'].apply(
                    lambda x: pdf_data.get(x, {}).get('title', ['Desconocido'])[0] if pdf_data.get(x).get('title') else 'Desconocido'
                )

                st.dataframe(df_bridge[['Título', 'Comunidades Conectadas']].head(10), hide_index=True)

        with tabs[1]:
            paper_authors = defaultdict(set)
            for node in author_graph.nodes:
                for paper in author_graph.nodes[node].get('papers', []):
                    paper_authors[paper].add(node)

            if paper_authors:
                df_authors = pd.DataFrame({
                    'ID Artículo': paper_authors.keys(),
                    'Cantidad de Autores': [len(v) for v in paper_authors.values()]
                }).sort_values('Cantidad de Autores', ascending=False)

                df_authors['Título'] = df_authors['ID Artículo'].apply(
                    lambda x: pdf_data.get(x, {}).get('title', ['Desconocido'])[0] if pdf_data.get(x).get('title') else 'Desconocido'
                )

                st.dataframe(df_authors[['Título', 'Cantidad de Autores']].head(10), hide_index=True)

        with tabs[2]:
            if pdf_data:
                df_topics = []
                for paper_id, metadata in pdf_data.items():
                    keywords = metadata.get('keywords', [])
                    num_keywords = len(keywords)
                    title = metadata.get('title', ['Desconocido'])[0] if pdf_data.get(paper_id).get('title') else 'Desconocido'
                    df_topics.append({
                        'ID Artículo': paper_id,
                        'Título': title,
                        'Cantidad de Temas': num_keywords
                    })

                df_topics = pd.DataFrame(df_topics).sort_values('Cantidad de Temas', ascending=False)
                st.dataframe(df_topics[['Título', 'Cantidad de Temas']].head(10), hide_index=True)
            else:
                st.info("No hay información de temas disponible.")



    