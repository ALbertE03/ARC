import streamlit as st
import networkx as nx
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
import json
# Función para visualizar el grafo (importada desde main.py)
def create_graph_visualization(graph, selected_nodes=None):
    """Crea una visualización interactiva del grafo usando Plotly"""
    if len(graph.nodes()) == 0:
        return go.Figure()
    
    # Calcular posiciones usando spring layout
    pos = nx.spring_layout(graph, k=1, iterations=50)
    
    # Separar nodos por tipo
    author_nodes = [n for n, d in graph.nodes(data=True) if d.get('type') == 'author']
    article_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'article']
    
    # Crear trazas para aristas
    edge_x = []
    edge_y = []
    for edge in graph.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Crear trazas para nodos de autores
    author_x = []
    author_y = []
    author_text = []
    author_colors = []
    
    for node in author_nodes:
        if node in pos:
            x, y = pos[node]
            author_x.append(x)
            author_y.append(y)
            
            # Información del nodo
            node_data = graph.nodes[node]
            display_name = node_data.get('display_name', str(node))
            author_text.append(f"Autor: {display_name}")
            
            # Color basado en si está seleccionado
            if selected_nodes and node in selected_nodes:
                author_colors.append('red')
            else:
                author_colors.append('lightblue')
    
    author_trace = go.Scatter(
        x=author_x, y=author_y,
        mode='markers+text',
        text=author_text,
        textposition="middle center",
        hoverinfo='text',
        marker=dict(
            size=15,
            color=author_colors,
            line=dict(width=2, color='black')
        ),
        name='Autores'
    )
    
    # Crear trazas para nodos de artículos
    article_x = []
    article_y = []
    article_text = []
    
    for node in article_nodes:
        if node in pos:
            x, y = pos[node]
            article_x.append(x)
            article_y.append(y)
            
            # Información del nodo
            node_data = graph.nodes[node]
            display_name = node_data.get('display_name', str(node))
            # Truncar título si es muy largo
            if len(display_name) > 30:
                display_name = display_name[:30] + "..."
            article_text.append(f"Artículo: {display_name}")
    
    article_trace = go.Scatter(
        x=article_x, y=article_y,
        mode='markers',
        hoverinfo='text',
        text=article_text,
        marker=dict(
            size=8,
            color='lightgreen',
            line=dict(width=1, color='black')
        ),
        name='Artículos'
    )
    
    # Crear la figura
    fig = go.Figure(data=[edge_trace, author_trace, article_trace],
                   layout=go.Layout(
                        title='Red de Colaboración Académica',
                        titlefont_size=16,
                        showlegend=True,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        annotations=[ dict(
                            text="",
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002 ) ],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        height=600
                    ))
    
    return fig

def show_overview():
    """Muestra la página de vista general con análisis completos"""
    # Header profesional
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; text-align: center; margin: 0;">
            🚀 Red de Colaboración Académica - Panel de Control
        </h1>
        <p style="color: white; text-align: center; margin: 0.5rem 0 0 0; font-size: 1.2rem;">
            Análisis de Redes de Investigación UH
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    show_executive_summary()
    
    st.markdown("### 🎯 Centro de Análisis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🌐 Red Completa\n(Investigadores + Publicaciones)", 
                    use_container_width=True, type="primary"):
            st.session_state.analysis_type = "complete"
    with col2:
        if st.button("🤝 Red de Colaboración\n(Solo Investigadores)", 
                    use_container_width=True):
            st.session_state.analysis_type = "collaboration"
    with col3:
        if st.button("📊 Análisis Comparativo\n(Métricas Avanzadas)", 
                    use_container_width=True):
            st.session_state.analysis_type = "comparative"
    
    # Mostrar análisis basado en selección
    analysis_type = getattr(st.session_state, 'analysis_type', 'complete')
    
    if analysis_type == "complete":
        show_mixed_graph_analysis()
    elif analysis_type == "collaboration":
        show_author_collaboration_analysis()
    else:
        show_comparative_analysis()

def show_executive_summary():
    """Muestra un resumen ejecutivo con métricas clave"""
    graph = st.session_state.graph
    
    # Calcular métricas principales
    num_authors = len([n for n, d in graph.nodes(data=True) if d.get('node_type') == 'author'])
    num_articles = len([n for n, d in graph.nodes(data=True) if d.get('node_type') == 'article'])
    total_connections = len(graph.edges())
    network_density = nx.density(graph)
    
    # Calcular métricas adicionales
    author_productivity = []
    collaboration_strength = []
    
    for node, data in graph.nodes(data=True):
        if data.get('node_type') == 'author':
            publications = len([n for n in graph.neighbors(node) 
                              if graph.nodes[n].get('node_type') == 'article'])
            author_productivity.append(publications)
    
    for node, data in graph.nodes(data=True):
        if data.get('node_type') == 'article':
            coauthors = len([n for n in graph.neighbors(node) 
                           if graph.nodes[n].get('node_type') == 'author'])
            collaboration_strength.append(coauthors)
    
    avg_productivity = np.mean(author_productivity) if author_productivity else 0
    avg_collaboration = np.mean(collaboration_strength) if collaboration_strength else 0
       
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="👥 Investigadores",
            value=f"{num_authors:,}",
            delta=f"Activos en la red"
        )
    
    with col2:
        st.metric(
            label="📄 Publicaciones",
            value=f"{num_articles:,}",
            delta=f"Documentos analizados"
        )
    
    with col3:
        st.metric(
            label="🔗 Conexiones",
            value=f"{total_connections:,}",
            delta=f"Vínculos identificados"
        )
    
    with col4:
        st.metric(
            label="📈 Productividad Media",
            value=f"{avg_productivity:.1f}",
            delta="Pubs/Investigador"
        )
    
    with col5:
        st.metric(
            label="🤝 Colaboración Media",
            value=f"{avg_collaboration:.1f}",
            delta="Coautores/Publicación"
        )
    
    
    # Crear dashboard de métricas
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Gráfico combinado de métricas
        fig = create_kpi_dashboard(graph, author_productivity, collaboration_strength)
        st.plotly_chart(fig, use_container_width=True)
 

