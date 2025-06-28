import streamlit as st
import networkx as nx 
from collections import defaultdict
import pandas as pd

def show_page_filter():
    st.title("🔍 Sistema de Búsqueda de Investigadores y Artículos")
    st.markdown("---")

    if 'graph' not in st.session_state:
        st.session_state.graph = nx.Graph()  
    graph = st.session_state.graph

    if 'author_options' not in st.session_state:
        authors = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'author']
        author_options = {}
        for author_id in authors:
            author_data = graph.nodes[author_id]
            name = author_data.get('display_name', author_id)
            author_options[name] = author_id
        st.session_state.author_options = author_options
    author_options = st.session_state.author_options

    if 'article_options' not in st.session_state:
        articles = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'article']
        article_options = {}
        for article_id in articles:
            article_data = graph.nodes[article_id]
            title = article_data.get('title', article_data.get('display_name', article_id))
            article_options[title] = article_id
        st.session_state.article_options = article_options
    article_options = st.session_state.article_options

    with st.expander("🔎 Buscar Investigador", expanded=False):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("🔍 Búsqueda")
            names = st.selectbox("Nombre del investigador", list(author_options.keys()), key='22a')
            selected_author_ids = []
            if names:
                selected_author_ids = [author_options[names]]
            if selected_author_ids:
                author_id = selected_author_ids[0]
                author_data = graph.nodes[author_id]
                with st.container():
                    st.markdown(f"### 👨‍🔬 {author_data.get('display_name', 'N/A')}")
                    st.markdown(f"**🆔 ID:** `{author_id}`")
                    st.markdown(f"**🏛️ Afiliación:** {author_data.get('affiliation', 'No disponible')}")
                    articles = []
                    for x in graph.neighbors(author_id):
                        if graph.nodes[x].get('node_type') == 'article':
                            articles.append(x)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("📚 Artículos", len(articles))
                    with col_b:
                        st.metric("🔗 Conexiones", graph.degree(author_id))
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                if names:
                    st.error("❌ No se encontró el investigador")

        with col2:
            st.subheader("📚 Portafolio de Publicaciones")
            if selected_author_ids:
                articles = []
                for x in graph.neighbors(selected_author_ids[0]):
                    if graph.nodes[x].get('node_type') == 'article':
                        articles.append(x)
                if articles:
                    articles_data = []
                    for art_id in articles:
                        article_data = graph.nodes[art_id]
                        articles_data.append({
                            'Título': article_data.get('title', article_data.get('display_name', art_id)),
                            'Año': article_data.get('year', 'N/A'),
                            'ID': art_id,
                            'Tipo': article_data.get('type', 'Artículo')
                        })
                    df_articles = pd.DataFrame(articles_data)
                    col_filter1, col_filter2 = st.columns(2)
                    with col_filter1:
                        years = df_articles['Año'].unique()
                        selected_year = st.selectbox("Filtrar por año:", ['Todos'] + sorted([y for y in years if y != 'N/A'], reverse=True))
                    with col_filter2:
                        sort_by = st.selectbox("Ordenar por:", ['Año (desc)', 'Año (asc)', 'Título'])
                    if selected_year != 'Todos':
                        df_articles = df_articles[df_articles['Año'] == selected_year]
                    if sort_by == 'Año (desc)':
                        df_articles = df_articles.sort_values('Año', ascending=False)
                    elif sort_by == 'Año (asc)':
                        df_articles = df_articles.sort_values('Año', ascending=True)
                    else:
                        df_articles = df_articles.sort_values('Título')
                    st.dataframe(df_articles[['Título', 'Año', 'Tipo']], 
                               use_container_width=True, 
                               hide_index=True,
                               column_config={
                                   "Título": st.column_config.TextColumn("Título", width="large"),
                                   "Año": st.column_config.NumberColumn("Año", width="small"),
                                   "Tipo": st.column_config.TextColumn("Tipo", width="medium")
                               })
                else:
                    st.info("📄 No se encontraron publicaciones para este investigador")
            else:
                st.info("👆 Seleccione un investigador para ver sus publicaciones")

    with st.expander("📖 Buscar Artículo", expanded=False):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("🔍 Búsqueda")
            selected_title = st.selectbox("Seleccione un artículo:", list(article_options.keys()), key="article_search")
            article_filter = []
            if selected_title:
                article_filter = [article_options[selected_title]]
            if article_filter:
                article_id = article_filter[0]
                article_data = graph.nodes[article_id]
                with st.container():

                    title = article_data.get('title', article_data.get('display_name', 'N/A'))
                    st.markdown(f"### 📄 {title[:50]}{'...' if len(title) > 50 else ''}")
                    st.markdown(f"**🆔 ID:** `{article_id}`")
                    st.markdown(f"**📅 Año:** {article_data.get('year', 'No disponible')}")
                    st.markdown(f"**📂 Tipo:** {article_data.get('type', 'Artículo')}")
                    authors = []
                    for x in graph.neighbors(article_id):
                        if graph.nodes[x].get('node_type') == 'author':
                            authors.append(x)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("👥 Autores", len(authors))
                    with col_b:
                        st.metric("🔗 Conexiones", graph.degree(article_id))
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("👆 Seleccione un artículo para ver detalles")

        with col2:
            st.subheader("👥 Equipo de Investigación")
            if article_filter:
                authors = []
                for x in graph.neighbors(article_filter[0]):
                    if graph.nodes[x].get('node_type') == 'author':
                        authors.append(x)
                if authors:
                    authors_data = []
                    for author_id in authors:
                        author_data = graph.nodes[author_id]
                        author_articles = sum(1 for x in graph.neighbors(author_id) 
                                            if graph.nodes[x].get('node_type') == 'article')
                        authors_data.append({
                            'Nombre': author_data.get('display_name', author_id),
                            'Afiliación': author_data.get('affiliation', 'No disponible').title(),
                            'Total Publicaciones': author_articles,
                            'ID': author_id
                        })
                    df_authors = pd.DataFrame(authors_data)
                    sort_option = st.selectbox("Ordenar por:", 
                                             ['Nombre', 'Total Publicaciones', 'Afiliación'],
                                             key="author_sort")
                    if sort_option == 'Total Publicaciones':
                        df_authors = df_authors.sort_values('Total Publicaciones', ascending=False)
                    elif sort_option == 'Afiliación':
                        df_authors = df_authors.sort_values('Afiliación')
                    else:
                        df_authors = df_authors.sort_values('Nombre')
                    st.dataframe(df_authors[['Nombre', 'Afiliación', 'Total Publicaciones']], 
                               use_container_width=True, 
                               hide_index=True,
                               column_config={
                                   "Nombre": st.column_config.TextColumn("Investigador", width="medium"),
                                   "Afiliación": st.column_config.TextColumn("Institución", width="large"),
                                   "Total Publicaciones": st.column_config.NumberColumn("Publicaciones", width="small")
                               })
                    st.markdown("### 📊 Estadísticas del Equipo")
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    with col_stat1:
                        st.metric("👥 Total Autores", len(authors))
                    with col_stat2:
                        institutions = df_authors['Afiliación'].nunique()
                        st.metric("🏛️ Instituciones", institutions)
                    with col_stat3:
                        avg_pubs = df_authors['Total Publicaciones'].mean()
                        st.metric("📚 Prom. Publicaciones", f"{avg_pubs:.1f}")
                else:
                    st.info("👥 No se encontraron autores para este artículo")
            else:
                st.info("👆 Seleccione un artículo para ver su equipo de investigación")