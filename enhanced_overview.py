import streamlit as st
import networkx as nx
import pandas as pd
from app.utils import load_graph, load_author_graph, load_article_graph
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict, Counter, deque
import numpy as np
from functools import lru_cache
import heapq
from typing import Dict, Set, List, Tuple

class GraphMetricsCache:
    """Cache optimizado para métricas de grafo usando estructuras de datos eficientes"""
    
    def __init__(self, graph):
        self.graph = graph
        self._cache = {}
        self._precompute_basic_metrics()
    
    def _precompute_basic_metrics(self):
        """Precomputa métricas básicas una sola vez"""
        self._node_array = np.array(list(self.graph.nodes()))
        self._degrees_dict = dict(self.graph.degree())
        self._degrees_array = np.array(list(self._degrees_dict.values()))
        
        self._author_nodes = set()
        self._article_nodes = set()
        
        for node, data in self.graph.nodes(data=True):
            node_type = data.get('node_type')
            if node_type == 'author':
                self._author_nodes.add(node)
            elif node_type == 'article':
                self._article_nodes.add(node)
    
    @property
    def degrees(self) -> Dict:
        return self._degrees_dict
    
    @property
    def degree_values(self) -> np.ndarray:
        return self._degrees_array
    
    @property
    def author_nodes(self) -> Set:
        return self._author_nodes
    
    @property
    def article_nodes(self) -> Set:
        return self._article_nodes
    
    @lru_cache(maxsize=1)
    def get_basic_stats(self) -> Dict:
        """Obtiene estadísticas básicas"""
        return {
            'num_nodes': len(self.graph.nodes()),
            'num_edges': len(self.graph.edges()),
            'num_authors': len(self._author_nodes),
            'num_articles': len(self._article_nodes),
            'density': nx.density(self.graph),
            'max_degree': int(np.max(self._degrees_array)) if len(self._degrees_array) > 0 else 0,
            'min_degree': int(np.min(self._degrees_array)) if len(self._degrees_array) > 0 else 0,
            'avg_degree': float(np.mean(self._degrees_array)) if len(self._degrees_array) > 0 else 0,
            'std_degree': float(np.std(self._degrees_array)) if len(self._degrees_array) > 0 else 0
        }
    
    @lru_cache(maxsize=1)
    def get_top_nodes_by_degree(self, node_type: str = None, top_k: int = 10) -> List[Tuple]:
        """Obtiene top k nodos por grado """
        if node_type == 'author':
            target_nodes = self._author_nodes
        elif node_type == 'article':
            target_nodes = self._article_nodes
        else:
            target_nodes = set(self.graph.nodes())
        

        heap = []
        for node in target_nodes:
            degree = self._degrees_dict[node]
            if len(heap) < top_k:
                heapq.heappush(heap, (degree, node))
            elif degree > heap[0][0]:
                heapq.heapreplace(heap, (degree, node))
        
        return sorted([(node, degree) for degree, node in heap], key=lambda x: x[1], reverse=True)
    
    @lru_cache(maxsize=1)
    def get_degree_distribution(self) -> Dict:
        """Calcula distribución de grados"""
        degree_counter = Counter(self._degrees_array)
        return {
            'degree_counts': dict(degree_counter),
            'unique_degrees': len(degree_counter),
            'degree_histogram': np.histogram(self._degrees_array, bins=min(20, len(degree_counter)))
        }
    
    @lru_cache(maxsize=1)
    def get_components_info(self) -> Dict:
        """Obtiene información de componentes"""
        if self.graph.is_directed():
            components = list(nx.weakly_connected_components(self.graph))
            num_components = nx.number_weakly_connected_components(self.graph)
        else:
            components = list(nx.connected_components(self.graph))
            num_components = nx.number_connected_components(self.graph)
        
        component_sizes = np.array([len(comp) for comp in components])
        
        return {
            'num_components': num_components,
            'components': components,
            'component_sizes': component_sizes,
            'largest_component_size': int(np.max(component_sizes)) if len(component_sizes) > 0 else 0,
            'component_size_distribution': Counter(component_sizes)
        }