def create_kpi_dashboard(graph, author_productivity, collaboration_strength):
    """Crea un dashboard visual con métricas clave"""
    from plotly.subplots import make_subplots
    
    # Crear subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Distribución de Productividad', 'Tendencia de Colaboración', 
                       ),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": True}]]
    )
    
    if author_productivity:
        productivity_hist = np.histogram(author_productivity, bins=min(20, len(set(author_productivity))))
        fig.add_trace(
            go.Bar(x=productivity_hist[1][:-1], y=productivity_hist[0], 
                   name="Productividad", marker_color='#667eea'),
            row=1, col=1
        )

    if collaboration_strength:
        collab_hist = np.histogram(collaboration_strength, bins=min(15, len(set(collaboration_strength))))
        fig.add_trace(
            go.Bar(x=collab_hist[1][:-1], y=collab_hist[0], 
                   name="Colaboración", marker_color='#764ba2'),
            row=1, col=2
        )
    
    # Gráfico 3: Métricas de conectividad
    if len(graph.nodes()) > 0:
        degrees = [graph.degree(n) for n in graph.nodes()]
        degree_dist = np.histogram(degrees, bins=min(10, len(set(degrees))))
        fig.add_trace(
            go.Scatter(x=degree_dist[1][:-1], y=degree_dist[0], 
                      mode='lines+markers', name="Conectividad", 
                      line=dict(color='#f093fb')),
            row=2, col=1
        )
    
   
    
    fig.update_layout(
        height=600,
        title_text="Dashboard de Métricas de Red",
        title_x=0.5,
        showlegend=True,
        template="plotly_white"
    )
    
    return fig

