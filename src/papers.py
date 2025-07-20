import networkx as nx
import streamlit as st
import pandas as pd 
from src.utils import load_article_grap,_centrality
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from networkx.algorithms import community
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



def render_papers_page():
    G_article = load_article_grap('./graph/articles_graph.graphml')
    min_grade = [G_article.degree(x) for x,d in G_article.nodes(data=True) if d and d['type']=='papers']
    paper_nodes = [n for n, d in G_article.nodes(data=True) if d.get('type') == 'papers']
    centrality_metrics = calculate_centrality(G_article)
    author_community_map = detect_author_communities(G_article)

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
    
    with st.expander("📊 Distribución de Autores por Artículo"):
        author_counts = [G_article.degree(p) for p in paper_nodes]
        df_counts = pd.DataFrame(author_counts, columns=['Nº de Autores'])
        
        fig = px.histogram(df_counts, x="Nº de Autores",
                           title="Frecuencia del Número de Autores por Artículo",
                           labels={'x': 'Número de Autores', 'y': 'Cantidad de Artículos'},
                           nbins=max(author_counts))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"""
        - **Promedio de autores por artículo:** `{df_counts['Nº de Autores'].mean():.2f}`
        - **Máximo de autores en un solo artículo:** `{df_counts['Nº de Autores'].max()}`
        - **Total de artículos con un solo autor:** `{len(df_counts[df_counts['Nº de Autores'] == 1])}`
        """)

    with st.expander("🏆 Artículos con Mayor Impacto y Centralidad"):
        st.info("Aquí se clasifican los artículos según diferentes métricas de importancia en la red de colaboración.")
        # Preparar dataframes para los rankings
        paper_metrics = []
        for paper in paper_nodes:
            paper_metrics.append({
                'Artículo': paper,
                'Nº Autores (Grado)': G_article.degree(paper),
                'Interconexión (Betweenness)': centrality_metrics['betweenness_centrality'].get(paper, 0),
                'Influencia (PageRank)': centrality_metrics['pagerank'].get(paper, 0)
            })
        df_metrics = pd.DataFrame(paper_metrics)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Más Colaborativos")
            st.dataframe(df_metrics[['Artículo', 'Nº Autores (Grado)']].sort_values('Nº Autores (Grado)', ascending=False).head(10), hide_index=True)
        with col2:
            st.subheader("Más Interconectores")
            st.dataframe(df_metrics[['Artículo', 'Interconexión (Betweenness)']].sort_values('Interconexión (Betweenness)', ascending=False).head(10), hide_index=True, use_container_width=True)
        with col3:
            st.subheader("Más Influyentes")
            st.dataframe(df_metrics[['Artículo', 'Influencia (PageRank)']].sort_values('Influencia (PageRank)', ascending=False).head(10), hide_index=True, use_container_width=True)

    with st.expander("🤝 Artículos con Mayor Interdisciplinariedad"):
        st.markdown("""
        Se mide la interdisciplinariedad de un artículo contando de **cuántas comunidades de investigación diferentes provienen sus autores**. 
        Un puntaje alto sugiere que el artículo es un punto de encuentro para diversas áreas del conocimiento.
        """)
        interdisciplinary_scores = []
        for paper in paper_nodes:
            authors = G_article.neighbors(paper)
            communities_involved = {author_community_map.get(author) for author in authors if author in author_community_map}
            score = len(communities_involved)
            interdisciplinary_scores.append({'Artículo': paper, 'Puntaje Interdisciplinario': score, 'Nº Autores': G_article.degree(paper)})
        
        df_interdisciplinary = pd.DataFrame(interdisciplinary_scores).sort_values('Puntaje Interdisciplinario', ascending=False)
        st.dataframe(df_interdisciplinary.head(15), hide_index=True, use_container_width=True)

        st.markdown("Selecciona un artículo para encontrar otros que compartan la mayor cantidad de autores.")
        selected_paper = st.selectbox("Elige un artículo de referencia:", options=sorted(paper_nodes))

        if selected_paper:
            target_authors = set(G_article.neighbors(selected_paper))
            similarities = []
            for other_paper in paper_nodes:
                if other_paper != selected_paper:
                    other_authors = set(G_article.neighbors(other_paper))
                    # Jaccard Similarity
                    intersection = len(target_authors.intersection(other_authors))
                    union = len(target_authors.union(other_authors))
                    if union > 0:
                        similarity = intersection / union
                        if similarity > 0:
                            similarities.append({
                                'Artículo Similar': other_paper,
                                'Similitud (Jaccard)': f"{similarity:.2%}",
                                'Autores en Común': intersection
                            })
            
            if similarities:
                df_similar = pd.DataFrame(similarities).sort_values('Autores en Común', ascending=False)
                st.dataframe(df_similar.head(10), hide_index=True, use_container_width=True)
            else:
                st.info("No se encontraron otros artículos que compartan autores con el seleccionado.")