import networkx as nx
import streamlit as st
import pandas as pd 
from src.utils import load_article_grap
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from networkx.algorithms import community
from collections import defaultdict
import json
from itertools import combinations

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
    
    author_nodes = {n for n, d in _g.nodes(data=True) if d.get('type') == 'author'}
    author_graph = nx.Graph()
    
    for paper_node, data in _g.nodes(data=True):
        if data.get('type') == 'papers':
            authors_of_paper = [n for n in _g.neighbors(paper_node) if n in author_nodes]
            for i in range(len(authors_of_paper)):
                for j in range(i + 1, len(authors_of_paper)):
                    u, v = authors_of_paper[i], authors_of_paper[j]
                    if author_graph.has_edge(u, v):
                        author_graph[u][v]['weight'] += 1
                    else:
                        author_graph.add_edge(u, v, weight=1)

    communities_list = list(community.louvain_communities(author_graph, weight='weight'))
    author_to_community = {author: i for i, comm in enumerate(communities_list) for author in comm}
    return author_to_community

@st.cache_data
def load_article_key():
    try:
        return nx.read_graphml('./graph/article_keywords_graph.graphml')
    except:
        st.error("ruta incorrecta")
        st.stop()


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
def get_node_name(graph, node_id, default_prefix="ID:"):
    node_data = graph.nodes.get(node_id, {})
    return node_data.get('name', node_id)

def render_papers_page(author_graph,keyword_graph):
    G_article = load_article_grap('./graph/articles_graph.graphml')
    min_grade = [G_article.degree(x) for x,d in G_article.nodes(data=True) if d and d['type']=='papers']
    paper_nodes = [n for n, d in G_article.nodes(data=True) if d.get('type') == 'papers']
    centrality_metrics = calculate_centrality(G_article)
    author_community_map = detect_author_communities(G_article)
    pdf_data = load_pdf()
    key_autor = load_key_autor()
    communities1 = list(community.louvain_communities(key_autor, weight='weight', seed=42))
    author_community_map1 = {author: i for i, comm in enumerate(communities1) for author in comm}
    article_key_graph = load_article_key()

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
    
    with st.expander("Artículos Clave: Análisis por Autores y Temas", expanded=False):
        tabs = st.tabs(["Ranking por N° de Autores", "Ranking por N° de Temas"])

        with tabs[0]:

            paper_authors_map = defaultdict(list)
            paper_nodes_social = [n for n, d in G_article.nodes(data=True) if d.get('type') == 'papers']
            for paper_id in paper_nodes_social:
                authors = [get_node_name(G_article, author_id) for author_id in G_article.neighbors(paper_id)]
                paper_authors_map[paper_id] = authors

            if paper_authors_map:
                df_authors = pd.DataFrame({
                    'ID Artículo': paper_authors_map.keys(),
                    'Cantidad de Autores': [len(v) for v in paper_authors_map.values()]
                }).sort_values('Cantidad de Autores', ascending=False).reset_index(drop=True)
                df_authors['Título'] = df_authors['ID Artículo'] 

                df_display = df_authors[['Título', 'Cantidad de Autores']]
                df_display.insert(0, "Seleccionar", False)

                st.markdown("**Tabla de artículos ordenados por cantidad de autores**")
                edited_df = st.data_editor(
                    df_display,
                    column_config={"Seleccionar": st.column_config.CheckboxColumn(required=True)},
                    use_container_width=True, hide_index=True, key="authors_editor"
                )

                selected_rows = edited_df[edited_df['Seleccionar']]
                if not selected_rows.empty:
                    st.subheader("Detalles de los Artículos Seleccionados")
                    for index, row in selected_rows.iterrows():
                        paper_id = df_authors.iloc[index]['ID Artículo']
                        with st.expander(f"Autores de: {row['Título']}"):
                            cols = st.columns(3)
                            for o, author_name in enumerate(paper_authors_map.get(paper_id, [])):

                                with cols[o % 3]:
                                    st.markdown(f" • {author_name}")

        with tabs[1]:
            paper_keywords_map = defaultdict(list)
            paper_nodes_thematic = [n for n, d in article_key_graph.nodes(data=True) if d.get('type') == 'papers']
            for paper_id in paper_nodes_thematic:
                keywords = [get_node_name(article_key_graph, kw_id) for kw_id in article_key_graph.neighbors(paper_id)]
                paper_keywords_map[paper_id] = keywords

            if paper_keywords_map:
                df_topics = pd.DataFrame({
                    'ID Artículo': paper_keywords_map.keys(),
                    'Cantidad de Temas': [len(v) for v in paper_keywords_map.values()]
                }).sort_values('Cantidad de Temas', ascending=False).reset_index(drop=True)
                df_topics['Título'] = df_topics['ID Artículo'] 

                df_display_topics = df_topics[['Título', 'Cantidad de Temas']]
                df_display_topics.insert(0, "Seleccionar", False)

                st.markdown("**Tabla de artículos ordenados por cantidad de temas**")
                edited_df_topics = st.data_editor(
                    df_display_topics,
                    column_config={"Seleccionar": st.column_config.CheckboxColumn(required=True)},
                    use_container_width=True, hide_index=True, key="topics_editor"
                )

                selected_rows_topics = edited_df_topics[edited_df_topics['Seleccionar']]
                if not selected_rows_topics.empty:
                    st.subheader("Detalles de los Artículos Seleccionados")
                    for index, row in selected_rows_topics.iterrows():
                        paper_id = df_topics.iloc[index]['ID Artículo']
                        with st.expander(f"Temas de: {row['Título']}"):
                            cols2 = st.columns(3)   
                            for r, keyword in enumerate(paper_keywords_map.get(paper_id, [])):
                                with cols2[r % 3]:
                                    st.markdown(f" • {keyword.capitalize()}")