class OptimizedBridgeAnalyzer:
    """Analizador de puntos de articulacion"""
    
    def __init__(self, graph, metrics_cache):
        self.graph = graph
        self.cache = metrics_cache
        self._bridge_cache = {}
    
    def find_critical_bridges(self, max_candidates: int = 50) -> List[Dict]:
        """Encuentra puentes críticos """
        if self.graph.is_directed():
            return []
        
        components_info = self.cache.get_components_info()
        
        if components_info['num_components'] == 1:
            return self._analyze_connected_graph_bridges()
        else:
            return self._analyze_fragmented_graph_bridges(components_info, max_candidates)
    
    def _analyze_connected_graph_bridges(self) -> List[Dict]:
        """Analiza puentes en grafo conectado"""
        articulation_points = set(nx.articulation_points(self.graph))
        
        if not articulation_points:
            return []
        
        bridge_heap = []
        degrees = self.cache.degrees
        
        sorted_bridges = sorted(articulation_points, key=lambda x: degrees[x], reverse=True)
        
        for node in sorted_bridges[:20]:  
            temp_graph = self.graph.copy()
            temp_graph.remove_node(node)
            new_components = nx.number_connected_components(temp_graph)
            
            author_data = self.graph.nodes[node]
            display_name = author_data.get('display_name', node)
            
            bridge_info = {
                'Autor': display_name,
                'Colaboraciones': degrees[node],
                'Componentes si se elimina': new_components,
                'Criticidad': new_components - 1,
                'Tipo': 'Puente Crítico'
            }
            
            if len(bridge_heap) < 10:
                heapq.heappush(bridge_heap, (new_components, degrees[node], bridge_info))
            elif new_components > bridge_heap[0][0]:
                heapq.heapreplace(bridge_heap, (new_components, degrees[node], bridge_info))
        
        return sorted([info for _, _, info in bridge_heap], 
                     key=lambda x: (x['Criticidad'], x['Colaboraciones']), reverse=True)
    
    def _analyze_fragmented_graph_bridges(self, components_info, max_candidates: int) -> List[Dict]:
        """Analiza puentes en grafo fragmentado"""
        components = components_info['components']
        degrees = self.cache.degrees
        all_bridges = []
        
        high_degree_nodes = [node for node, degree in degrees.items() if degree >= 2]
        candidate_nodes = heapq.nlargest(max_candidates, high_degree_nodes, key=lambda x: degrees[x])
        
        for node in candidate_nodes:
            temp_graph = self.graph.copy()
            temp_graph.remove_node(node)
            new_components = nx.number_connected_components(temp_graph)
            
            if new_components > components_info['num_components']:
                author_data = self.graph.nodes[node]
                display_name = author_data.get('display_name', node)
                
                all_bridges.append({
                    'Autor': display_name,
                    'Colaboraciones': degrees[node],
                    'Componentes si se elimina': new_components,
                    'Criticidad Global': new_components - components_info['num_components'],
                    'Tipo': 'Puente Global'
                })
        
        global_bridge_authors = {bridge['Autor'] for bridge in all_bridges}
        
        large_components = [comp for comp in sorted(components, key=len, reverse=True)[:5] if len(comp) > 3]
        
        for i, comp in enumerate(large_components):
            subgraph = self.graph.subgraph(comp)
            if nx.is_connected(subgraph):
                articulation_points = set(nx.articulation_points(subgraph))
                
                for node in articulation_points:
                    author_data = self.graph.nodes[node]
                    display_name = author_data.get('display_name', node)
                    
                    if display_name not in global_bridge_authors:
                        temp_subgraph = subgraph.copy()
                        temp_subgraph.remove_node(node)
                        new_sub_components = nx.number_connected_components(temp_subgraph)
                        
                        all_bridges.append({
                            'Autor': display_name,
                            'Colaboraciones': degrees[node],
                            'Componentes si se elimina': new_sub_components,
                            'Criticidad Global': new_sub_components - 1,
                            'Tipo': f'Puente Local (Comp. {i+1})'
                        })
    
        return sorted(all_bridges, key=lambda x: (x['Criticidad Global'], x['Colaboraciones']), reverse=True)