def show_mixed_graph_analysis():
    """Análisis del grafo mixto autor-artículo con visualizaciones avanzadas"""
    st.markdown("### 🌐 Análisis Completo de la Red de Investigación")
    
    graph = st.session_state.graph
    
    # Panel de control interactivo
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Visualización principal mejorada
        st.markdown("#### 🎨 Visualización Interactiva de la Red")
        
        # Opciones de visualización
        viz_options = st.columns(3)
        with viz_options[0]:
            show_labels = st.checkbox("Mostrar etiquetas", value=False)
        with viz_options[1]:
            layout_type = st.selectbox("Algoritmo de layout", 
                                     ["spring", "circular", "kamada_kawai", "shell"])
        with viz_options[2]:
            node_size_metric = st.selectbox("Tamaño de nodo basado en", 
                                          ["grado", "h_index", "citaciones"])
        
        if st.button("� Generar Visualización Avanzada", type="primary", use_container_width=True):
            with st.spinner("Creando visualización profesional de la red..."):
                fig = create_advanced_graph_visualization(
                    graph, layout_type, show_labels, node_size_metric
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Panel de métricas dinámicas
        st.markdown("#### � Métricas en Tiempo Real")
        show_dynamic_metrics_panel(graph)
    
    # Análisis de productividad mejorado
    st.markdown("### 📈 Centro de Análisis de Productividad")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Rankings de Impacto", 
        "📚 Análisis de Colaboración", 
        "🔍 Patrones Temporales",
        "🌍 Análisis Geográfico"
    ])
    
    with tab1:
        show_impact_rankings(graph)
    
    with tab2:
        show_collaboration_analysis_enhanced(graph)
    
    with tab3:
        show_temporal_patterns(graph)
    
    with tab4:
        show_geographic_analysis(graph)
    
    with tab1:
        # Top investigadores por número de publicaciones
        author_productivity = []
        for node, data in graph.nodes(data=True):
            if data.get('node_type') == 'author':
                publications = len([n for n in graph.neighbors(node) 
                                  if graph.nodes[n].get('node_type') == 'article'])
                author_productivity.append({
                    'Investigador': data.get('display_name', node),
                    'Institución': data.get('affiliation', 'N/A'),
                    'Publicaciones': publications,
                    'H-Index': data.get('h_index', 0)
                })
        
        if author_productivity:
            productivity_df = pd.DataFrame(author_productivity)
            productivity_df = productivity_df.sort_values('Publicaciones', ascending=False)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 🥇 Top 10 Más Productivos")
                st.dataframe(productivity_df.head(10), use_container_width=True)
            
            with col2:
                if len(productivity_df) > 0:
                    fig = px.bar(
                        productivity_df.head(10), 
                        x='Investigador', 
                        y='Publicaciones',
                        title="Productividad por Investigador",
                        color='H-Index',
                        color_continuous_scale="Viridis"
                    )
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Artículos con más coautores
        article_collaboration = []
        for node, data in graph.nodes(data=True):
            if data.get('node_type') == 'article':
                coauthors = len([n for n in graph.neighbors(node) 
                               if graph.nodes[n].get('node_type') == 'author'])
                article_collaboration.append({
                    'Título': data.get('display_name', node)[:50] + "..." if len(data.get('display_name', node)) > 50 else data.get('display_name', node),
                    'Año': data.get('publication_year', 'N/A'),
                    'Revista': data.get('journal', 'N/A'),
                    'Co-autores': coauthors,
                    'Citas': data.get('citation_count', 0)
                })
        
        if article_collaboration:
            collaboration_df = pd.DataFrame(article_collaboration)
            collaboration_df = collaboration_df.sort_values('Co-autores', ascending=False)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 🤝 Publicaciones Más Colaborativas")
                st.dataframe(collaboration_df.head(10), use_container_width=True)
            
            with col2:
                if len(collaboration_df) > 0:
                    fig = px.scatter(
                        collaboration_df,
                        x='Co-autores',
                        y='Citas',
                        size='Co-autores',
                        hover_data=['Título', 'Año'],
                        title="Colaboración vs Impacto"
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribución de publicaciones por investigador
            if author_productivity:
                pub_counts = [item['Publicaciones'] for item in author_productivity if item['Publicaciones'] > 0]
                if pub_counts:
                    fig = px.histogram(
                        x=pub_counts,
                        nbins=min(20, len(set(pub_counts))),
                        title="Distribución de Productividad",
                        labels={'x': 'Número de Publicaciones', 'y': 'Investigadores'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Distribución de coautores por artículo
            if article_collaboration:
                coauthor_counts = [item['Co-autores'] for item in article_collaboration if item['Co-autores'] > 0]
                if coauthor_counts:
                    fig = px.histogram(
                        x=coauthor_counts,
                        nbins=min(15, len(set(coauthor_counts))),
                        title="Distribución de Colaboración",
                        labels={'x': 'Número de Co-autores', 'y': 'Publicaciones'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

def show_author_collaboration_analysis():
    """Análisis específico de la red de colaboración autor-autor"""
    st.markdown("### 🤝 Análisis de Red de Colaboración")
    
    if st.session_state.author_graph is None:
        st.warning("⚠️ No se pudo cargar el grafo de colaboración autor-autor. Generando desde red mixta...")
        # Crear grafo autor-autor temporal desde el grafo mixto
        mixed_graph = st.session_state.graph
        temp_author_graph = create_author_projection(mixed_graph)
        if temp_author_graph:
            analyze_collaboration_network(temp_author_graph, is_temporary=True)
        return
    
    author_graph = st.session_state.author_graph
    analyze_collaboration_network(author_graph, is_temporary=False)

def create_author_projection(mixed_graph):
    """Crea una proyección autor-autor desde el grafo mixto"""
    try:
        # Identificar nodos de autores y artículos
        authors = [n for n, d in mixed_graph.nodes(data=True) if d.get('node_type') == 'author']
        articles = [n for n, d in mixed_graph.nodes(data=True) if d.get('node_type') == 'article']
        
        if len(authors) < 2:
            return None
        
        # Crear grafo autor-autor
        author_graph = nx.Graph()
        
        # Agregar nodos de autores
        for author in authors:
            author_data = mixed_graph.nodes[author]
            author_graph.add_node(author, **author_data)
        
        # Crear conexiones entre autores que comparten artículos
        for article in articles:
            article_authors = [n for n in mixed_graph.neighbors(article) if n in authors]
            # Conectar cada par de autores del mismo artículo
            for i, author1 in enumerate(article_authors):
                for author2 in article_authors[i+1:]:
                    if author_graph.has_edge(author1, author2):
                        # Incrementar peso de la conexión
                        author_graph[author1][author2]['weight'] = author_graph[author1][author2].get('weight', 0) + 1
                        author_graph[author1][author2]['shared_articles'] = author_graph[author1][author2].get('shared_articles', []) + [article]
                    else:
                        # Crear nueva conexión
                        author_graph.add_edge(author1, author2, weight=1, shared_articles=[article])
        
        return author_graph
    
    except Exception as e:
        st.error(f"Error creando proyección autor-autor: {e}")
        return None

def analyze_collaboration_network(author_graph, is_temporary=False):
    """Analiza la red de colaboración entre autores"""
    
    if is_temporary:
        st.info("📊 Análisis generado desde el grafo mixto (proyección temporal)")
    else:
        st.success("🔗 Usando grafo de colaboración autor-autor especializado")
    
    # Métricas básicas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Investigadores", len(author_graph.nodes()))
        
    with col2:
        st.metric("🤝 Colaboraciones", len(author_graph.edges()))
        
    with col3:
        density = nx.density(author_graph)
        st.metric("📊 Densidad", f"{density:.3f}")
        
    with col4:
        components = nx.number_connected_components(author_graph)
        st.metric("🔍 Grupos", components)
    
    # Análisis de colaboraciones
    st.markdown("### 🔍 Análisis de Patrones de Colaboración")
    
    tab1, tab2, tab3 = st.tabs(["🌟 Investigadores Clave", "🎯 Análisis de Influencia", "👥 Comunidades"])
    
    with tab1:
        show_key_researchers(author_graph)
    
    with tab2:
        show_influence_analysis(author_graph)
    
    with tab3:
        show_communities_analysis(author_graph)

def show_key_researchers(author_graph):
    """Muestra investigadores clave basado en diferentes métricas"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔗 Más Colaborativos")
        # Investigadores con más colaboraciones
        degree_centrality = nx.degree_centrality(author_graph)
        top_collaborative = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10]
        
        collab_data = []
        for node, centrality in top_collaborative:
            node_data = author_graph.nodes[node]
            collab_data.append({
                'Investigador': node_data.get('display_name', node),
                'Institución': node_data.get('affiliation', 'N/A'),
                'Colaboraciones': author_graph.degree(node),
                'Centralidad': f"{centrality:.3f}"
            })
        
        if collab_data:
            st.dataframe(pd.DataFrame(collab_data), use_container_width=True)
    
    with col2:
        st.markdown("#### 🌉 Conectores Clave")
        # Investigadores que conectan diferentes grupos (betweenness centrality)
        if len(author_graph.nodes()) < 500:  # Solo para grafos no muy grandes
            betweenness = nx.betweenness_centrality(author_graph)
            top_bridges = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:10]
            
            bridge_data = []
            for node, centrality in top_bridges:
                if centrality > 0:  # Solo mostrar quienes realmente conectan
                    node_data = author_graph.nodes[node]
                    bridge_data.append({
                        'Investigador': node_data.get('display_name', node),
                        'Institución': node_data.get('affiliation', 'N/A'),
                        'Importancia': f"{centrality:.3f}",
                        'Rol': "Conector" if centrality > 0.1 else "Intermediario"
                    })
            
            if bridge_data:
                st.dataframe(pd.DataFrame(bridge_data), use_container_width=True)
            else:
                st.info("Calculando conectores clave...")
        else:
            st.info("Red muy grande - análisis disponible bajo demanda")

def show_influence_analysis(author_graph):
    """Análisis de influencia en la red"""
    
    st.markdown("#### 🎯 Investigadores con Mayor Influencia")
    
    # Calcular diferentes métricas de influencia
    metrics_to_calculate = st.multiselect(
        "Selecciona las métricas a calcular:",
        ["🔗 Grado (Colaboraciones directas)", 
         "🌉 Intermediación (Rol de conector)",
         "📍 Cercanía (Acceso a la red)",
         "⭐ Vector Propio (Influencia ponderada)"],
        default=["🔗 Grado (Colaboraciones directas)"]
    )
    
    if st.button("📊 Calcular Métricas de Influencia", type="primary"):
        influence_data = []
        
        # Obtener datos básicos de nodos
        for node in author_graph.nodes():
            node_data = author_graph.nodes[node]
            researcher_info = {
                'ID': node,
                'Investigador': node_data.get('display_name', node),
                'Institución': node_data.get('affiliation', 'N/A'),
                'H-Index': node_data.get('h_index', 0)
            }
            influence_data.append(researcher_info)
        
        influence_df = pd.DataFrame(influence_data)
        
        with st.spinner("Calculando métricas de influencia..."):
            # Calcular métricas seleccionadas
            if "🔗 Grado (Colaboraciones directas)" in metrics_to_calculate:
                degree_cent = nx.degree_centrality(author_graph)
                influence_df['Grado'] = influence_df['ID'].map(degree_cent)
            
            if "🌉 Intermediación (Rol de conector)" in metrics_to_calculate:
                if len(author_graph.nodes()) < 500:
                    between_cent = nx.betweenness_centrality(author_graph)
                else:
                    between_cent = nx.betweenness_centrality(author_graph, k=100)
                influence_df['Intermediación'] = influence_df['ID'].map(between_cent)
            
            if "📍 Cercanía (Acceso a la red)" in metrics_to_calculate:
                if nx.is_connected(author_graph):
                    close_cent = nx.closeness_centrality(author_graph)
                    influence_df['Cercanía'] = influence_df['ID'].map(close_cent)
                else:
                    st.warning("La red no está completamente conectada. Calculando cercanía por componentes.")
                    close_cent = {}
                    for component in nx.connected_components(author_graph):
                        subgraph = author_graph.subgraph(component)
                        component_closeness = nx.closeness_centrality(subgraph)
                        close_cent.update(component_closeness)
                    influence_df['Cercanía'] = influence_df['ID'].map(close_cent)
            
            if "⭐ Vector Propio (Influencia ponderada)" in metrics_to_calculate:
                try:
                    eigen_cent = nx.eigenvector_centrality(author_graph, max_iter=1000)
                    influence_df['Vector Propio'] = influence_df['ID'].map(eigen_cent)
                except:
                    st.warning("No se pudo calcular centralidad de vector propio. Usando grado como alternativa.")
                    influence_df['Vector Propio'] = influence_df['ID'].map(nx.degree_centrality(author_graph))
        
        # Mostrar resultados
        st.markdown("#### 📋 Resultados del Análisis")
        
        # Remover columna ID para mostrar
        display_df = influence_df.drop('ID', axis=1)
        
        # Ordenar por la primera métrica calculada
        if len(metrics_to_calculate) > 0:
            metric_name = metrics_to_calculate[0].split(' ')[1]  # Extraer nombre simple
            metric_columns = [col for col in display_df.columns if metric_name.lower() in col.lower()]
            if metric_columns:
                display_df = display_df.sort_values(metric_columns[0], ascending=False)
        
        st.dataframe(display_df.head(15), use_container_width=True)

def show_communities_analysis(author_graph):
    """Análisis de comunidades en la red de colaboración"""
    
    st.markdown("#### 👥 Detección de Comunidades de Investigación")
    
    if len(author_graph.nodes()) < 3:
        st.warning("Se necesitan al menos 3 investigadores para detectar comunidades")
        return
    
    if st.button("🔍 Detectar Comunidades", type="primary"):
        with st.spinner("Detectando comunidades de investigación..."):
            try:
                communities = list(nx.community.greedy_modularity_communities(author_graph))
                modularity = nx.community.modularity(author_graph, communities)
                
                # Mostrar resultados
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("🏘️ Comunidades Encontradas", len(communities))
                with col2:
                    st.metric("📊 Modularidad", f"{modularity:.3f}")
                with col3:
                    sizes = [len(comm) for comm in communities]
                    st.metric("👥 Comunidad Más Grande", max(sizes) if sizes else 0)
                
                # Análisis detallado de comunidades
                st.markdown("#### 🔍 Análisis Detallado de Comunidades")
                
                community_analysis = []
                for i, community in enumerate(communities):
                    community_members = list(community)
                    
                    # Información básica de la comunidad
                    institutions = []
                    h_indices = []
                    
                    for member in community_members:
                        member_data = author_graph.nodes[member]
                        if member_data.get('affiliation'):
                            institutions.append(member_data['affiliation'])
                        if member_data.get('h_index'):
                            h_indices.append(member_data['h_index'])
                    
                    # Institución más común
                    most_common_institution = "Mixta"
                    if institutions:
                        institution_counts = pd.Series(institutions).value_counts()
                        if len(institution_counts) > 0 and institution_counts.iloc[0] > len(community_members) * 0.5:
                            most_common_institution = institution_counts.index[0]
                    
                    community_analysis.append({
                        'Comunidad': f"Grupo {i+1}",
                        'Miembros': len(community_members),
                        'Institución Principal': most_common_institution,
                        'H-Index Promedio': np.mean(h_indices) if h_indices else 0,
                        'Conexiones Internas': len([edge for edge in author_graph.edges() 
                                                   if edge[0] in community and edge[1] in community])
                    })
                
                # Mostrar tabla de comunidades
                community_df = pd.DataFrame(community_analysis)
                community_df = community_df.sort_values('Miembros', ascending=False)
                st.dataframe(community_df, use_container_width=True)
            
            except Exception as e:
                st.error(f"Error en la detección de comunidades: {e}")

def show_comparative_analysis():
    """Análisis comparativo entre ambos grafos"""
    st.markdown("### 📊 Análisis Comparativo de Redes")
    
    mixed_graph = st.session_state.graph
    author_graph = st.session_state.author_graph
    
    if author_graph is None:
        st.warning("⚠️ Grafo autor-autor no disponible. Generando proyección temporal...")
        author_graph = create_author_projection(mixed_graph)
        if author_graph is None:
            st.error("No se pudo generar la proyección autor-autor")
            return
    
    # Comparación de métricas básicas
    st.markdown("#### 🔍 Comparación de Estructuras")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 🌐 Red Completa (Investigadores + Publicaciones)")
        mixed_authors = len([n for n, d in mixed_graph.nodes(data=True) if d.get('node_type') == 'author'])
        mixed_articles = len([n for n, d in mixed_graph.nodes(data=True) if d.get('node_type') == 'article'])
        
        st.metric("👥 Investigadores", mixed_authors)
        st.metric("📄 Publicaciones", mixed_articles)
        st.metric("🔗 Conexiones Totales", len(mixed_graph.edges()))
        st.metric("📊 Densidad", f"{nx.density(mixed_graph):.4f}")
    
    with col2:
        st.markdown("##### 🤝 Red de Colaboración (Solo Investigadores)")
        st.metric("👥 Investigadores", len(author_graph.nodes()))
        st.metric("🤝 Colaboraciones", len(author_graph.edges()))
        st.metric("📊 Densidad", f"{nx.density(author_graph):.4f}")
        st.metric("🌐 Componentes", nx.number_connected_components(author_graph))
    
    # Análisis de conectividad
    st.markdown("#### 🎯 Análisis de Conectividad")
    
    # Investigadores en ambas redes
    mixed_authors_set = set([n for n, d in mixed_graph.nodes(data=True) if d.get('node_type') == 'author'])
    collab_authors_set = set(author_graph.nodes())
    
    common_authors = mixed_authors_set.intersection(collab_authors_set)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("👥 Investigadores Comunes", len(common_authors))
    with col2:
        st.metric("📄 Solo en Red Completa", len(mixed_authors_set - collab_authors_set))
    with col3:
        st.metric("🤝 Solo en Red Colaboración", len(collab_authors_set - mixed_authors_set))

def create_advanced_graph_visualization(graph, layout_type, show_labels, node_size_metric):
    """Crea una visualización avanzada del grafo con opciones personalizables"""
    if len(graph.nodes()) == 0:
        return go.Figure()
    
    # Calcular posiciones según el layout seleccionado
    if layout_type == "spring":
        pos = nx.spring_layout(graph, k=2, iterations=100)
    elif layout_type == "circular":
        pos = nx.circular_layout(graph)
    elif layout_type == "kamada_kawai":
        pos = nx.kamada_kawai_layout(graph)
    elif layout_type == "shell":
        # Separar nodos por tipo para shell layout
        authors = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'author']
        articles = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'article']
        shells = [authors, articles] if authors and articles else [list(graph.nodes())]
        pos = nx.shell_layout(graph, nlist=shells)
    else:
        pos = nx.spring_layout(graph, k=1, iterations=50)
    
    # Separar nodos por tipo
    author_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'author']
    article_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'article']
    
    # Crear trazas para aristas con gradiente
    edge_x, edge_y = [], []
    edge_weights = []
    
    for edge in graph.edges():
        if edge[0] in pos and edge[1] in pos:
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            # Peso de la arista (para grosor)
            weight = graph[edge[0]][edge[1]].get('weight', 1)
            edge_weights.extend([weight, weight, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color='rgba(125,125,125,0.5)'),
        hoverinfo='none',
        mode='lines',
        name='Conexiones'
    )
    
    # Función para calcular tamaño de nodo
    def get_node_size(node, metric):
        node_data = graph.nodes[node]
        if metric == "grado":
            return min(max(graph.degree(node) * 2, 8), 50)
        elif metric == "h_index":
            return min(max(node_data.get('h_index', 0) * 1.5, 8), 50)
        elif metric == "citaciones":
            return min(max(node_data.get('citation_count', 0) / 10, 8), 50)
        return 15
    
    # Crear trazas para nodos de autores con colores mejorados
    author_x, author_y, author_text, author_colors, author_sizes = [], [], [], [], []
    
    for node in author_nodes:
        if node in pos:
            x, y = pos[node]
            author_x.append(x)
            author_y.append(y)
            
            node_data = graph.nodes[node]
            display_name = node_data.get('display_name', str(node))
            h_index = node_data.get('h_index', 0)
            affiliation = node_data.get('affiliation', 'N/A')
            
            # Texto del hover mejorado
            hover_text = f"<b>{display_name}</b><br>"
            hover_text += f"H-Index: {h_index}<br>"
            hover_text += f"Institución: {affiliation}<br>"
            hover_text += f"Conexiones: {graph.degree(node)}"
            author_text.append(hover_text)
            
            # Color basado en h-index
            if h_index > 20:
                author_colors.append('#FF6B6B')  # Rojo para alto impacto
            elif h_index > 10:
                author_colors.append('#4ECDC4')  # Verde para impacto medio
            else:
                author_colors.append('#45B7D1')  # Azul para otros
            
            author_sizes.append(get_node_size(node, node_size_metric))
    
    author_trace = go.Scatter(
        x=author_x, y=author_y,
        mode='markers+text' if show_labels else 'markers',
        text=[node_data.get('display_name', str(node))[:10] + "..." 
              if len(node_data.get('display_name', str(node))) > 10 
              else node_data.get('display_name', str(node)) 
              for node in author_nodes if node in pos] if show_labels else None,
        textposition="top center",
        hoverinfo='text',
        hovertext=author_text,
        marker=dict(
            size=author_sizes,
            color=author_colors,
            line=dict(width=2, color='white'),
            opacity=0.8
        ),
        name='Investigadores'
    )
    
    # Crear trazas para artículos
    article_x, article_y, article_text, article_sizes = [], [], [], []
    
    for node in article_nodes:
        if node in pos:
            x, y = pos[node]
            article_x.append(x)
            article_y.append(y)
            
            node_data = graph.nodes[node]
            display_name = node_data.get('display_name', str(node))
            year = node_data.get('publication_year', 'N/A')
            citations = node_data.get('citation_count', 0)
            
            hover_text = f"<b>{display_name[:50]}...</b><br>"
            hover_text += f"Año: {year}<br>"
            hover_text += f"Citas: {citations}<br>"
            hover_text += f"Co-autores: {graph.degree(node)}"
            article_text.append(hover_text)
            
            article_sizes.append(get_node_size(node, "citaciones"))
    
    article_trace = go.Scatter(
        x=article_x, y=article_y,
        mode='markers',
        hoverinfo='text',
        hovertext=article_text,
        marker=dict(
            size=article_sizes,
            color='#FFA07A',
            symbol='diamond',
            line=dict(width=1, color='white'),
            opacity=0.7
        ),
        name='Publicaciones'
    )
    
    # Crear la figura con diseño mejorado
    fig = go.Figure(data=[edge_trace, author_trace, article_trace])
    
    fig.update_layout(
        title=dict(
            text='Red de Colaboración Académica - Vista Avanzada',
            x=0.5,
            font=dict(size=20, color='#2C3E50')
        ),
        showlegend=True,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=60),
        annotations=[
            dict(
                text=f"Layout: {layout_type.title()} | Nodos: {len(graph.nodes())} | Conexiones: {len(graph.edges())}",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor='left', yanchor='bottom',
                font=dict(color='gray', size=12)
            )
        ],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        height=700,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def show_dynamic_metrics_panel(graph):
    """Panel de métricas dinámicas"""
    # Métricas básicas
    num_authors = len([n for n, d in graph.nodes(data=True) if d.get('node_type') == 'author'])
    num_articles = len([n for n, d in graph.nodes(data=True) if d.get('node_type') == 'article'])
    
    st.metric("👥 Investigadores", f"{num_authors:,}")
    st.metric("📄 Publicaciones", f"{num_articles:,}")
    st.metric("🔗 Conexiones", f"{len(graph.edges()):,}")
    
    # Densidad con indicador visual
    density = nx.density(graph)
    if density > 0.1:
        density_color = "🟢"
    elif density > 0.05:
        density_color = "🟡"
    else:
        density_color = "🔴"
    
    st.metric("📊 Densidad", f"{density:.4f}", delta=f"{density_color}")
    
    # Gráfico de distribución de grados
    degrees = [graph.degree(n) for n in graph.nodes()]
    if degrees:
        fig_degree = px.histogram(
            x=degrees, 
            nbins=min(20, len(set(degrees))),
            title="Distribución de Conexiones",
            labels={'x': 'Grado', 'y': 'Frecuencia'}
        )
        fig_degree.update_layout(height=200, margin=dict(t=30, b=30))
        st.plotly_chart(fig_degree, use_container_width=True)

def show_impact_rankings(graph):
    """Muestra rankings de impacto con visualizaciones mejoradas"""
    st.markdown("#### 🏆 Rankings de Alto Impacto")
    
    # Recopilar datos de investigadores
    researcher_data = []
    for node, data in graph.nodes(data=True):
        if data.get('node_type') == 'author':
            publications = len([n for n in graph.neighbors(node) 
                              if graph.nodes[n].get('node_type') == 'article'])
            
            # Calcular citas totales
            total_citations = 0
            for neighbor in graph.neighbors(node):
                if graph.nodes[neighbor].get('node_type') == 'article':
                    total_citations += graph.nodes[neighbor].get('citation_count', 0)
            try:
                s = data.get("summary_stats", {} )
                d = json.loads(s)
            except:
                d = {'h_index': 0}
            researcher_data.append({
                'Investigador': data.get('display_name', node),
                'Institución': data.get('affiliation', 'N/A'),
                'Publicaciones': publications,
                'H-Index': d['h_index'],
                'Citas Totales': total_citations,
                'Impacto Promedio': total_citations / publications if publications > 0 else 0
            })
    
    if researcher_data:
        df = pd.DataFrame(researcher_data)
        
        # Crear tabs para diferentes rankings
        rank_tab1, rank_tab2, rank_tab3 = st.tabs([
            "📈 Por H-Index", "📊 Por Publicaciones", "⭐ Por Impacto"
        ])
        
        with rank_tab1:
            df_h = df.sort_values('H-Index', ascending=False).head(15)
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.dataframe(df_h[['Investigador', 'Institución', 'H-Index']], 
                           use_container_width=True)
            
            with col2:
                fig = px.bar(df_h.head(10), 
                           x='H-Index', y='Investigador',
                           title="Top 10 por H-Index",
                           orientation='h',
                           color='H-Index',
                           color_continuous_scale='Viridis')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with rank_tab2:
            df_pub = df.sort_values('Publicaciones', ascending=False).head(15)
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.dataframe(df_pub[['Investigador', 'Institución', 'Publicaciones']], 
                           use_container_width=True)
            
            with col2:
                fig = px.scatter(df_pub, 
                               x='Publicaciones', y='H-Index',
                               size='Citas Totales',
                               hover_data=['Investigador'],
                               title="Productividad vs Impacto",
                               color='Impacto Promedio',
                               color_continuous_scale='Plasma')
                st.plotly_chart(fig, use_container_width=True)
        
        with rank_tab3:
            df_impact = df.sort_values('Impacto Promedio', ascending=False).head(15)
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.dataframe(df_impact[['Investigador', 'Institución', 'Impacto Promedio']], 
                           use_container_width=True)
            
            with col2:
                # Crear gráfico de burbujas
                fig = px.scatter(df_impact, 
                               x='Publicaciones', y='Impacto Promedio',
                               size='H-Index',
                               hover_data=['Investigador', 'Citas Totales'],
                               title="Calidad vs Cantidad",
                               color='H-Index',
                               color_continuous_scale='RdYlBu_r')
                st.plotly_chart(fig, use_container_width=True)

def show_collaboration_analysis_enhanced(graph):
    """Análisis de colaboración mejorado"""
    st.markdown("#### 🤝 Análisis Avanzado de Colaboración")
    
    # Recopilar datos de colaboración
    collaboration_data = []
    for node, data in graph.nodes(data=True):
        if data.get('node_type') == 'article':
            coauthors = [n for n in graph.neighbors(node) 
                        if graph.nodes[n].get('node_type') == 'author']
            
            if len(coauthors) > 1:  # Solo artículos colaborativos
                collaboration_data.append({
                    'Título': data.get('display_name', node)[:60] + "...",
                    'Año': data.get('publication_year', 'N/A'),
                    'Co-autores': len(coauthors),
                    'Citas': data.get('citation_count', 0),
                    'Revista': data.get('journal', 'N/A'),
                    'Factor de Colaboración': len(coauthors) * data.get('citation_count', 0)
                })
    
    if collaboration_data:
        df_collab = pd.DataFrame(collaboration_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Top colaboraciones
            df_top = df_collab.sort_values('Factor de Colaboración', ascending=False).head(10)
            st.markdown("##### 🌟 Colaboraciones Más Exitosas")
            st.dataframe(df_top[['Título', 'Co-autores', 'Citas']], use_container_width=True)
        
        with col2:
            # Gráfico de colaboración vs impacto
            fig = px.scatter(df_collab,
                           x='Co-autores', y='Citas',
                           size='Factor de Colaboración',
                           color='Año',
                           title="Colaboración vs Impacto",
                           hover_data=['Título'])
            st.plotly_chart(fig, use_container_width=True)
        
        # Análisis temporal de colaboración
        st.markdown("##### 📈 Evolución de la Colaboración")
        
        # Agrupar por año
        yearly_collab = df_collab.groupby('Año').agg({
            'Co-autores': 'mean',
            'Citas': 'mean',
            'Título': 'count'
        }).reset_index()
        yearly_collab.columns = ['Año', 'Promedio Co-autores', 'Promedio Citas', 'Número Publicaciones']
        
        if len(yearly_collab) > 1:
            fig_trend = px.line(yearly_collab, x='Año', y='Promedio Co-autores',
                              title="Tendencia de Colaboración por Año")
            fig_trend.add_scatter(x=yearly_collab['Año'], y=yearly_collab['Promedio Citas'],
                                mode='lines', name='Promedio Citas', yaxis='y2')
            
            fig_trend.update_layout(
                yaxis2=dict(overlaying='y', side='right', title='Promedio Citas'),
                yaxis=dict(title='Promedio Co-autores')
            )
            st.plotly_chart(fig_trend, use_container_width=True)

def show_temporal_patterns(graph):
    """Análisis de patrones temporales"""
    st.markdown("#### ⏰ Patrones Temporales de Investigación")
    
    # Recopilar datos temporales
    temporal_data = []
    for node, data in graph.nodes(data=True):
        if data.get('node_type') == 'article':
            year = data.get('publication_year')
            if year and year != 'N/A':
                try:
                    year = int(year)
                    if 2000 <= year <= 2024:  # Filtrar años válidos
                        coauthors = len([n for n in graph.neighbors(node) 
                                       if graph.nodes[n].get('node_type') == 'author'])
                        temporal_data.append({
                            'Año': year,
                            'Citas': data.get('citation_count', 0),
                            'Co-autores': coauthors,
                            'Revista': data.get('journal', 'N/A')
                        })
                except ValueError:
                    continue
    
    if temporal_data:
        df_temporal = pd.DataFrame(temporal_data)
        
        # Análisis por año
        yearly_stats = df_temporal.groupby('Año').agg({
            'Citas': ['count', 'sum', 'mean'],
            'Co-autores': 'mean'
        }).round(2)
        
        yearly_stats.columns = ['Publicaciones', 'Citas Totales', 'Citas Promedio', 'Colaboración Promedio']
        yearly_stats = yearly_stats.reset_index()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Evolución de publicaciones
            fig1 = px.bar(yearly_stats, x='Año', y='Publicaciones',
                         title="Evolución de Publicaciones por Año",
                         color='Publicaciones',
                         color_continuous_scale='Blues')
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Evolución del impacto
            fig2 = px.line(yearly_stats, x='Año', y='Citas Promedio',
                          title="Evolución del Impacto Promedio",
                          markers=True)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Heatmap de productividad
        st.markdown("##### 🔥 Mapa de Calor de Productividad")
        
        # Crear matriz para heatmap
        years = sorted(df_temporal['Año'].unique())
        if len(years) > 3:
            productivity_matrix = []
            
            for year in years[-10:]:  # Últimos 10 años
                year_data = df_temporal[df_temporal['Año'] == year]
                productivity_matrix.append([
                    len(year_data),  # Publicaciones
                    year_data['Citas'].sum(),  # Citas totales
                    year_data['Co-autores'].mean(),  # Colaboración promedio
                    year_data['Citas'].mean()  # Impacto promedio
                ])
            
            heatmap_df = pd.DataFrame(productivity_matrix, 
                                    index=years[-10:],
                                    columns=['Publicaciones', 'Citas Totales', 'Colaboración', 'Impacto'])
            
            # Normalizar para el heatmap
            heatmap_normalized = (heatmap_df - heatmap_df.min()) / (heatmap_df.max() - heatmap_df.min())
            
            fig_heatmap = px.imshow(heatmap_normalized.T, 
                                  aspect='auto',
                                  title="Mapa de Calor de Métricas Normalizadas",
                                  color_continuous_scale='RdYlBu_r')
            st.plotly_chart(fig_heatmap, use_container_width=True)

def show_geographic_analysis(graph):
    """Análisis geográfico de la red"""
    st.markdown("#### 🌍 Análisis Geográfico de Colaboración")
    
    # Recopilar datos de afiliaciones
    affiliations = []
    for node, data in graph.nodes(data=True):
        if data.get('node_type') == 'author':
            affiliation = data.get('affiliation', 'N/A')
            if affiliation and affiliation != 'N/A':
                publications = len([n for n in graph.neighbors(node) 
                                  if graph.nodes[n].get('node_type') == 'article'])
                h_index = data.get('h_index', 0)
                
                affiliations.append({
                    'Institución': affiliation,
                    'Investigador': data.get('display_name', node),
                    'Publicaciones': publications,
                    'H-Index': h_index
                })
    
    if affiliations:
        df_geo = pd.DataFrame(affiliations)
        
        # Análisis por institución
        inst_stats = df_geo.groupby('Institución').agg({
            'Investigador': 'count',
            'Publicaciones': 'sum',
            'H-Index': 'mean'
        }).round(2)
        inst_stats.columns = ['Investigadores', 'Publicaciones Totales', 'H-Index Promedio']
        inst_stats = inst_stats.sort_values('Publicaciones Totales', ascending=False).reset_index()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 🏛️ Top Instituciones")
            st.dataframe(inst_stats.head(10), use_container_width=True)
        
        with col2:
            # Gráfico de burbujas por institución
            if len(inst_stats) > 1:
                fig_inst = px.scatter(inst_stats.head(15),
                                    x='Investigadores', 
                                    y='H-Index Promedio',
                                    size='Publicaciones Totales',
                                    hover_data=['Institución'],
                                    title="Análisis Institucional",
                                    color='Publicaciones Totales',
                                    color_continuous_scale='Viridis')
                st.plotly_chart(fig_inst, use_container_width=True)
        
        # Análisis de diversidad institucional
        st.markdown("##### 🌐 Diversidad Institucional")
        
        total_institutions = len(inst_stats)
        total_researchers = df_geo['Investigador'].nunique()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🏛️ Instituciones Únicas", total_institutions)
        with col2:
            diversity_index = total_institutions / total_researchers if total_researchers > 0 else 0
            st.metric("📊 Índice de Diversidad", f"{diversity_index:.3f}")
        with col3:
            avg_researchers_per_inst = total_researchers / total_institutions if total_institutions > 0 else 0
            st.metric("👥 Promedio por Institución", f"{avg_researchers_per_inst:.1f}")
        
        # Distribución de tamaños institucionales
        if len(inst_stats) > 5:
            fig_dist = px.histogram(inst_stats, x='Investigadores',
                                  title="Distribución de Tamaños Institucionales",
                                  nbins=min(20, len(inst_stats)))
            st.plotly_chart(fig_dist, use_container_width=True)
