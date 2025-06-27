import networkx as nx 
import streamlit as st
try:
    import warnings
    warnings.filterwarnings('ignore')
    HAS_ADVANCED_LIBS = True
except ImportError:
    HAS_ADVANCED_LIBS = False

import plotly.express as px
import numpy as np
import pandas as pd

def show_network_analysis():
    """Muestra la página de análisis de redes complejas"""
    st.markdown("## 🔬 Análisis de Redes Complejas")
    
    if not HAS_ADVANCED_LIBS:
        st.error("⚠️ Faltan librerías para análisis avanzado. Instala: matplotlib, seaborn, python-louvain")
        return
    
    if st.session_state.graph is None or len(st.session_state.graph.nodes()) == 0:
        st.warning("⚠️ No hay datos en el grafo para analizar")
        return
    
    graph = st.session_state.graph
    
    # Tabs para diferentes análisis
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Métricas Básicas", "🎯 Centralidad", "👥 Comunidades", "🔬 Métricas Avanzadas"])
    
    with tab1:
        st.markdown("### 📊 Métricas Básicas de la Red")
        
        # Métricas básicas (rápidas)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Nodos", len(graph.nodes()))
            st.metric("Aristas", len(graph.edges()))
        
        with col2:
            density = nx.density(graph)
            st.metric("Densidad", f"{density:.4f}")
            components = nx.number_connected_components(graph)
            st.metric("Componentes", components)
        
        with col3:
            # Solo calcular si el grafo no es muy grande
            if len(graph.nodes()) < 500:
                avg_clustering = nx.average_clustering(graph)
                st.metric("Clustering Promedio", f"{avg_clustering:.4f}")
            else:
                st.metric("Clustering Promedio", "Calculando...")
                if st.button("🔄 Calcular Clustering", key="calc_clustering"):
                    with st.spinner("Calculando clustering promedio..."):
                        avg_clustering = nx.average_clustering(graph)
                        st.metric("Clustering Promedio", f"{avg_clustering:.4f}")
                        st.success("✅ Clustering calculado")
            
            is_bipartite = nx.bipartite.is_bipartite(graph)
            st.metric("Red Bipartita", "Sí" if is_bipartite else "No")
        
        with col4:
            # Solo calcular métricas costosas para grafos pequeños o bajo demanda
            if nx.is_connected(graph):
                if len(graph.nodes()) < 200:
                    # Calcular automáticamente solo para grafos pequeños
                    diameter = nx.diameter(graph)
                    avg_path = nx.average_shortest_path_length(graph)
                    st.metric("Diámetro", diameter)
                    st.metric("Camino Promedio", f"{avg_path:.4f}")
                else:
                    # Para grafos grandes, mostrar botón
                    st.metric("Diámetro", "📊")
                    st.metric("Camino Promedio", "📊")
                    if st.button("🔄 Calcular Métricas de Camino", key="calc_path_metrics"):
                        with st.spinner("Calculando métricas de camino (puede tomar tiempo)..."):
                            diameter = nx.diameter(graph)
                            avg_path = nx.average_shortest_path_length(graph)
                            st.metric("Diámetro", diameter)
                            st.metric("Camino Promedio", f"{avg_path:.4f}")
                            st.success("✅ Métricas de camino calculadas")
            else:
                st.metric("Diámetro", "N/A")
                st.metric("Camino Promedio", "N/A")
        
        # Distribución de grados
        st.markdown("### 📈 Distribución de Grados")
        degrees = [graph.degree(n) for n in graph.nodes()]
        
        if degrees:  # Solo si hay nodos
            col1, col2 = st.columns(2)
            with col1:
                # Solo crear histograma si no es muy costoso
                if len(degrees) < 1000:
                    fig_hist = px.histogram(
                        x=degrees,
                        nbins=min(20, len(set(degrees))),
                        title="Distribución de Grados",
                        labels={'x': 'Grado', 'y': 'Frecuencia'}
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)
                else:
                    st.info("Grafo grande detectado. Las visualizaciones están optimizadas.")
                    if st.button("📊 Generar Histograma", key="generate_histogram"):
                        with st.spinner("Generando histograma..."):
                            fig_hist = px.histogram(
                                x=degrees,
                                nbins=min(20, len(set(degrees))),
                                title="Distribución de Grados",
                                labels={'x': 'Grado', 'y': 'Frecuencia'}
                            )
                            st.plotly_chart(fig_hist, use_container_width=True)
            
            with col2:
                st.metric("Grado Mínimo", min(degrees))
                st.metric("Grado Máximo", max(degrees))
                st.metric("Grado Promedio", f"{np.mean(degrees):.2f}")
                st.metric("Desviación Estándar", f"{np.std(degrees):.2f}")
        else:
            st.warning("No hay nodos en el grafo para analizar")
    
    with tab2:
        st.markdown("### 🎯 Análisis de Centralidad")
        
        # Mostrar información del cache
        graph_hash = f"{len(graph.nodes())}_{len(graph.edges())}"
        cache_exists = ('centralities_cache' in st.session_state and 
                       graph_hash in st.session_state.centralities_cache)
        
        if cache_exists:
            st.info("📋 **Estado:** Centralidades ya calculadas y almacenadas en cache")
            # Mostrar información adicional sobre el cache
            st.markdown("#### 💾 Información del Cache")
            cache_info = st.session_state.centralities_cache[graph_hash]
            available_measures = list(cache_info.keys())
            st.success(f"**Medidas disponibles en cache:** {', '.join(available_measures)}")
        else:
            st.warning("⏳ **Estado:** Centralidades no calculadas. Se calcularán cuando hagas clic en 'Calcular Centralidades'.")
        
        # Botón para recalcular centralidades
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            centrality_type = st.selectbox(
                "Selecciona medida de centralidad:",
                ["Grado", "Intermediación", "Cercanía", "Vector Propio"]
            )
        with col2:
            calculate_button = st.button("🎯 Calcular Centralidades", 
                                       help="Calcular todas las centralidades para el grafo actual",
                                       type="primary" if not cache_exists else "secondary")
        with col3:
            if cache_exists and st.button("🔄 Recalcular", help="Forzar recálculo de todas las centralidades"):
                # Limpiar cache para este grafo
                if 'centralities_cache' in st.session_state and graph_hash in st.session_state.centralities_cache:
                    del st.session_state.centralities_cache[graph_hash]
                    st.success("Cache limpiado. Se recalcularán las centralidades.")
                    st.rerun()
        
        # Solo calcular centralidades si se presiona el botón o ya existen en cache
        if calculate_button or cache_exists:
            if calculate_button and not cache_exists:
                # Calcular centralidades
                with st.spinner("🔄 Calculando todas las centralidades..."):
                    centralities = calculate_centralities(graph)
                st.success("🎯 Centralidades calculadas y almacenadas en cache")
                st.rerun()
            elif cache_exists:
                # Obtener centralidad desde cache (sin recalcular)
                centralities = st.session_state.centralities_cache[graph_hash]
                centrality = centralities.get(centrality_type, nx.degree_centrality(graph))
                
                # Top nodos por centralidad
                sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
                
                centrality_data = []
                for node, cent_value in sorted_nodes:
                    node_data = graph.nodes[node]
                    name = node_data.get('display_name', node_data.get('title', str(node)))
                    node_type = node_data.get('type', node_data.get('node_type', 'unknown'))
                    centrality_data.append({
                        'Nombre': name,
                        'Tipo': node_type,
                        f'{centrality_type}': f"{cent_value:.4f}"
                    })
                
                st.markdown(f"#### Top 10 por {centrality_type}")
                st.dataframe(pd.DataFrame(centrality_data), use_container_width=True)
                
                # Distribución
                values = list(centrality.values())
                
                col1, col2 = st.columns(2)
                with col1:
                    fig_cent = px.histogram(
                        x=values,
                        nbins=20,
                        title=f"Distribución de {centrality_type}",
                        labels={'x': centrality_type, 'y': 'Frecuencia'}
                    )
                    st.plotly_chart(fig_cent, use_container_width=True)
                
                with col2:
                    # Estadísticas de la centralidad
                    st.markdown(f"#### Estadísticas de {centrality_type}")
                    st.metric("Valor Mínimo", f"{min(values):.4f}")
                    st.metric("Valor Máximo", f"{max(values):.4f}")
                    st.metric("Valor Promedio", f"{np.mean(values):.4f}")
                    st.metric("Desviación Estándar", f"{np.std(values):.4f}")
                    
                    # Nodo con mayor centralidad
                    max_node = max(centrality.items(), key=lambda x: x[1])
                    max_node_data = graph.nodes[max_node[0]]
                    max_node_name = max_node_data.get('display_name', max_node_data.get('title', str(max_node[0])))
                    st.markdown(f"**Nodo más central:** {max_node_name}")
                
                # Mostrar comparación rápida entre medidas si hay múltiples en cache
                if len(available_measures) > 1:
                    st.markdown("---")
                    st.markdown("#### 📊 Comparación Rápida entre Medidas")
                    comparison_data = []
                    for measure in available_measures:
                        measure_values = list(centralities[measure].values())
                        comparison_data.append({
                            'Medida': measure,
                            'Mín': f"{min(measure_values):.4f}",
                            'Máx': f"{max(measure_values):.4f}",
                            'Promedio': f"{np.mean(measure_values):.4f}",
                            'Desv. Est.': f"{np.std(measure_values):.4f}"
                        })
                    
                    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True)
        else:
            st.info("👆 Haz clic en 'Calcular Centralidades' para comenzar el análisis")
    
    with tab3:
        st.markdown("### 👥 Análisis de Comunidades")
        
        if len(graph.nodes()) < 3:
            st.warning("Se necesitan al menos 3 nodos para detectar comunidades")
            return
        
        try:
            # Detectar comunidades usando algoritmo greedy
            communities = list(nx.community.greedy_modularity_communities(graph))
            modularity = nx.community.modularity(graph, communities)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Número de Comunidades", len(communities))
                st.metric("Modularidad", f"{modularity:.4f}")
            
            with col2:
                sizes = [len(comm) for comm in communities]
                st.metric("Comunidad más grande", max(sizes))
                st.metric("Comunidad más pequeña", min(sizes))
            
            # Distribución de tamaños
            fig_comm = px.bar(
                x=list(range(len(sizes))),
                y=sizes,
                title="Tamaño de Comunidades",
                labels={'x': 'Comunidad', 'y': 'Tamaño'}
            )
            st.plotly_chart(fig_comm, use_container_width=True)
            
            # Detalles de comunidades
            selected_comm = st.selectbox("Ver detalles de comunidad:", range(len(communities)))
            
            if selected_comm is not None:
                comm_nodes = list(communities[selected_comm])
                comm_data = []
                for node in comm_nodes:
                    node_data = graph.nodes[node]
                    name = node_data.get('display_name', node_data.get('title', str(node)))
                    node_type = node_data.get('type', node_data.get('node_type', 'unknown'))
                    comm_data.append({'Nombre': name, 'Tipo': node_type})
                
                st.dataframe(pd.DataFrame(comm_data), use_container_width=True)
                
        except Exception as e:
            st.error(f"Error en detección de comunidades: {str(e)}")
    
    with tab4:
        show_advanced_network_metrics()