def show_overview():
    """Muestra una vista general de los grafos con caché en session_state"""
    st.title("📊 Vista General")
    st.markdown("---")

    # Verificar el tipo de grafo seleccionado
    graph_type = st.session_state.get('graph_type', 'base')
    
    if graph_type == 'pdf':
        # Modo PDF: solo mostrar el grafo principal (que es el de PDFs)
        main_graph = st.session_state.get('graph')
        if main_graph is None:
            st.error("❌ No se pudo cargar el grafo de PDFs")
            return
        
        st.info("🔍 **Modo PDF**: Mostrando solo datos extraídos de documentos PDF procesados")
        show_pdf_graph_overview(main_graph)
    
    else:
        # Modo base: mostrar todos los grafos
        main_graph = st.session_state.get('graph')
        author_graph = st.session_state.get('author_graph')
        article_graph = st.session_state.get('article_graph')
        
        if main_graph is None:
            st.error("❌ No se pudo cargar el grafo principal")
            return

        tab1, tab2, tab3 = st.tabs([
            "🔗 Grafo Principal (Autores-Artículos)", 
            "👥 Grafo Autor-Autor",
            "📄 Grafo Artículo-Artículo"
        ])
        
        with tab1:
            show_main_graph_overview(main_graph)
        with tab2:
            show_author_graph_overview(author_graph)
        with tab3:
            show_article_graph_overview(article_graph)

