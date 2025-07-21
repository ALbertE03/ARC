
import streamlit as st
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go 
from collections import defaultdict
import json
from networkx.algorithms import community

@st.cache_data
def load_pdf():
    try:
        with open("./data/extract_result.json",'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("No se encontró el archivo extract_result.json")
        return None
@st.cache_data
def process_niche_topics(_keyword_graph):
    """
    Analiza el grafo para encontrar autores y sus temas de nicho.
    """
    specialist_to_topics = defaultdict(list)

    niche_topics_set = set()
    for keyword_node, data in _keyword_graph.nodes(data=True):
        if data.get('type') == 'keyword':
            authors = [n for n in _keyword_graph.neighbors(keyword_node) if _keyword_graph.nodes[n].get('type') == 'author']
            if 1 <= len(authors) <= 2:
                niche_topics_set.add(keyword_node)

    
    for author_node, data in _keyword_graph.nodes(data=True):
        if data.get('type') == 'author':
            author_name = data.get('name', 'N/A')
            specialized_topics = [
                neighbor for neighbor in _keyword_graph.neighbors(author_node)
                if neighbor in niche_topics_set
            ]
            if specialized_topics:
                specialist_to_topics[author_name] = specialized_topics
    
    if not specialist_to_topics:
        return pd.DataFrame(), {}

    df_data = {
        'Especialista': specialist_to_topics.keys(),
        'Nº de Temas de Nicho': [len(topics) for topics in specialist_to_topics.values()]
    }
    df = pd.DataFrame(df_data).sort_values('Nº de Temas de Nicho', ascending=False)
    
    return df, specialist_to_topics

@st.cache_data
def load_key_autor():
    try:
        return nx.read_graphml('./graph/author_collaboration_graph_keywords.graphml')
    except:
        st.error("ruta incorrecta")
        st.stop()
def render_authors_page(author_analytics, keyword_graph):
    """
    Renderiza la página de análisis de autores
    """
    if 'master_table' not in author_analytics or author_analytics['master_table'].empty:
        st.error("No hay datos de autores para analizar.")
        return
    
    pdf_data = load_pdf()
    if pdf_data is None:
        return

    master_df = author_analytics['master_table']
    communities = author_analytics.get('communities', [])
    author_graph = st.session_state.get('author_graph')
    key_autor = load_key_autor()
    communities1 = list(community.louvain_communities(key_autor, weight='weight', seed=42))
    author_community_map = {author: i for i, comm in enumerate(communities1) for author in comm}


    with st.expander("Explorador de Autores y Rankings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            a = int(master_df['Artículos'].min())
            m = int(master_df['Artículos'].max())
            min_papers = st.slider("Mínimo de Artículos Publicados:", a, m, a, key="min_papers_filter")
        with col2:
            b = int(master_df['Nº Colaboradores'].min())
            m2 = int(master_df['Nº Colaboradores'].max())
            min_collabs = st.slider("Mínimo de Colaboradores:", b, m2, b, key="min_collabs_filter")
        
        filtered_df = master_df[(master_df['Artículos'] >= min_papers) & (master_df['Nº Colaboradores'] >= min_collabs)]
        
        if filtered_df.empty:
            st.warning("No hay autores que cumplan con los criterios de filtrado.")
        else:
            st.info(f"Mostrando **{len(filtered_df)}** de **{len(master_df)}** autores que cumplen los criterios.")
            top_n = st.slider("Mostrar el Top N en los rankings:", 1, max(1, len(filtered_df)), min(10, len(filtered_df)), key="author_rank_slider")
            
            st.divider()
            
            col_rank1, col_rank2 = st.columns(2)
            with col_rank1:
                st.subheader("Top por Artículos")
                st.dataframe(
                    filtered_df[['Autor', 'Artículos']].nlargest(top_n, 'Artículos'),
                    use_container_width=True, hide_index=True
                )
            with col_rank2:
                st.subheader("Top por Colaboradores")
                st.dataframe(
                    filtered_df[['Autor', 'Nº Colaboradores']].nlargest(top_n, 'Nº Colaboradores'),
                    use_container_width=True, hide_index=True
                )

    
    with st.expander("Autores más Influyentes", expanded=False):
        if author_graph is not None and author_graph.number_of_nodes() > 0 and keyword_graph is not None and keyword_graph.number_of_nodes() > 0:
            
            degree_centrality = nx.degree_centrality(author_graph)
            betweenness_centrality = nx.betweenness_centrality(keyword_graph, k=min(100, len(keyword_graph.nodes)-1) , seed=42) 
            pagerank = nx.pagerank(author_graph, weight='weight')
            tab1, tab2, tab3 = st.tabs([
                "Hubs de Colaboración", 
                "Puentes del Conocimiento", 
                "Ecosistema de Influencia"
            ])

            with tab1:
                top_hubs = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)
                u = st.slider("Mostrar el Top N de Autores Influyentes:", 1, len(top_hubs), min(5,len(top_hubs)), key="top_influential_slider2")
                for author_id, score in top_hubs[:u]:
                    author_data = author_graph.nodes[author_id]
                    num_connections = author_graph.degree(author_id)
                    neighbors = list(author_graph.neighbors(author_id))
                    top_collaborators = sorted(neighbors, key=lambda n: pagerank.get(n, 0), reverse=True)
                    top_collaborator_names = [author_graph.nodes[n].get('name', n) for n in top_collaborators]
                    with st.container(border=True):
                            st.subheader(author_data.get('name', author_id))
                            st.write(f"Colabora directamente con **{num_connections}** investigadores.")
                            with st.expander("Colaboradores:"):
                                q1 = st.slider("Mostrar los principales colaboradores:", 1, len(top_collaborator_names), min(3, len(top_collaborator_names)), key=f"top_collaborators_slider{author_id}")
                                for collaborator in top_collaborator_names[:q1]:
                                    st.write(f"- {collaborator}")
  
            with tab2: 
                key_scores = {
                    node: score for node, score in betweenness_centrality.items()
                    if keyword_graph.nodes[node].get('type') == 'keyword'
                }
                top_theme_bridges = sorted(key_scores.items(), key=lambda x: x[1], reverse=True)

                u2 = st.slider(
                    "Mostrar el Top N de Temas Puente:",
                    min_value=1,
                    max_value=len(top_theme_bridges),
                    value=min(5, len(top_theme_bridges)),
                    key="bridges_slider"
                )

                if not top_theme_bridges:
                    st.warning("No se encontraron temas puente en el grafo.")
                else:
                    for theme_name, score in top_theme_bridges[:u2]:
                        with st.container(border=True):
                          
                            st.subheader(theme_name.capitalize(),anchor=False)
                            author_neighbors_ids = [
                                node_id for node_id in keyword_graph.neighbors(theme_name)
                                if keyword_graph.nodes[node_id].get('type') == 'author'
                            ]
                            
                            if not author_neighbors_ids:
                                st.info("No hay autores directamente asociados a este tema.")
                                continue

                            author_details = [keyword_graph.nodes[node_id] for node_id in author_neighbors_ids]
                            author_names = sorted([data.get('name', 'N/A') for data in author_details])

                            with st.expander(f"{len(author_names)} autores que impulsan este tema", expanded=False):

                                    num_to_show = st.slider(
                                        "Mostrar los N autores principales:", 
                                        min_value=1, 
                                        max_value=len(author_names), 
                                        value=min(10, len(author_names)),  
                                        key=f"top_authors_{theme_name}"
                                    )
                                    
                                    num_cols = 3
                                    rows_needed = (num_to_show + num_cols - 1) // num_cols  
                                    
                                    for row in range(rows_needed):
                                        cols = st.columns(num_cols)
                                        for col in range(num_cols):
                                            idx = row * num_cols + col
                                            if idx < num_to_show:
                                                with cols[col]:
                                                    st.markdown(f"""
                                                    {author_names[idx]}""")
                                                    
            with tab3:
                top_pagerank = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
                u3 = st.slider("Mostrar el Top N de Autores Influyentes:", 1, len(top_pagerank), min(5,len(top_pagerank)), key="top_influential_slide3r")
                for author_id, score in top_pagerank[:u3]:
                    author_data = author_graph.nodes[author_id]

                    neighbors = list(author_graph.neighbors(author_id))
                    top_collaborators = sorted(neighbors, key=lambda n: pagerank.get(n, 0), reverse=True)
                    top_collaborator_names = [author_graph.nodes[n].get('name', n) for n in top_collaborators]

                    with st.container(border=True):
                       
                        
                        st.subheader(author_data.get('name', author_id), anchor=False)
                        if top_collaborator_names:
                            with st.expander("Colaboradores Principales", expanded=False):
                                num_to_show = st.slider(
                                    "Mostrar los principales colaboradores:",
                                    min_value=1,
                                    max_value=len(top_collaborator_names),
                                    value=min(3, len(top_collaborator_names)),
                                    key=f"top_collaborators_{author_id}"
                                )
                                
                                num_cols = 3
                                rows_needed = (num_to_show + num_cols - 1) // num_cols  

                                for row in range(rows_needed):
                                    cols = st.columns(num_cols)
                                    for col in range(num_cols):
                                        idx = row * num_cols + col
                                        if idx < num_to_show:
                                            with cols[col]:
                                                st.markdown(f"""     
                                                 • {top_collaborator_names[idx]}
                                                
                                                """)

        else:
            st.warning("No hay datos de red disponibles para analizar la influencia.")

    with st.expander("Autores más Prolíficos", expanded=False):
        t = st.slider("top N",1,len(master_df),10)
        prolific_data = master_df[['Autor', 'Artículos', 'Nº Colaboradores']].copy()
        prolific_data['Artículos'] = prolific_data['Artículos'].astype(int)
        
        filtered_prolific = prolific_data.nlargest(t, 'Artículos')

        if not filtered_prolific.empty:
            fig = px.scatter(
                filtered_prolific,
                x='Nº Colaboradores',
                y='Artículos',
                size='Artículos',
                color='Nº Colaboradores',
                hover_name='Autor',
                title=f'Top {t} Autores más Prolíficos',
                labels={'Artículos': 'Número de Artículos', 'Nº Colaboradores': 'Colaboradores'}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                filtered_prolific,
                column_config={
                    "Autor": st.column_config.TextColumn("Autor"),
                    "Artículos": st.column_config.NumberColumn(
                        "Artículos",
                        format="%d",
                        min_value=0
                    ),
                    "Nº Colaboradores": st.column_config.NumberColumn(
                        "Colaboradores",
                        format="%d",
                        min_value=0
                    )
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning("No hay autores que cumplan los criterios de filtrado")
            
    with st.expander("Puentes Temáticos entre Comunidades", expanded=False):
        inter_community_edges = defaultdict(int)
        for u, v in key_autor.edges():
            c1 = author_community_map.get(u)
            c2 = author_community_map.get(v)
            if c1 is not None and c2 is not None and c1 != c2:
                edge = tuple(sorted((c1, c2)))
                inter_community_edges[edge] += 1
                
        if not inter_community_edges:
            st.warning("No se encontraron conexiones temáticas entre las diferentes comunidades.")
        else:
            collaboration_data = []
            for (c1, c2), weight in inter_community_edges.items():
                collaboration_data.append({
                    'Comunidad A': f"Comunidad {c1+1}",
                    'Comunidad B': f"Comunidad {c2+1}",
                    'Nº Conexiones Temáticas': weight, 
                    'indices': (c1, c2)
                })
            
            df_collab = pd.DataFrame(collaboration_data).sort_values('Nº Conexiones Temáticas', ascending=False)
            
            st.subheader("Comunidades con Mayor Conexión Temática")
            st.dataframe(df_collab[['Comunidad A', 'Comunidad B', 'Nº Conexiones Temáticas']].head(10), hide_index=True, use_container_width=True)

            st.divider()

            st.subheader("Análisis Detallado de los Puentes")
            options_list = [f"{row['Comunidad A']} <-> {row['Comunidad B']}" for _, row in df_collab.iterrows()]
            selected_pair_str = st.selectbox("Selecciona un par de comunidades para analizar:", options=options_list)

            if selected_pair_str:
                selected_row = df_collab[df_collab.apply(lambda r: f"{r['Comunidad A']} <-> {r['Comunidad B']}" == selected_pair_str, axis=1)].iloc[0]
                c1_idx, c2_idx = selected_row['indices']
                
                topics_c1 = set()
                for author_id in communities1[c1_idx]:
                    topics_c1.update(n for n in keyword_graph.neighbors(author_id) if keyword_graph.nodes[n].get('type') == 'keyword')

                topics_c2 = set()
                for author_id in communities1[c2_idx]:
                    topics_c2.update(n for n in keyword_graph.neighbors(author_id) if keyword_graph.nodes[n].get('type') == 'keyword')
                

                bridge_topics = topics_c1.intersection(topics_c2)

                st.markdown("##### Temas Puente que Conectan Ambas Comunidades")
                if bridge_topics:
                    st.multiselect("Temas en común:", options=list(bridge_topics), default=list(bridge_topics), disabled=True)
                else:
                    st.warning("No se encontraron temas compartidos directos entre estas dos comunidades.")
                if bridge_topics:    
                    st.divider()    
                    st.markdown("##### Autores que Trabajan en los Temas Puente")
                    col1, col2 = st.columns(2)

                    def display_bridge_authors(comm_idx, community_name, bridge_topics, column):
                        with column:
                            st.markdown(f"**De {community_name}:**")
                            bridge_authors_in_comm = []
                            for author_id in communities1[comm_idx]:
                                author_topics = {n for n in keyword_graph.neighbors(author_id) if keyword_graph.nodes[n].get('type') == 'keyword'}
                                if author_topics.intersection(bridge_topics):
                                    author_name = key_autor.nodes[author_id].get('name', author_id)
                                    bridge_authors_in_comm.append(author_name)
                            lim = st.slider("Cantidad a mostrar",1,len(bridge_authors_in_comm),min(3,len(bridge_authors_in_comm)),key=f"bridge_authors_{comm_idx}")
                            if bridge_authors_in_comm:
                                for name in sorted(bridge_authors_in_comm)[:lim]: 
                                    st.write(f" • {name}")
                            else:
                                st.info("Ningún autor de esta comunidad trabaja en los temas puente.")
                    
                    display_bridge_authors(c1_idx, selected_row['Comunidad A'], bridge_topics, col1)
                    display_bridge_authors(c2_idx, selected_row['Comunidad B'], bridge_topics, col2)

    with st.expander("Especialistas y Temas de Nicho", expanded=False):
    
        df_specialists, specialist_to_topics_map = process_niche_topics(keyword_graph)

        if not df_specialists.empty:
            st.subheader("Ranking de Especialistas por N° de Temas de Nicho",anchor=False)
            
            top_n_slider = st.slider(
                "Mostrar el Top N de Especialistas:",
                min_value=1,
                max_value=len(df_specialists),
                value=min(10, len(df_specialists)), 
                key="niche_barchart_slider"
            )
            top_specialists_df = df_specialists.head(top_n_slider)
            fig = px.bar(
                df_specialists.head(top_n_slider),
                x='Nº de Temas de Nicho',
                y='Especialista',
                orientation='h',
                title=f"Top {top_n_slider} Especialistas con más Temas de Nicho",
                labels={'Nº de Temas de Nicho': 'Cantidad de Temas Únicos', 'Especialista': 'Nombre del Especialista'},
                text='Nº de Temas de Nicho', 
                color='Nº de Temas de Nicho',
                color_continuous_scale=px.colors.sequential.Plasma
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
            st.subheader(f"Análisis del Top {top_n_slider}",anchor=False)
            for ll, row in top_specialists_df.iterrows():
                specialist_name = row['Especialista']
                topics = specialist_to_topics_map.get(specialist_name, [])
                
                with st.expander(f"**{specialist_name}** - {len(topics)} temas de nicho"):
                    qq=st.slider("Cantidad a mostrar",1,max_value=len(topics),value=min(3,len(topics)),key=f"{ll}{row}{row}")
                    qwer = st.columns(2)
                    for i,topic in enumerate(topics[:qq]):
                        with qwer[i%2]:
                            st.markdown(f"{i+1}. {topic.capitalize()}")
        else:
            st.warning("No se encontraron temas de nicho o especialistas asociados.")

    with st.expander("Pares de Autores que más Colaboran",expanded=False):
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
            with st.expander("#### Artículos en colaboración",expanded=False):

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
    

    with st.expander("Comunidades más Productivas", expanded=False):
        if communities:
            community_stats = []
          
            for i, comm in enumerate(communities):
                a=set()
                members = len(comm)
                papers = sum(len(author_graph.nodes[node_id].get('papers', [])) for node_id in comm)
                community_stats.append({
                    'Comunidad': f"Comunidad {i+1}",
                    'Miembros': members,
                    'Artículos': papers,
                    'Productividad': round(papers / members, 2) if members > 0 else 0,
                    'community_index': i
                })
            
            comm_df = pd.DataFrame(community_stats).sort_values('Productividad', ascending=False)
            p = st.slider("Mostrar el Top N de Comunidades:", 1, len(comm_df), min(5, len(comm_df)), key="top_communities_slider")
            fig = px.bar(
                comm_df.head(p), 
                x='Comunidad',
                y='Productividad',
                color='Miembros',
                title=f'Top {p} Comunidades por Productividad (Artículos/Miembro)',
                labels={'Productividad': 'Artículos por miembro'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### Detalles por Comunidad")
            selected_comm_name = st.selectbox(
                "Selecciona una comunidad para ver sus miembros:", 
                options=comm_df['Comunidad'][:p]
            )
            comm_data = comm_df[comm_df['Comunidad'] == selected_comm_name].iloc[0]
            comm_index = comm_data['community_index']
            member_nodes = communities[comm_index]
            a =set()
            mape = {}
            for node_id in member_nodes:
                node_data = author_graph.nodes[node_id]
                a.update(x for x in node_data.get('papers', []))
                mape[node_id] = a
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Miembros", comm_data['Miembros'])
            with col2:
                st.metric("Artículos totales", len(a))
            g =set()
            st.markdown(f"**Artículos en la comunidad:**")
            for id,pdf_id in mape.items():
                for f in pdf_id:
                    pdf_data1 = pdf_data.get(f, {})
                    title = pdf_data1.get('title', 'Título no disponible')
                    g.add(title[0] if title else title)
            w ={}
            for j,i in enumerate(g,start=1):
                w[i]=j
                st.markdown(f"{j}. {i}")
            st.markdown(f"**Miembros de la {selected_comm_name}**")

            comm_index = comm_data['community_index']
            member_nodes = communities[comm_index]

            member_details = []
            for node_id in member_nodes:
                node_data = author_graph.nodes[node_id]
                papers = node_data.get('papers',[])
                s=''
                for j,i in enumerate(papers,start=1):
                    if j+1<=len(papers):
                        s+=f'{w[pdf_data[i].get("title", ["Título no disponible"])[0] if pdf_data[i].get("title") else "Título no disponible"]}, '
                        continue
                    s+=f'{w[pdf_data[i].get("title", ["Título no disponible"])[0] if pdf_data[i].get("title") else "Título no disponible"]}'
                member_details.append({
                    'Autor': node_data.get('name', 'Nombre no disponible'),
                    'Artículos Publicados': len(node_data.get('papers', [])),
                    'id de articulos': s
                })

            if member_details:
                members_df = pd.DataFrame(member_details).sort_values('Artículos Publicados', ascending=False)
                st.dataframe(members_df, use_container_width=True, hide_index=True)
            else:
                st.info("Esta comunidad no tiene miembros para mostrar.")

        else:
            st.warning("No se detectaron comunidades")

    with st.expander("Colaboraciones Exclusivas", expanded=False):
        if author_graph is not None:
          
            total_edges = len(author_graph.edges())
            exclusive_pairs = []
            
            for node in author_graph.nodes():
                neighbors = list(author_graph.neighbors(node))
                if len(neighbors) == 1:
                    collaborator = neighbors[0]
                    edge_data = author_graph.get_edge_data(node, collaborator)
                    weight = edge_data.get('weight', 1)
                    percentage = (weight / total_edges) * 100 if total_edges > 0 else 0
                    
                    exclusive_pairs.append({
                        'author1': author_graph.nodes[node].get('name', node),
                        'author2': author_graph.nodes[collaborator].get('name', collaborator),
                        'collaborations': weight,
                        'percentage': percentage
                    })

            if exclusive_pairs:
                st.subheader("Relaciones de Colaboración Única")
                cols = st.columns(3)
                cols[0].metric("Pares exclusivos", len(exclusive_pairs))
                cols[1].metric("Colaboraciones totales", total_edges)
                cols[2].metric("Representación", f"{sum(p['percentage'] for p in exclusive_pairs):.1f}%")
                st.subheader("Distribución en la red")
                  
                fig = px.pie(
                        names=["Exclusivas", "Otras"],
                        values=[sum(p['percentage'] for p in exclusive_pairs), 
                            100 - sum(p['percentage'] for p in exclusive_pairs)],
                        hole=0.5,
                        color_discrete_sequence=['#FF6B00', '#DDDDDD']
                    )
                fig.update_traces(textinfo='percent+label', 
                                    marker=dict(line=dict(color='#FFFFFF', width=2)))
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Principales colaboraciones exclusivas",expanded=False):
                    k = st.slider("Mostrar el Top N de Colaboraciones Exclusivas:", 1, len(exclusive_pairs), 5, key="exclusive_pairs_slider")
                    top_pairs = sorted(exclusive_pairs, key=lambda x: x['collaborations'], reverse=True)[:k]

                    for pair in top_pairs:           
                        col1, col2, col3 = st.columns([1,2,1])
                        with col1:
                            st.markdown(f"### {pair['author1']}")
                            st.caption("Autor principal")
                        
                        with col2:
                            st.markdown(f"<div style='text-align: center; margin: 15px 0;'>"
                                    f"<h2 style='color: #FF6B00;'>⇄ {pair['collaborations']} colaboraciones</h2>"
                                    f"<small>Relación exclusiva</small></div>", 
                                    unsafe_allow_html=True)
                        
                        with col3:
                            st.markdown(f"### {pair['author2']}")
                            st.caption("Único colaborador")

                        st.write("")

                
            else:
                st.info("No se encontraron relaciones de colaboración exclusiva", icon="ℹ️")
        else:
            st.warning("Red de colaboración no disponible", icon="⚠️")
