import streamlit as st
import networkx as nx
import pandas as pd
from app.utils import load_graph, load_author_graph
import plotly.express as px
import plotly.graph_objects as go

def show_overview():
    """Muestra una vista general de los grafos con tabs separados"""
    st.title("📊 Vista General de los Grafos")
    st.markdown("---")
    
    # Cargar los grafos
    main_graph = load_graph()
    author_graph = load_author_graph()
    
    # Crear tabs
    tab1, tab2 = st.tabs(["🔗 Grafo Principal (Autores-Artículos)", "👥 Grafo Autor-Autor"])
    
    with tab1:
        show_main_graph_overview(main_graph)
    
    with tab2:
        show_author_graph_overview(author_graph)

def show_main_graph_overview(graph):
    """Muestra información general del grafo principal (autores-artículos)"""
    if graph is None:
        st.error("❌ No se pudo cargar el grafo principal")
        return
    
    st.header("🔗 Grafo Principal: Autores y Artículos")
    st.markdown("Este grafo representa las relaciones entre autores y sus artículos publicados.")
    
    # Métricas básicas
    col1, col2, col3, col4 = st.columns(4)
    
    # Separar nodos por tipo
    author_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'author']
    article_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'article']
    
    with col1:
        st.metric("Total de Nodos", len(graph.nodes()))
    with col2:
        st.metric("Autores", len(author_nodes))
    with col3:
        st.metric("Artículos", len(article_nodes))
    with col4:
        st.metric("Conexiones", len(graph.edges()))
    
    st.markdown("---")
    
    # Información detallada en columnas
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Estadísticas del Grafo")
        
        # Densidad del grafo
        density = nx.density(graph)
        st.metric("Densidad del Grafo", f"{density:.4f}")
        
        # Grado promedio
        degrees = dict(graph.degree())
        avg_degree = sum(degrees.values()) / len(degrees) if degrees else 0
        st.metric("Grado Promedio", f"{avg_degree:.2f}")
        
        # Componentes conectados
        if graph.is_directed():
            num_components = nx.number_weakly_connected_components(graph)
            st.metric("Componentes Débilmente Conectados", num_components)
        else:
            num_components = nx.number_connected_components(graph)
            st.metric("Componentes Conectados", num_components)
    
    with col2:
        st.subheader("🏆 Top Autores por Conexiones")
        
        # Calcular grados solo para autores
        author_degrees = {node: degree for node, degree in degrees.items() if node in author_nodes}
        
        if author_degrees:
            # Crear DataFrame para mostrar top autores
            top_authors = sorted(author_degrees.items(), key=lambda x: x[1], reverse=True)[:10]
            df_top = pd.DataFrame(top_authors, columns=['Autor', 'Conexiones'])
            
            # Obtener nombres reales de los autores
            for idx, row in df_top.iterrows():
                author_id = row['Autor']
                if author_id in graph.nodes():
                    author_data = graph.nodes[author_id]
                    display_name = author_data.get('display_name', author_id)
                    df_top.at[idx, 'Autor'] = display_name
            
            st.dataframe(df_top, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de autores disponibles")
    
    # Gráfico de distribución de grados
    st.subheader("📊 Distribución de Grados")
    
    if degrees:
        degree_values = list(degrees.values())
        
        fig = px.histogram(
            x=degree_values,
            nbins=20,
            title="Distribución de Grados en el Grafo",
            labels={'x': 'Grado', 'y': 'Frecuencia'}
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Interpretación de enlaces y patrones de colaboración
    st.subheader("🔗 Interpretación de Enlaces y Patrones")
    
    if degrees and len(graph.edges()) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🌐 Análisis de la Red:**")
            
            # Densidad interpretada
            density = nx.density(graph)
            if density > 0.1:
                st.write("• Red densa: Alta interconexión entre autores")
            elif density > 0.01:
                st.write("• Red moderadamente conectada")
            else:
                st.write("• Red dispersa: Pocos enlaces entre autores")
            
            # Componentes interpretados
            if graph.is_directed():
                num_components = nx.number_weakly_connected_components(graph)
            else:
                num_components = nx.number_connected_components(graph)
            
            if num_components == 1:
                st.write("• Red completamente conectada")
            elif num_components < len(graph.nodes()) * 0.1:
                st.write("• Pocas comunidades aisladas")
            else:
                st.write("• Múltiples grupos de colaboración separados")
        
        with col2:
            st.write("**🤝 Patrones de Colaboración:**")
            
            # Análisis de distribución de grados
            degree_values = list(degrees.values())
            unique_degrees = len(set(degree_values))
            
            if max(degree_values) > 0:
                # Porcentaje de autores muy conectados
                high_collab = len([d for d in degree_values if d >= max(degree_values) * 0.5])
                high_collab_pct = (high_collab / len(degree_values)) * 100
                
                if high_collab_pct > 20:
                    st.write("• Muchos autores altamente colaborativos")
                elif high_collab_pct > 5:
                    st.write("• Algunos autores actúan como conectores clave")
                else:
                    st.write("• Pocos autores dominan las colaboraciones")
                
                # Autores aislados
                isolated = len([d for d in degree_values if d == 0])
                if isolated > 0:
                    isolated_pct = (isolated / len(degree_values)) * 100
                    st.write(f"• {isolated_pct:.1f}% de autores sin colaboraciones")
                else:
                    st.write("• Todos los autores tienen al menos una colaboración")
    else:
        st.info("No hay suficientes enlaces para realizar interpretaciones detalladas")

def show_author_graph_overview(graph):
    """Muestra información general del grafo autor-autor"""
    if graph is None:
        st.warning("⚠️ No se pudo cargar el grafo autor-autor")
        st.info("Este grafo se genera automáticamente basado en colaboraciones entre autores.")
        return
    
    st.header("👥 Grafo Autor-Autor: Red de Colaboraciones")
    st.markdown("Este grafo muestra las relaciones de colaboración entre autores basadas en artículos compartidos.")
    
    # Métricas básicas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Autores", len(graph.nodes()))
    with col2:
        st.metric("Colaboraciones", len(graph.edges()))
    with col3:
        density = nx.density(graph)
        st.metric("Densidad", f"{density:.4f}")
    with col4:
        # Componentes conectados
        if graph.is_directed():
            num_components = nx.number_weakly_connected_components(graph)
        else:
            num_components = nx.number_connected_components(graph)
        st.metric("Componentes", num_components)
    
    st.markdown("---")
    
    # Información detallada en columnas
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔍 Análisis de Colaboraciones")
        
        # Análisis de los enlaces y colaboraciones
        if len(graph.nodes()) > 0 and len(graph.edges()) > 0:
            degrees = dict(graph.degree())
            
            # Estadísticas de colaboración
            max_collaborations = max(degrees.values())
            min_collaborations = min(degrees.values())
            avg_collaborations = sum(degrees.values()) / len(degrees)
            
            st.metric("Máximo de Colaboraciones", max_collaborations)
            st.metric("Mínimo de Colaboraciones", min_collaborations)
            st.metric("Promedio de Colaboraciones", f"{avg_collaborations:.1f}")
            
            # Interpretación de la red
            if max_collaborations > avg_collaborations * 3:
                st.info("🌟 Hay autores muy conectados que actúan como hubs en la red")
            
            # Análisis de aislamiento
            isolated_authors = len([n for n, d in degrees.items() if d == 0])
            if isolated_authors > 0:
                st.warning(f"⚠️ {isolated_authors} autores están aislados (sin colaboraciones)")
        else:
            st.info("No hay suficientes datos para el análisis")
    
    with col2:
        st.subheader("🤝 Top Colaboradores")
        
        # Autores con más colaboraciones
        degrees = dict(graph.degree())
        
        if degrees:
            top_collaborators = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:10]
            df_collab = pd.DataFrame(top_collaborators, columns=['Autor', 'Colaboraciones'])
            
            # Obtener nombres reales de los autores
            for idx, row in df_collab.iterrows():
                author_id = row['Autor']
                if author_id in graph.nodes():
                    author_data = graph.nodes[author_id]
                    display_name = author_data.get('display_name', author_id)
                    df_collab.at[idx, 'Autor'] = display_name
            
            st.dataframe(df_collab, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de colaboración disponibles")
    
    # Gráfico de distribución de colaboraciones
    st.subheader("📊 Distribución de Colaboraciones")
    
    if degrees:
        degree_values = list(degrees.values())
        
        fig = px.histogram(
            x=degree_values,
            nbins=15,
            title="Distribución de Número de Colaboraciones",
            labels={'x': 'Número de Colaboraciones', 'y': 'Frecuencia'}
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # Información adicional sobre el grafo
    st.subheader("ℹ️ Información Adicional")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Tipo de Grafo:**", "Dirigido" if graph.is_directed() else "No dirigido")
        st.write("**Grado Promedio:**", f"{sum(degrees.values()) / len(degrees):.2f}" if degrees else "N/A")
    
    with col2:
        # Clustering coefficient si es posible calcularlo
        try:
            if not graph.is_directed() and len(graph.nodes()) > 0:
                clustering = nx.average_clustering(graph)
                st.write("**Coeficiente de Clustering:**", f"{clustering:.4f}")
        except:
            st.write("**Coeficiente de Clustering:**", "No calculable")