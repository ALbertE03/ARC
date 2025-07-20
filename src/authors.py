import streamlit as st
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go 
import matplotlib.pyplot as plt
import json
from src.utils import load_article_grap
from nxviz import ArcPlot
@st.cache_data
def load_pdf():
    try:
        with open("./data/extract_result.json",'r') as f:
            return json.load(f)
    except:
        return None
    

def render_authors_page(author_analytics,keyword_graph):
    """
    Renderiza la página de análisis de autores con filtros, tablas y visualizaciones avanzadas.
    """
    if 'master_table' not in author_analytics or author_analytics['master_table'].empty:
        st.error("No hay datos de autores para analizar.")
        return
    pdf_data = load_pdf()
    if pdf_data is None:
        st.error("Error al cargar los datos del PDF.")
        return
    master_df = author_analytics['master_table']
    communities = author_analytics['communities']
    papers = author_analytics.get('papers', {})
    article_graph = load_article_grap('./graph/articles_graph.graphml')
    author_graph = st.session_state.get('author_graph') 

    # representar en una tabla 
    with st.expander("**Filtros**", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            a=int(master_df['Artículos'].min())
            m=int(master_df['Artículos'].max())
            min_papers = st.slider("Mínimo de Artículos Publicados:", a, m, m//2)
        with col2:
            b=int(master_df['Nº Colaboradores'].min())
            m2=int(master_df['Nº Colaboradores'].max())
            min_collabs = st.slider("Mínimo de Colaboradores:", b,m2 , m2//2)
        

        filtered_df = master_df[(master_df['Artículos'] >= min_papers) & (master_df['Nº Colaboradores'] >= min_collabs)]
        if filtered_df.empty:
            st.warning("No hay autores que cumplan con los criterios de filtrado.")
            return
        st.info(f"Mostrando **{len(filtered_df)}** de **{len(master_df)}** autores que cumplen los criterios.")
        top_n = st.slider("Mostrar el Top N en los rankings:", 1, len(filtered_df), len(filtered_df)//2, key="author_rank_slider")
               
        filtered_df = filtered_df[['Autor', 'Artículos']].sort_values('Artículos', ascending=False).head(top_n)
        P = nx.Graph()
        for i, j in papers.items():
            if i in filtered_df['Autor'].values:
                if not P.has_node(i):
                    P.add_node(i)
                for k in j:
                    article = pdf_data.get(k, {}).get('title', k) 
                    try:
                        article = article[0] if isinstance(article, list) else article
                    except:
                        article = k
                    if not P.has_node(article):
                        P.add_node(article)
                    if not P.has_edge(i, article):
                        P.add_edge(i, article)

        fig, ax = plt.subplots(figsize=(5, 3))

        pos = nx.spring_layout(P)

        node_colors = []
        node_sizes=[]
        node_labels = {}
        for node in P.nodes():
            if node in filtered_df['Autor'].values:
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

    with st.expander("🤝 Pares de Autores que más Colaboran"):
        if author_graph is not None:
            top_k = st.slider("Mostrar el Top N de Pares de Autores:", 1, 20, 10, key="top_pairs_slider")
            edge_weights = nx.get_edge_attributes(author_graph, 'weight')
            top_pairs = sorted(edge_weights.items(), key=lambda x: x[1], reverse=True)[:top_k]
            
            pairs = [f"{author_graph.nodes[pair[0][0]]['name']}  <->  {author_graph.nodes[pair[0][1]]['name']}" for pair in top_pairs]
            weights = [pair[1] for pair in top_pairs]
            
            fig = px.bar(
                x=weights,
                y=pairs,
                orientation='h',
                title=f"Top {len(top_pairs)} Pares de Autores con más Colaboraciones",
                labels={'x': 'Número de Colaboraciones', 'y': 'Pares de Autores'},
                color=weights,
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("#### Artículos en colaboración")
                    
            for i, (pair, weight) in enumerate(top_pairs, 1):
                        author1 = author_graph.nodes[pair[0]].get('name', pair[0])
                        author2 = author_graph.nodes[pair[1]].get('name', pair[1])
                        
                        with st.expander(f"**{i}. {author1} & {author2} - {weight} artículos**", expanded=(i==1)):
                            articles = set(author_graph.nodes[pair[0]]['papers']) & set(author_graph.nodes[pair[1]]['papers'])

                            if articles:
                                for article_id in articles:
                                    article_data = pdf_data.get(article_id, {})
                                    title = article_data.get('title', 'Título no disponible')[0]
                                    year = article_data.get('year', 'Año no disponible')
                                    
                                    st.markdown(f"""
                                    - **{title}** 
                                    """)
                            else:
                                st.warning("No se encontraron detalles de los artículos")
        else:
            st.warning("No hay datos de colaboración entre autores disponibles.")

    # Autores puente
    with st.expander("🌉 Autores Puente"):
        if author_graph is not None:
            # Calcular betweenness centrality
            betweenness = nx.betweenness_centrality(author_graph)
            top_betweenness = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:top_n]
            
            # Mostrar tabla con los autores puente
            bridge_df = pd.DataFrame(top_betweenness, columns=['Autor', 'Centralidad de Intermediación'])
            bridge_df['Centralidad de Intermediación'] = bridge_df['Centralidad de Intermediación'].apply(lambda x: round(x, 4))
            
            st.dataframe(
                bridge_df.style.background_gradient(cmap='Blues', subset=['Centralidad de Intermediación']),
                use_container_width=True
            )
            
            # Explicación
            st.info("""
            **Autores Puente** son aquellos que conectan diferentes grupos o comunidades en la red. 
            Su **Centralidad de Intermediación** mide cuánto actúan como puente entre otros autores.
            """)
        else:
            st.warning("No hay datos de red de autores disponibles para este análisis.")

    
        st.markdown("Explora, busca y ordena la tabla completa con todos los autores que cumplen los filtros.")
        search_term = st.text_input("Buscar autor en la tabla filtrada:", key="author_search")
        
        display_df = filtered_df
        if search_term:
            display_df = display_df[display_df['Autor'].str.contains(search_term, case=False, na=False)]
            
        st.dataframe(display_df.style.format({
            'Intermediación': '{:.4f}',
            'Influencia (Eigenvector)': '{:.4f}',
            'Influencia (PageRank)': '{:.4f}',
            'Cohesión (Clustering)': '{:.3f}'
        }), use_container_width=True, hide_index=True)