# Función para calcular y cachear centralidades
def calculate_centralities(graph):
    """
    Calcula todas las medidas de centralidad y las almacena en el estado de la sesión
    para evitar recálculos innecesarios
    """
    # Verificar si ya están calculadas las centralidades para este grafo
    graph_hash = f"{len(graph.nodes())}_{len(graph.edges())}"
    
    # Inicializar cache de centralidades si no existe
    if 'centralities_cache' not in st.session_state:
        st.session_state.centralities_cache = {}
    
    # Si ya están calculadas para este grafo, devolver del cache
    if graph_hash in st.session_state.centralities_cache:
        return st.session_state.centralities_cache[graph_hash]

    centralities = {}
    
    try:

        progress_placeholder = st.empty()
        
        progress_placeholder.info("🔄 Calculando centralidad de grado...")
        centralities['Grado'] = nx.degree_centrality(graph)

        progress_placeholder.info("🔄 Calculando centralidad de intermediación...")
        if len(graph.nodes()) < 1000:  
            centralities['Intermediación'] = nx.betweenness_centrality(graph)
        else:
            centralities['Intermediación'] = nx.betweenness_centrality(graph, k=100)
        
        progress_placeholder.info("🔄 Calculando centralidad de cercanía...")
        if nx.is_connected(graph):
            centralities['Cercanía'] = nx.closeness_centrality(graph)
        else:
            centralities['Cercanía'] = {}
            for component in nx.connected_components(graph):
                subgraph = graph.subgraph(component)
                closeness = nx.closeness_centrality(subgraph)
                centralities['Cercanía'].update(closeness)

        progress_placeholder.info("🔄 Calculando centralidad de vector propio...")
        try:
            centralities['Vector Propio'] = nx.eigenvector_centrality(graph, max_iter=1000)
        except:
            centralities['Vector Propio'] = centralities['Grado']
        
        progress_placeholder.empty()
            
    except Exception as e:
        st.error(f"Error calculando centralidades: {str(e)}")
        centralities = {
            'Grado': nx.degree_centrality(graph),
            'Intermediación': nx.degree_centrality(graph),
            'Cercanía': nx.degree_centrality(graph),
            'Vector Propio': nx.degree_centrality(graph)
        }
    
    # Guardar en cache
    st.session_state.centralities_cache[graph_hash] = centralities
    
    return centralities