def show_main_graph_overview(graph):
    """Muestra información general del grafo principal (autores-artículos)"""
    if graph is None:
        st.error("❌ No se pudo cargar el grafo principal")
        return

    st.header("🔗 Grafo Principal: Autores y Artículos")
    st.markdown("Este grafo representa las relaciones entre autores y sus artículos publicados.")
    st.markdown("---")

    metrics_cache = GraphMetricsCache(graph)
    basic_stats = metrics_cache.get_basic_stats()

    with st.container():

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Nodos", basic_stats['num_nodes'])
        with col2:
            st.metric("Autores", basic_stats['num_authors'])
        with col3:
            st.metric("Artículos", basic_stats['num_articles'])
        with col4:
            st.metric("Conexiones", basic_stats['num_edges'])
    st.markdown("---")

    # Estadísticas y Top autores
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📈 Estadísticas del Grafo")
            st.metric("Densidad del Grafo", f"{basic_stats['density']:.4f}")
            st.metric("Grado Promedio", f"{basic_stats['avg_degree']:.2f}")
            components_info = metrics_cache.get_components_info()
            if graph.is_directed():
                st.metric("Componentes Débilmente Conectados", components_info['num_components'])
            else:
                st.metric("Componentes Conectados", components_info['num_components'])
        with col2:
            st.subheader("🏆 Top Autores por Conexiones")
            top_authors = metrics_cache.get_top_nodes_by_degree('author', 10)
            if top_authors:
                df_data = []
                for author_id, connections in top_authors:
                    if author_id in graph.nodes():
                        author_data = graph.nodes[author_id]
                        display_name = author_data.get('display_name', author_id)
                        df_data.append({'Autor': display_name, 'Conexiones': connections})
                df_top = pd.DataFrame(df_data)
                st.dataframe(df_top, use_container_width=True, hide_index=True)
            else:
                st.info("No hay datos de autores disponibles")
    st.markdown("---")

    # Distribución de grados
    with st.container():
        st.subheader("📊 Distribución de Grados")
        if basic_stats['num_nodes'] > 0:
            degree_dist = metrics_cache.get_degree_distribution()
            degree_values = metrics_cache.degree_values
            fig = px.histogram(
                x=degree_values,
                nbins=min(20, degree_dist['unique_degrees']),
                title="Distribución de Grados en el Grafo",
                labels={'x': 'Grado', 'y': 'Frecuencia'}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay suficientes enlaces para realizar interpretaciones detalladas")


def fast_top_k_degree_nodes(graph, k=10):
    return heapq.nlargest(k, graph.degree, key=lambda x: x[1])

def fast_articulation_points(graph, max_points=10):
    try:
        gen = nx.articulation_points(graph)
        return [next(gen) for _ in range(max_points)]
    except StopIteration:
        return []
    except Exception:
        return []

def show_author_graph_overview(graph):
    """Muestra información general del grafo autor-autor"""
    if graph is None:
        st.warning("⚠️ No se pudo cargar el grafo autor-autor")
        st.info("Este grafo se genera automáticamente basado en colaboraciones entre autores.")
        return

    st.header("👥 Grafo Autor-Autor: Red de Colaboraciones")
    st.markdown("Este grafo muestra las relaciones de colaboración entre autores basadas en artículos compartidos.")
    st.markdown("---")

    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()
    density = nx.density(graph)
    if graph.is_directed():
        num_components = nx.number_weakly_connected_components(graph)
    else:
        num_components = nx.number_connected_components(graph)

    # Métricas principales agrupadas
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Autores", num_nodes)
        with col2:
            st.metric("Colaboraciones", num_edges)
        with col3:
            st.metric("Densidad", f"{density:.4f}")
        with col4:
            st.metric("Componentes", num_components)
    st.markdown("---")

    if num_edges == 0:
        st.info("👥 No hay colaboraciones entre autores en este grafo")
        return

    degrees = dict(graph.degree())
    degree_values = np.fromiter(degrees.values(), dtype=int)
    max_collaborations = degree_values.max() if degree_values.size else 0
    min_collaborations = degree_values.min() if degree_values.size else 0
    avg_collaborations = degree_values.mean() if degree_values.size else 0

    # Estadísticas y Top colaboradores
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔍 Análisis de Colaboraciones")
            st.metric("Máximo de Colaboraciones", max_collaborations)
            st.metric("Mínimo de Colaboraciones", min_collaborations)
            st.metric("Promedio de Colaboraciones", f"{avg_collaborations:.1f}")
            with st.expander("Autores actúan como puentes críticos (muestra)",expanded=False):
                if not graph.is_directed():
                    art_points = fast_articulation_points(graph, max_points=10)
                    if art_points:
                        df_bridges = pd.DataFrame({
                            'Autor': [graph.nodes[n].get('display_name', n) for n in art_points],
                            'Colaboraciones': [degrees[n] for n in art_points]
                        })
                        st.dataframe(df_bridges, use_container_width=True, hide_index=True)
                    else:
                        st.info("🔗 No hay autores puentes críticos identificados (o muestra vacía)")
                isolated_count = int(np.sum(degree_values == 0))
                if isolated_count > 0:
                    st.warning(f"⚠️ {isolated_count} autores están aislados")
        with col2:
            st.subheader("🤝 Top Colaboradores")
            
            top_collaborators = fast_top_k_degree_nodes(graph, 10)
            if top_collaborators:
                    df_collab = pd.DataFrame({
                        'Autor': [graph.nodes[n].get('display_name', n) for n, _ in top_collaborators],
                        'Colaboraciones': [d for _, d in top_collaborators]
                    })
                    st.dataframe(df_collab, use_container_width=True, hide_index=True)
            else:
                    st.info("No hay datos de colaboración disponibles")
    st.markdown("---")

    # Distribución de colaboraciones
    with st.container():
        st.subheader("📊 Distribución de Colaboraciones")
        fig = px.histogram(
            x=degree_values,
            nbins=min(15, len(np.unique(degree_values))),
            title="Distribución de Número de Colaboraciones",
            labels={'x': 'Número de Colaboraciones', 'y': 'Frecuencia'}
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

def show_article_graph_overview(graph):
    """Muestra información general del grafo artículo-artículo con optimizaciones avanzadas"""
    st.header("📄 Grafo Artículo-Artículo: Red de Coautorías")
    st.markdown("Este grafo muestra las relaciones entre artículos que comparten autores en común.")
    st.markdown("---")

    if graph is None:
        st.warning("⚠️ No se pudo cargar el grafo artículo-artículo")
        st.info("Este grafo se genera automáticamente basado en artículos que comparten autores.")
        return

    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()
    density = nx.density(graph)
    if graph.is_directed():
        num_components = nx.number_weakly_connected_components(graph)
    else:
        num_components = nx.number_connected_components(graph)

    # Métricas principales agrupadas
    with st.container():
        st.subheader("📌 Resumen General")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Artículos", num_nodes)
        with col2:
            st.metric("Conexiones", num_edges)
        with col3:
            st.metric("Densidad", f"{density:.4f}")
        with col4:
            st.metric("Componentes", num_components)
    st.markdown("---")

    if num_edges == 0:
        st.info("📄 No hay conexiones entre artículos en este grafo")
        return

    degrees = dict(graph.degree())
    degree_values = np.fromiter(degrees.values(), dtype=int)
    max_connections = degree_values.max() if degree_values.size else 0
    min_connections = degree_values.min() if degree_values.size else 0
    avg_connections = degree_values.mean() if degree_values.size else 0
    edge_data = graph.edges(data=True)
    has_weights = any('weight' in data for _, _, data in edge_data)
    if has_weights:
        weights = np.fromiter((data.get('weight', 1) for _, _, data in edge_data), dtype=float)
        avg_weight = weights.mean()
        max_weight = weights.max()
    else:
        avg_weight = None
        max_weight = None

    # Estadísticas y Top artículos
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 Estadísticas del Grafo")
            st.metric("Máximo de Conexiones", max_connections)
            st.metric("Mínimo de Conexiones", min_connections)
            st.metric("Promedio de Conexiones", f"{avg_connections:.1f}")
            if avg_weight is not None:
                st.metric("Peso Promedio", f"{avg_weight:.1f}")
                st.metric("Máximo Autores Compartidos", int(max_weight))
        with col2:
            st.subheader("📰 Top Artículos por Conexiones")
            top_articles = fast_top_k_degree_nodes(graph, 10)
            if top_articles:
                df_top = pd.DataFrame({
                    'Artículo': [graph.nodes[n].get('title', graph.nodes[n].get('display_name', n)) for n, _ in top_articles],
                    'Conexiones': [d for _, d in top_articles]
                })
                st.dataframe(df_top, use_container_width=True, hide_index=True)
            else:
                st.info("No hay datos de conexiones disponibles")
    st.markdown("---")

    with st.container():
        st.subheader("🔗 Análisis de Agrupaciones por Coautoría")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**🌐 Estructura de la Red:**")
            if num_components == 1:
                st.write("• Red completamente conectada de artículos")
                try:
                    if not graph.is_directed() and num_nodes > 2:
                        clustering = nx.average_clustering(graph)
                        st.write(f"• **Coeficiente de Clustering:** {clustering:.4f}")
                        if clustering > 0.3:
                            st.write("• Alta formación de clusters por coautoría")
                        elif clustering > 0.1:
                            st.write("• Moderada agrupación por coautoría")
                        else:
                            st.write("• Baja agrupación por coautoría")
                except:
                    st.write("• Coeficiente de clustering no calculable")
            else:
                st.write(f"• **{num_components} grupos de coautoría separados**")
                components = sorted((len(c) for c in nx.connected_components(graph)), reverse=True)
                
                component_data = []
                for i, size in enumerate(components[:10]):
                    component_data.append({
                        'Componente': f"Componente {i+1}",
                        'Artículos': int(size),
                        'Porcentaje': f"{(size/num_nodes)*100:.1f}%"
                    })
                st.write("**🏆 Top 10 Componentes:**")
                df_components = pd.DataFrame(component_data)
                st.dataframe(df_components, use_container_width=True, hide_index=True)
        with col2:
            st.write("**📚 Patrones de Coautoría:**")
            if has_weights:
                strong_count = int(np.sum(weights >= 3))
                medium_count = int(np.sum((weights >= 2) & (weights < 3)))
                weak_count = int(np.sum(weights == 1))
                total_count = len(weights)
                st.write(f"• **Coautorías intensas:** {strong_count} ({(strong_count/total_count)*100:.1f}%)")
                st.write(f"• **Coautorías moderadas:** {medium_count} ({(medium_count/total_count)*100:.1f}%)")
                st.write(f"• **Coautorías ocasionales:** {weak_count} ({(weak_count/total_count)*100:.1f}%)")
            else:
                st.write("• Todas las conexiones tienen peso unitario")
            isolated_count = int(np.sum(degree_values == 0))
            if isolated_count > 0:
                st.warning(f"⚠️ {isolated_count} artículos están aislados")
    st.markdown("---")

    with st.container():
        st.subheader("📊 Distribución de Conexiones")
        fig = px.histogram(
            x=degree_values,
            nbins=min(15, len(np.unique(degree_values))),
            title="Distribución de Conexiones por Coautoría",
            labels={'x': 'Número de Conexiones', 'y': 'Frecuencia'}
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

def show_pdf_graph_overview(graph):
    """Muestra información general del grafo de PDFs procesados"""
    if graph is None:
        st.error("❌ No se pudo cargar el grafo de PDFs")
        return

    st.header("📑 Grafo de PDFs: Datos Extraídos de Documentos")
    st.markdown("Este grafo representa las relaciones entre autores y artículos extraídos de documentos PDF procesados localmente.")
    st.markdown("---")

    metrics_cache = GraphMetricsCache(graph)
    basic_stats = metrics_cache.get_basic_stats()

    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Nodos", basic_stats['num_nodes'])
        with col2:
            st.metric("Autores", basic_stats['num_authors'])
        with col3:
            st.metric("Artículos (PDFs)", basic_stats['num_articles'])
        with col4:
            st.metric("Conexiones", basic_stats['num_edges'])
    
    st.markdown("---")

    # Estadísticas y Top autores específicas para PDFs
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📈 Estadísticas del Grafo PDF")
            st.metric("Densidad del Grafo", f"{basic_stats['density']:.4f}")
            st.metric("Grado Promedio", f"{basic_stats['avg_degree']:.2f}")
            components_info = metrics_cache.get_components_info()
            if graph.is_directed():
                st.metric("Componentes Débilmente Conectados", components_info['num_components'])
            else:
                st.metric("Componentes Conectados", components_info['num_components'])
                
            # Mostrar información específica de PDFs
            st.info("📄 **Fuente de datos**: Documentos PDF procesados localmente")
            
        with col2:
            st.subheader("🏆 Top Autores en PDFs")
            top_authors = metrics_cache.get_top_nodes_by_degree('author', 10)
            if top_authors:
                df_data = []
                for author_id, connections in top_authors:
                    if author_id in graph.nodes():
                        author_data = graph.nodes[author_id]
                        display_name = author_data.get('display_name', author_id)
                        df_data.append({'Autor': display_name, 'Conexiones': connections})
                df_top = pd.DataFrame(df_data)
                st.dataframe(df_top, use_container_width=True, hide_index=True)
            else:
                st.info("No hay datos de autores disponibles en los PDFs")
    
    st.markdown("---")

    # Distribución de grados específica para PDFs
    with st.container():
        st.subheader("📊 Distribución de Grados en PDFs")
        if basic_stats['num_nodes'] > 0:
            degree_dist = metrics_cache.get_degree_distribution()
            degree_values = metrics_cache.degree_values
            fig = px.histogram(
                x=degree_values,
                nbins=min(20, degree_dist['unique_degrees']),
                title="Distribución de Grados en Documentos PDF",
                labels={'x': 'Grado', 'y': 'Frecuencia'}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay suficientes enlaces para mostrar la distribución")
    
    # Información adicional específica de PDFs
    with st.container():
        st.subheader("📑 Información de Procesamiento de PDFs")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔍 Características del Grafo PDF:**")
            st.markdown(f"• **{basic_stats['num_articles']}** documentos PDF procesados")
            st.markdown(f"• **{basic_stats['num_authors']}** autores identificados")
            st.markdown(f"• **{basic_stats['num_edges']}** relaciones autor-documento")
            
        with col2:
            st.markdown("**📊 Métricas de Calidad:**")
            if basic_stats['num_nodes'] > 0:
                articles_per_author = basic_stats['num_articles'] / max(basic_stats['num_authors'], 1)
                st.markdown(f"• **{articles_per_author:.1f}** artículos promedio por autor")
                
                if basic_stats['avg_degree'] > 0:
                    st.markdown(f"• **{basic_stats['avg_degree']:.1f}** conexiones promedio")
                
                if components_info['num_components'] == 1:
                    st.markdown("• ✅ Grafo completamente conectado")
                else:
                    st.markdown(f"• ⚠️ {components_info['num_components']} componentes separados")
            else:
                st.markdown("• No hay métricas disponibles")