def get_cached_centrality(graph, centrality_type):
    """
    Obtiene una centralidad específica del cache o la calcula si no existe
    """
    centralities = calculate_centralities(graph)
    return centralities.get(centrality_type, nx.degree_centrality(graph))


def show_advanced_network_metrics():
    """Muestra métricas avanzadas de la red"""
    st.markdown("### 🔬 Métricas Avanzadas")
    
    graph = st.session_state.graph
    
    # Información sobre el tamaño del grafo
    num_nodes = len(graph.nodes())
    num_edges = len(graph.edges())
    
    if num_nodes > 500:
        st.warning(f"⚠️ Grafo grande detectado ({num_nodes} nodos). Algunas métricas se calcularán bajo demanda para optimizar el rendimiento.")
    
    # Análisis de caminos más cortos
    if nx.is_connected(graph):
        st.markdown("#### Análisis de Caminos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if num_nodes < 200:
                # Calcular automáticamente para grafos pequeños
                try:
                    eccentricity = nx.eccentricity(graph)
                    center = nx.center(graph)
                    periphery = nx.periphery(graph)
                    
                    st.metric("Radio", nx.radius(graph))
                    st.metric("Diámetro", nx.diameter(graph))
                    st.metric("Nodos Centrales", len(center))
                    st.metric("Nodos Periféricos", len(periphery))
                    
                except Exception as e:
                    st.warning(f"No se pudieron calcular algunas métricas: {str(e)}")
            else:
                # Para grafos grandes, mostrar botón
                st.info("Métricas de excentricidad disponibles bajo demanda")
                if st.button("🔄 Calcular Métricas de Excentricidad", key="calc_eccentricity"):
                    with st.spinner("Calculando métricas de excentricidad (puede tomar tiempo)..."):
                        try:
                            eccentricity = nx.eccentricity(graph)
                            center = nx.center(graph)
                            periphery = nx.periphery(graph)
                            
                            st.metric("Radio", nx.radius(graph))
                            st.metric("Diámetro", nx.diameter(graph))
                            st.metric("Nodos Centrales", len(center))
                            st.metric("Nodos Periféricos", len(periphery))
                            st.success("✅ Métricas calculadas")
                            
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        
        with col2:
            # Distribución de distancias
            if num_nodes < 100:
                # Solo para grafos muy pequeños
                try:
                    all_pairs_shortest = dict(nx.all_pairs_shortest_path_length(graph))
                    distances = []
                    for source in all_pairs_shortest:
                        for target, distance in all_pairs_shortest[source].items():
                            if source != target:
                                distances.append(distance)
                    
                    fig_dist = px.histogram(
                        x=distances,
                        nbins=max(1, min(20, len(set(distances)))),
                        title="Distribución de Distancias",
                        labels={'x': 'Distancia', 'y': 'Frecuencia'}
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)
                    
                except Exception as e:
                    st.warning(f"No se pudo calcular distribución de distancias: {str(e)}")
            else:
                st.info("Distribución de distancias disponible bajo demanda")
                if st.button("📊 Calcular Distribución de Distancias", key="calc_distances"):
                    with st.spinner("Calculando distribución de distancias..."):
                        try:
                            # Para grafos grandes, usar muestra
                            if num_nodes > 200:
                                sample_nodes = list(graph.nodes())[:50]  # Muestra de 50 nodos
                                st.info(f"Usando muestra de {len(sample_nodes)} nodos para el cálculo")
                            else:
                                sample_nodes = list(graph.nodes())
                            
                            distances = []
                            for source in sample_nodes:
                                try:
                                    paths = nx.single_source_shortest_path_length(graph, source, cutoff=6)
                                    for target, distance in paths.items():
                                        if source != target:
                                            distances.append(distance)
                                except:
                                    continue
                            
                            if distances:
                                fig_dist = px.histogram(
                                    x=distances,
                                    nbins=max(1, min(20, len(set(distances)))),
                                    title="Distribución de Distancias (Muestra)",
                                    labels={'x': 'Distancia', 'y': 'Frecuencia'}
                                )
                                st.plotly_chart(fig_dist, use_container_width=True)
                                st.success("✅ Distribución calculada")
                            else:
                                st.warning("No se pudieron calcular distancias")
                                
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
    else:
        st.info("El grafo no está conectado. Las métricas de caminos no están disponibles.")
    
    # Análisis de triángulos y clustering
    st.markdown("#### Análisis de Clustering")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Cálculos básicos de triángulos
        if num_nodes < 300:
            triangles = nx.triangles(graph)
            total_triangles = sum(triangles.values()) // 3
            
            st.metric("Total de Triángulos", total_triangles)
            st.metric("Transitividad", f"{nx.transitivity(graph):.4f}")
            
            # Nodos con más triángulos
            top_triangles = sorted(triangles.items(), key=lambda x: x[1], reverse=True)[:5]
            triangle_data = []
            for node, count in top_triangles:
                node_data = graph.nodes[node]
                name = node_data.get('display_name', node_data.get('title', str(node)))
                triangle_data.append({'Nombre': name, 'Triángulos': count})
            
            if triangle_data:
                st.markdown("**Top 5 Nodos en Triángulos:**")
                st.dataframe(pd.DataFrame(triangle_data), use_container_width=True)
        else:
            st.info("Análisis de triángulos disponible bajo demanda")
            if st.button("🔺 Calcular Análisis de Triángulos", key="calc_triangles"):
                with st.spinner("Calculando triángulos..."):
                    try:
                        triangles = nx.triangles(graph)
                        total_triangles = sum(triangles.values()) // 3
                        
                        st.metric("Total de Triángulos", total_triangles)
                        st.metric("Transitividad", f"{nx.transitivity(graph):.4f}")
                        
                        # Top 5 nodos
                        top_triangles = sorted(triangles.items(), key=lambda x: x[1], reverse=True)[:5]
                        triangle_data = []
                        for node, count in top_triangles:
                            node_data = graph.nodes[node]
                            name = node_data.get('display_name', node_data.get('title', str(node)))
                            triangle_data.append({'Nombre': name, 'Triángulos': count})
                        
                        if triangle_data:
                            st.markdown("**Top 5 Nodos en Triángulos:**")
                            st.dataframe(pd.DataFrame(triangle_data), use_container_width=True)
                        
                        st.success("✅ Análisis de triángulos completado")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    with col2:
        # Distribución de clustering local
        if num_nodes < 200:
            clustering = nx.clustering(graph)
            clustering_values = list(clustering.values())
            
            if clustering_values:
                fig_clust = px.histogram(
                    x=clustering_values,
                    nbins=20,
                    title="Distribución de Clustering Local",
                    labels={'x': 'Clustering Coefficient', 'y': 'Frecuencia'}
                )
                st.plotly_chart(fig_clust, use_container_width=True)
        else:
            st.info("Distribución de clustering disponible bajo demanda")
            if st.button("📊 Calcular Clustering Local", key="calc_local_clustering"):
                with st.spinner("Calculando clustering local..."):
                    try:
                        clustering = nx.clustering(graph)
                        clustering_values = list(clustering.values())
                        
                        if clustering_values:
                            fig_clust = px.histogram(
                                x=clustering_values,
                                nbins=20,
                                title="Distribución de Clustering Local",
                                labels={'x': 'Clustering Coefficient', 'y': 'Frecuencia'}
                            )
                            st.plotly_chart(fig_clust, use_container_width=True)
                            st.success("✅ Clustering local calculado")
                        else:
                            st.warning("No se pudieron calcular valores de clustering")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
