import networkx as nx 
import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import hashlib
import warnings
warnings.filterwarnings('ignore')



def get_graph_signature(graph):
    """Genera una firma única para el grafo"""
    try:
        basic_info = {
            'nodes': len(graph.nodes()),
            'edges': len(graph.edges()),
            'directed': graph.is_directed()
        }
        
        edges_sample = list(graph.edges())
        if len(edges_sample) > 10000:
            step = len(edges_sample) // 5000
            edges_sample = edges_sample[::step]
        
        edges_str = str(sorted(edges_sample))
        structure_hash = hashlib.md5(edges_str.encode()).hexdigest()[:8]
        
        return f"{basic_info['nodes']}_{basic_info['edges']}_{structure_hash}"
    except:
        return f"{len(graph.nodes())}_{len(graph.edges())}_{int(time.time())}"

def get_cached_metrics(graph, graph_type, metric_type):
    """Obtiene métricas del caché o retorna None"""
    signature = get_graph_signature(graph)
    cache_key = f"{graph_type}_{metric_type}_{signature}"
    
    if cache_key in st.session_state.metrics_cache:
        cached_data = st.session_state.metrics_cache[cache_key]

        age_hours = (time.time() - cached_data['timestamp']) / 3600
        if age_hours:
            return cached_data['metrics']
    return None

def cache_metrics(graph, graph_type, metric_type, metrics):
    """Guarda métricas en el caché"""
    signature = get_graph_signature(graph)
    cache_key = f"{graph_type}_{metric_type}_{signature}"
    
    st.session_state.metrics_cache[cache_key] = {
        'metrics': metrics,
        'timestamp': time.time(),
        'signature': signature
    }
    
    if len(st.session_state.metrics_cache) > 100:
        clean_old_cache()

def clean_old_cache():
    """Limpia entradas viejas del caché"""
    current_time = time.time()
    keys_to_remove = []
    
    for key, data in st.session_state.metrics_cache.items():
        age_hours = (current_time - data['timestamp']) / 3600
        if age_hours > 48:  
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del st.session_state.metrics_cache[key]


def create_sampling_ui(graph, graph_type):
    """Crea interfaz de muestreo según el tipo de grafo"""
    st.markdown("### 🎯 Configuración de Muestreo")
    
    total_nodes = len(graph.nodes())
    
    if graph_type == "author":
        # Para grafo autor-autor: solo muestreo aleatorio
        st.markdown("#### 🤝 Red de Colaboración - Muestreo Aleatorio")
        
        with st.expander("⚙️ Configuración de Muestreo", expanded=True):
            col1, col2 = st.columns(2)
            
            
            st.info(f"**Total de autores:** {total_nodes:,}")
                
            random_node_count = st.number_input(
                    "Cantidad de autores a analizar:",
                    min_value=10,
                    max_value=total_nodes,
                    value=min(1000, total_nodes // 2) if total_nodes > 0 else 100,
                    help="Seleccionar cantidad específica de autores al azar"
                )
                
            if total_nodes > 0:
                    percentage = (random_node_count / total_nodes) * 100
                    st.metric("📊 Porcentaje del total", f"{percentage:.1f}%")
            
        return {
            'random_node_count': random_node_count,
            'filter_type': 'random_authors'
        }
    
    else:
        st.markdown("#### 📊 Grafo Bipartito - Opciones de Filtrado")
        
        with st.expander("⚙️ Filtros", expanded=True):
            st.markdown("**🎯 Tipo de Filtrado**")
            filter_type = st.selectbox(
                "Método de filtrado:",
                ["Cantidad específica al azar", "Por artículos aleatorios"],
                help="Elige cómo filtrar los nodos"
            )
            
            if filter_type == "Cantidad específica al azar":
                random_node_count = st.number_input(
                    "Cantidad de nodos:",
                    min_value=10,
                    max_value=total_nodes,
                    value=min(1000, total_nodes // 2) if total_nodes > 0 else 100,
                    help="Seleccionar cantidad específica de nodos al azar"
                )
                
                if total_nodes > 0:
                    percentage = (random_node_count / total_nodes) * 100
                    st.metric("📊 Porcentaje del total", f"{percentage:.1f}%")
                    st.metric("🎲 Selección", "Aleatoria")
                
                article_count = None
                selected_article_authors = None
            
            else:  
                article_nodes = [n for n, d in graph.nodes(data=True) 
                               if d.get('node_type', '').lower() in ['articulo', 'article']]
                total_articles = len(article_nodes)
                
                article_count = st.number_input(
                    "Cantidad de artículos:",
                    min_value=1,
                    max_value=total_articles if total_articles > 0 else 1,
                    value=min(100, total_articles) if total_articles > 0 else 1,
                    help="Seleccionar cantidad de artículos aleatorios"
                )

                selected_article_authors = []
                if total_articles > 0 and article_count > 0:
                    selected_articles = np.random.choice(article_nodes, article_count, replace=False)
                    for art in selected_articles:
                        neighbors = list(graph.neighbors(art))
                        selected_article_authors.extend(neighbors)
                    selected_article_authors = list(set(selected_article_authors))
                    
                    st.metric("📰 Artículos seleccionados", len(selected_articles))
                    st.metric("👥 Autores únicos", len(selected_article_authors))
                
                random_node_count = None
        
        return {
            'filter_type': filter_type,
            'random_node_count': random_node_count,
            'article_count': article_count,
            'selected_article_authors': selected_article_authors
        }

def apply_sampling_filters(graph, filters):
    """Aplica filtros de muestreo optimizados al grafo"""
    filtered_graph = graph.copy()

    filter_type = filters.get('filter_type', 'random_authors')
    
    if filter_type == 'random_authors':

        if filters.get('random_node_count') is not None:
            all_nodes = list(graph.nodes())
            random_count = min(filters['random_node_count'], len(all_nodes))
            
            if random_count < len(all_nodes):
                selected_nodes = np.random.choice(all_nodes, random_count, replace=False)
                filtered_graph = graph.subgraph(selected_nodes).copy()
    
    elif filter_type == 'Cantidad específica al azar':

        if filters.get('random_node_count') is not None:
            all_nodes = list(graph.nodes())
            random_count = min(filters['random_node_count'], len(all_nodes))
            
            if random_count < len(all_nodes):
                selected_nodes = np.random.choice(all_nodes, random_count, replace=False)
                filtered_graph = graph.subgraph(selected_nodes).copy()
    
    elif filter_type == 'Por artículos aleatorios':
        if filters.get('selected_article_authors') is not None and len(filters['selected_article_authors']) > 0:
            filtered_graph = graph.subgraph(filters['selected_article_authors']).copy()
    
    return filtered_graph



def calculate_fast_metrics_cached(graph, graph_type):
    """Calcula métricas básicas con caché"""
    cached = get_cached_metrics(graph, graph_type, "basic_metrics")
    if cached:
        return cached
    
    # Calcular métricas básicas
    n_nodes = len(graph.nodes())
    n_edges = len(graph.edges())
    
    if n_nodes == 0:
        return {}
    
    try:
        degrees = np.array([graph.degree(n) for n in graph.nodes()])
        
        metrics = {
            'n_nodes': n_nodes,
            'n_edges': n_edges,
            'density': nx.density(graph),
            'avg_degree': float(degrees.mean()) if len(degrees) > 0 else 0.0,
            'degree_std': float(degrees.std()) if len(degrees) > 0 else 0.0,
            'max_degree': int(degrees.max()) if len(degrees) > 0 else 0,
            'min_degree': int(degrees.min()) if len(degrees) > 0 else 0,
            'degree_cv': float(degrees.std() / degrees.mean()) if degrees.mean() > 0 else 0.0,
            'n_components': nx.number_connected_components(graph) if not graph.is_directed() else nx.number_strongly_connected_components(graph),
            'is_connected': nx.is_connected(graph) if not graph.is_directed() else nx.is_strongly_connected(graph),
            'transitivity': nx.transitivity(graph) or 0.0,
            'avg_clustering': nx.average_clustering(graph) or 0.0
        }
        
        if metrics['is_connected']:
            try:
                metrics['diameter'] = nx.diameter(graph)
                metrics['radius'] = nx.radius(graph)
                metrics['avg_path_length'] = nx.average_shortest_path_length(graph)
            except:
                metrics['diameter'] = 0
                metrics['radius'] = 0
                metrics['avg_path_length'] = 0.0
        else:
            metrics['diameter'] = 0
            metrics['radius'] = 0
            metrics['avg_path_length'] = 0.0

        for key, value in metrics.items():
            if value is None or (isinstance(value, float) and np.isnan(value)):
                if key in ['n_nodes', 'n_edges', 'max_degree', 'min_degree', 'n_components', 'diameter', 'radius']:
                    metrics[key] = 0
                else:
                    metrics[key] = 0.0
        
        cache_metrics(graph, graph_type, "basic_metrics", metrics)
        return metrics
        
    except Exception as e:
        # En caso de error, retornar métricas básicas completas
        return {
            'n_nodes': n_nodes,
            'n_edges': n_edges,
            'density': 0.0,
            'avg_degree': 0.0,
            'degree_std': 0.0,
            'max_degree': 0,
            'min_degree': 0,
            'degree_cv': 0.0,
            'n_components': 1,
            'is_connected': False,
            'transitivity': 0.0,
            'avg_clustering': 0.0,
            'diameter': 0,
            'radius': 0,
            'avg_path_length': 0.0
        }

def show_network_analysis_optimized():
    """Análisis avanzado de patrones de red"""
    
    # Header profesional
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <h1 style="color: white; text-align: center; margin: 0; font-weight: 700;">
            🔬 Análisis de Patrones de Red
        </h1>
        <p style="color: rgba(255,255,255,0.9); text-align: center; margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            Sistema de Análisis • Muestreo • Métricas
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Selector de grafo
    st.markdown("### 🎯 Selección de Grafo")
    
    graph_options = {}
    
    # Grafo principal
    if st.session_state.graph is not None and len(st.session_state.graph.nodes()) > 0:
        graph_options[f"📊 Grafo Bipartito ({len(st.session_state.graph.nodes()):,} nodos)"] = ("main", st.session_state.graph)
    
    # Grafo de colaboración
    if hasattr(st.session_state, 'author_graph') and st.session_state.author_graph is not None and len(st.session_state.author_graph.nodes()) > 0:
        graph_options[f"🤝 Red de Colaboración ({len(st.session_state.author_graph.nodes()):,} nodos)"] = ("author", st.session_state.author_graph)
    
    if not graph_options:
        st.error("⚠️ No hay datos en ningún grafo para analizar")
        st.info("💡 Ve a la sección 'Explorar mi Red' para cargar datos o generar la red de colaboración")
        return
    
    selected_graph_key = st.selectbox(
        "Selecciona el grafo que deseas analizar:",
        options=list(graph_options.keys()),
        help="Elige entre el grafo bipartito o la red de colaboración"
    )
    
    graph_type, graph = graph_options[selected_graph_key]
    
    st.markdown("---")
    
    # Interfaz de muestreo según tipo de grafo
    sampling_filters = create_sampling_ui(graph, graph_type)
    
    # Botón principal para calcular
    if st.button("🚀 Calcular Análisis Completo", type="primary", help="Aplica el muestreo y calcula todas las métricas"):
        with st.spinner("⚡ Aplicando muestreo y preparando análisis..."):
            # Aplicar filtros de muestreo
            filtered_graph = apply_sampling_filters(graph, sampling_filters)
            
            # Guardar el grafo filtrado en session state para uso en pestañas
            st.session_state.filtered_graph = filtered_graph
            st.session_state.original_graph = graph
            st.session_state.current_filters = sampling_filters
            st.session_state.current_graph_type = graph_type
            
            st.success(f"✅ Muestreo completado: {len(filtered_graph.nodes()):,} nodos seleccionados de {len(graph.nodes()):,} totales")
    
    # Mostrar análisis solo si hay un grafo filtrado
    if hasattr(st.session_state, 'filtered_graph') and st.session_state.filtered_graph is not None:
        filtered_graph = st.session_state.filtered_graph
        original_graph = st.session_state.original_graph
        filters = st.session_state.current_filters
        graph_type = st.session_state.current_graph_type
        
        st.markdown("---")
        
        # Análisis principal con tabs optimizadas
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎯 Análisis Estructural", 
            "🎲 Comparación Aleatoria", 
            "🛡️ Resiliencia & Robustez",
            "🌐 Comunidades & Difusión", 
            "⚡ Métricas"
        ])
        
        with tab1:
            show_structural_analysis_cached(filtered_graph, graph_type)
        
        with tab2:
            show_random_comparison_cached(filtered_graph, graph_type)
        
        with tab3:
            show_resilience_analysis_cached(filtered_graph, graph_type)
        
        with tab4:
            show_community_diffusion_analysis_cached(filtered_graph, graph_type)
        
        with tab5:
            show_advanced_metrics_cached(filtered_graph, graph_type)
    
    else:
        st.markdown("### 📊 Configuración de Análisis")
        st.markdown("Configura el muestreo arriba y presiona '🚀 Calcular Análisis Completo' para comenzar el análisis")

def show_structural_analysis_cached(graph, graph_type):
    """Análisis estructural con caché"""
    
    if graph_type == "main":
        st.markdown("### 📊 Análisis Estructural - Grafo Bipartito")
    else:
        st.markdown("### 🤝 Análisis Estructural - Red de Colaboración")
    
    with st.spinner("📊 Calculando métricas estructurales..."):
        basic_metrics = calculate_fast_metrics_cached(graph, graph_type)
    
    if not basic_metrics:
        st.warning("⚠️ No se pudieron calcular las métricas básicas")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🔗 Nodos", f"{basic_metrics['n_nodes']:,}")
        st.metric("🌐 Aristas", f"{basic_metrics['n_edges']:,}")
    
    with col2:
        st.metric("📊 Densidad", f"{basic_metrics['density']:.6f}")
        st.metric("📈 Grado Promedio", f"{basic_metrics['avg_degree']:.2f}")
    
    with col3:
        st.metric("⚖️ Coef. Variación", f"{basic_metrics['degree_cv']:.3f}")
        st.metric("🔺 Componentes", basic_metrics['n_components'])
    
    with col4:
        st.metric("🔄 Conectado", "Sí" if basic_metrics['is_connected'] else "No")
        if 'transitivity' in basic_metrics:
            st.metric("🔺 Transitividad", f"{basic_metrics['transitivity']:.4f}")
    
    show_degree_analysis_cached(graph, graph_type)

def show_degree_analysis_cached(graph, graph_type):
    """Análisis de distribución de grados con caché"""
    st.markdown("#### 📈 Análisis de Conectividad")
    
    # Verificar caché
    cached = get_cached_metrics(graph, graph_type, "degree_analysis")
    if cached:
        degrees = cached['degrees']
        degree_dist = cached['degree_distribution']
    else:
        degrees = np.array([graph.degree(n) for n in graph.nodes()])
        unique_degrees, counts = np.unique(degrees, return_counts=True)
        
        degree_data = {
            'degrees': degrees,
            'degree_distribution': {
                'unique_degrees': unique_degrees,
                'counts': counts
            }
        }
        
        cache_metrics(graph, graph_type, "degree_analysis", degree_data)
        degree_dist = degree_data['degree_distribution']
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = create_degree_distribution_plot(degree_dist)
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.markdown("**📊 Estadísticas de Grado:**")
        st.metric("Media", f"{degrees.mean():.2f}")
        st.metric("Mediana", f"{np.median(degrees):.2f}")
        st.metric("Máximo", f"{degrees.max()}")
        st.metric("Desv. Est.", f"{degrees.std():.2f}")
        
        # Análisis de ley de potencias
        if len(degree_dist['unique_degrees']) > 5:
            power_law_exp = analyze_power_law_fast(degree_dist)
            st.metric("Exp. Potencia", f"{power_law_exp:.2f}")

def create_degree_distribution_plot(degree_dist):
    """Crea gráfico optimizado de distribución de grados"""
    unique_degrees = degree_dist['unique_degrees']
    counts = degree_dist['counts']
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Distribución', 'Escala Log-Log'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    fig.add_trace(
        go.Bar(x=unique_degrees, y=counts, name="Frecuencia", 
               marker_color='#667eea', showlegend=False),
        row=1, col=1
    )
    
    # Gráfico log-log
    valid_idx = (unique_degrees > 0) & (counts > 0)
    if np.sum(valid_idx) > 1:
        fig.add_trace(
            go.Scatter(
                x=unique_degrees[valid_idx], 
                y=counts[valid_idx],
                mode='markers+lines',
                name="Log-Log",
                marker=dict(color='#764ba2', size=6),
                showlegend=False
            ),
            row=1, col=2
        )
        
        fig.update_xaxes(title_text="Grado (log)", type="log", row=1, col=2)
        fig.update_yaxes(title_text="Frecuencia (log)", type="log", row=1, col=2)
    
    fig.update_xaxes(title_text="Grado", row=1, col=1)
    fig.update_yaxes(title_text="Frecuencia", row=1, col=1)
    
    fig.update_layout(height=400, template="plotly_white")
    
    return fig

def analyze_power_law_fast(degree_dist):
    """Análisis rápido de ley de potencias"""
    unique_degrees = degree_dist['unique_degrees']
    counts = degree_dist['counts']
    
    # Filtrar valores válidos para log
    valid_idx = (unique_degrees > 0) & (counts > 0)
    
    if np.sum(valid_idx) < 3:
        return 0.0
    
    log_degrees = np.log(unique_degrees[valid_idx])
    log_counts = np.log(counts[valid_idx])
    
    # Regresión lineal simple
    slope, _ = np.polyfit(log_degrees, log_counts, 1)
    
    return abs(slope)

def show_random_comparison_cached(graph, graph_type):
    """Comparación con modelos aleatorios"""
    st.markdown("### 🎲 Comparación con Modelos Aleatorios")
    
    # Verificar si ya hay resultados en caché
    cached = get_cached_metrics(graph, graph_type, "random_comparison")
    
    if cached:
        st.info("✅ Usando resultados en caché")
        display_comparison_results_cached(graph, cached)
        
        # Botón para limpiar caché y rehacer análisis
        if st.button("🔄 Rehacer Análisis", help="Limpia el caché y ejecuta nuevo análisis"):
            # Limpiar caché específico
            signature = get_graph_signature(graph)
            cache_key = f"{graph_type}_random_comparison_{signature}"
            if cache_key in st.session_state.metrics_cache:
                del st.session_state.metrics_cache[cache_key]
            try:
                st.experimental_rerun()
            except:
                st.rerun()
        return
    
    n_nodes = len(graph.nodes())
    n_edges = len(graph.edges())
    
    # Información del grafo actual
    st.markdown("#### 📊 Información del Grafo Original")
    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
    
    with col_info1:
        st.metric("🔗 Nodos", f"{n_nodes:,}")
    with col_info2:
        st.metric("🌐 Aristas", f"{n_edges:,}")
    with col_info3:
        density = nx.density(graph)
        st.metric("📊 Densidad", f"{density:.6f}")
    with col_info4:
        avg_degree = 2 * n_edges / n_nodes if n_nodes > 0 else 0
        st.metric("📈 Grado Promedio", f"{avg_degree:.2f}")
    
    st.markdown("---")
    
    # Configuración expandida de modelos
    st.markdown("#### ⚙️ Configuración de Modelos")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Modelos disponibles según tipo de grafo
        if graph_type == "main":
            st.markdown("**📊 Modelos para Grafo Bipartito:**")
            available_models = [
                "Erdős–Rényi", 
                "Configuration Model",
                "Modelo de Crecimiento"
            ]
            default_models = ["Erdős–Rényi", "Configuration Model"]
        else:
            st.markdown("**🤝 Modelos para Red de Colaboración:**")
            available_models = [
                "Erdős–Rényi", 
                "Barabási–Albert", 
                "Watts-Strogatz",
                "Configuration Model",
                "Modelo de Crecimiento",
                "Modelo de Introducción",
                "Modelo Geográfico Estático",
                "Modelo de Encuentros Aleatorios"
            ]
            default_models = ["Erdős–Rényi", "Barabási–Albert", "Watts-Strogatz"]
        
        models = st.multiselect(
            "Selecciona modelos a comparar:",
            available_models,
            default=default_models,
            help="Elige uno o más modelos de red aleatoria para comparar"
        )
        
        if models:
            with st.expander("ℹ️ Información sobre Modelos Seleccionados", expanded=False):
                for model in models:
                    if model == "Configuration Model":
                        st.markdown("**🔧 Configuration Model:** Preserva exactamente la secuencia de grados del grafo original, pero redistribuye las conexiones aleatoriamente. Útil para determinar si las propiedades son solo consecuencia de la distribución de grados.")
                    elif model == "Erdős–Rényi":
                        st.markdown("**🎲 Erdős–Rényi:** Modelo más simple donde cada par de nodos se conecta con probabilidad p. Genera grafos completamente aleatorios.")
                    elif model == "Barabási–Albert":
                        st.markdown("**📈 Barabási–Albert:** Modelo de crecimiento con enlace preferencial. Los nodos nuevos se conectan preferentemente a nodos ya muy conectados, generando distribuciones de ley de potencia.")
                    elif model == "Watts-Strogatz":
                        st.markdown("**🌐 Watts-Strogatz:** Modelo de 'mundo pequeño' que interpola entre redes regulares y aleatorias, manteniendo alto clustering pero caminos cortos.")
                    elif model == "Modelo de Crecimiento":
                        st.markdown("**🌱 Modelo de Crecimiento:** Los nodos se agregan progresivamente en el tiempo, cada uno conectándose a nodos existentes.")
                    elif model == "Modelo de Introducción":
                        st.markdown("**🤝 Modelo de Introducción:** Nuevas conexiones se hacen preferentemente a través de amigos comunes, simulando introducciones sociales.")
                    elif model == "Modelo Geográfico Estático":
                        st.markdown("**🗺️ Modelo Geográfico:** Cada nodo se conecta a sus vecinos más cercanos en un espacio geográfico, simulando restricciones espaciales.")
                    elif model == "Modelo de Encuentros Aleatorios":
                        st.markdown("**⚡ Modelo de Encuentros:** Los nodos se mueven aleatoriamente y se conectan cuando se 'encuentran', simulando dinámicas de movilidad.")
        
        # Configuraciones adicionales
        if models:
            st.markdown("**🎛️ Configuraciones Avanzadas:**")
            
            advanced_config = {}
            
            if "Erdős–Rényi" in models:
                # Calcular probabilidad por defecto basada en densidad actual
                default_p = 2 * n_edges / (n_nodes * (n_nodes - 1)) if n_nodes > 1 else 0.01
                advanced_config['er_p'] = st.slider(
                    "Probabilidad de enlace (Erdős–Rényi):",
                    0.001, 0.5, min(default_p, 0.1), 0.001,
                    help="Probabilidad de que dos nodos estén conectados",
                    format="%.3f"
                )
                st.info(f"Probabilidad del grafo original: {default_p:.4f}")
            
            if "Watts-Strogatz" in models:
                advanced_config['ws_p'] = st.slider(
                    "Probabilidad de reconexión (Watts-Strogatz):",
                    0.0, 1.0, 0.1, 0.05,
                    help="Probabilidad de reconectar aristas en el modelo Watts-Strogatz"
                )
                advanced_config['ws_k'] = st.slider(
                    "Vecinos iniciales (Watts-Strogatz):",
                    2, min(20, n_nodes//2), min(6, n_nodes//3), 2,
                    help="Número de vecinos más cercanos en el anillo inicial"
                )
            
            if "Modelo de Introducción" in models:
                advanced_config['intro_p'] = st.slider(
                    "Probabilidad de introducción:",
                    0.0, 1.0, 0.3, 0.05,
                    help="Probabilidad de conectarse a través de amigos comunes"
                )
            
            if "Modelo Geográfico Estático" in models:
                advanced_config['geo_neighbors'] = st.slider(
                    "Número de vecinos geográficos:",
                    1, min(10, n_nodes//5), min(3, n_nodes//10), 1,
                    help="Número de nodos más cercanos a los que conectarse"
                )
            
            if "Modelo de Encuentros Aleatorios" in models:
                advanced_config['encounter_prob'] = st.slider(
                    "Probabilidad de encuentro:",
                    0.1, 1.0, 0.5, 0.1,
                    help="Probabilidad de que dos nodos se encuentren y conecten"
                )
    
        
    if not models:
        st.warning("⚠️ Selecciona al menos un modelo para comparar")
        return
    
    if st.button("🚀 Ejecutar Comparación", type="primary"):
        with st.spinner("🎯 Generando modelos y calculando métricas..."):
            comparison_results = perform_random_comparison_optimized(
                graph, models, 30, graph_type, 
                advanced_config if 'advanced_config' in locals() else {},
                metrics_to_compare=None
            )
            
            # Cachear resultados
            cache_metrics(graph, graph_type, "random_comparison", comparison_results)
            
            display_comparison_results_cached(
                graph, comparison_results, 
                show_distributions=None, show_violin_plots=None
            )

def perform_random_comparison_optimized(graph, models, n_samples, graph_type, advanced_config={}, metrics_to_compare=None):
    """Comparación con modelos aleatorios"""
    n_nodes = len(graph.nodes())
    n_edges = len(graph.edges())
    
    # Métricas del grafo original
    original_metrics = calculate_fast_metrics_cached(graph, graph_type)
    
    results = {}
    
    # Progreso de la simulación
    total_simulations = len(models) * n_samples
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    simulation_count = 0
    
    for model in models:
        status_text.text(f"Generando {model}...")
        model_metrics = []
        
        for i in range(n_samples):
            # Generar grafo aleatorio
            random_graph = generate_random_graph_expanded(
                model, n_nodes, n_edges, graph, advanced_config
            )
            
            if random_graph:
                metrics = calculate_basic_metrics_fast_expanded(
                    random_graph, metrics_to_compare
                )
                model_metrics.append(metrics)
            
            # Actualizar progreso
            simulation_count += 1
            progress_bar.progress(simulation_count / total_simulations)
        
        results[model] = model_metrics
    
    # Limpiar elementos de progreso
    progress_bar.empty()
    status_text.empty()
    
    return {
        'original': original_metrics,
        'random_models': results,
        'config': advanced_config,
        'metrics_compared': metrics_to_compare or list(original_metrics.keys())
    }

def generate_random_graph_expanded(model, n_nodes, n_edges, original_graph, config={}):
    """Genera grafo aleatorio según el modelo especificado"""
    try:
        if model == "Erdős–Rényi":
            # Usar probabilidad configurada por el usuario o calcular por defecto
            p = config.get('er_p', 2 * n_edges / (n_nodes * (n_nodes - 1))) if n_nodes > 1 else 0.01
            return nx.erdos_renyi_graph(n_nodes, p)
            
        elif model == "Barabási–Albert":
            m = max(1, min(n_edges // n_nodes, n_nodes - 1))
            return nx.barabasi_albert_graph(n_nodes, m)
            
        elif model == "Watts-Strogatz":
            # Usar configuración del usuario
            k = config.get('ws_k', min(6, n_nodes//3))
            if k % 2 == 1:
                k += 1
            k = max(2, min(k, n_nodes - 1))
            p = config.get('ws_p', 0.1)
            return nx.watts_strogatz_graph(n_nodes, k, p)
            
        elif model == "Configuration Model":
            degree_sequence = [original_graph.degree(n) for n in original_graph.nodes()]
            if sum(degree_sequence) % 2 == 1:
                degree_sequence[-1] += 1
            random_graph = nx.configuration_model(degree_sequence)
            return nx.Graph(random_graph)  # Remover self-loops y multi-edges
            
        elif model == "Modelo de Crecimiento":
            # Modelo de crecimiento simple: nodos se agregan en el tiempo
            G = nx.Graph()
            # Comenzar con unos pocos nodos conectados
            G.add_edges_from([(0, 1), (1, 2), (0, 2)])
            
            # Agregar nodos uno por uno
            m = max(1, min(3, n_edges // n_nodes))  # Enlaces por nodo nuevo
            for new_node in range(3, n_nodes):
                # Conectar a nodos existentes aleatoriamente
                existing_nodes = list(G.nodes())
                targets = np.random.choice(existing_nodes, min(m, len(existing_nodes)), replace=False)
                for target in targets:
                    G.add_edge(new_node, target)
            return G
            
        elif model == "Modelo de Introducción":
            # Modelo donde nuevas conexiones se hacen a través de amigos comunes
            G = nx.erdos_renyi_graph(n_nodes, 0.01)  # Red inicial muy dispersa
            p_intro = config.get('intro_p', 0.3)
            
            # Agregar enlaces adicionales hasta alcanzar el número deseado
            current_edges = G.number_of_edges()
            target_edges = min(n_edges, n_nodes * (n_nodes - 1) // 2)
            
            attempts = 0
            max_attempts = (target_edges - current_edges) * 10
            
            while G.number_of_edges() < target_edges and attempts < max_attempts:
                # Seleccionar dos nodos
                u, v = np.random.choice(n_nodes, 2, replace=False)
                
                if not G.has_edge(u, v):
                    # Con probabilidad p_intro, conectar si tienen amigos comunes
                    common_neighbors = set(G.neighbors(u)) & set(G.neighbors(v))
                    
                    if (len(common_neighbors) > 0 and np.random.random() < p_intro) or \
                       (len(common_neighbors) == 0 and np.random.random() < (1 - p_intro) * 0.1):
                        G.add_edge(u, v)
                
                attempts += 1
            
            return G
            
        elif model == "Modelo Geográfico Estático":
            # Cada nodo se conecta a sus k vecinos más cercanos
            k = config.get('geo_neighbors', min(3, n_nodes//10))
            
            # Generar posiciones aleatorias para nodos
            pos = {i: (np.random.random(), np.random.random()) for i in range(n_nodes)}
            
            G = nx.Graph()
            G.add_nodes_from(range(n_nodes))
            
            # Para cada nodo, conectar a los k más cercanos
            for node in range(n_nodes):
                # Calcular distancias a todos los otros nodos
                distances = []
                for other in range(n_nodes):
                    if other != node:
                        dist = np.sqrt((pos[node][0] - pos[other][0])**2 + 
                                     (pos[node][1] - pos[other][1])**2)
                        distances.append((dist, other))
                
                # Conectar a los k más cercanos
                distances.sort()
                for i in range(min(k, len(distances))):
                    neighbor = distances[i][1]
                    G.add_edge(node, neighbor)
            
            return G
            
        elif model == "Modelo de Encuentros Aleatorios":
            # Nodos se mueven y se conectan cuando se encuentran
            encounter_prob = config.get('encounter_prob', 0.5)
            
            G = nx.Graph()
            G.add_nodes_from(range(n_nodes))
            
            # Simular múltiples rondas de encuentros
            target_edges = min(n_edges, n_nodes * (n_nodes - 1) // 2)
            rounds = 0
            max_rounds = 50
            
            while G.number_of_edges() < target_edges and rounds < max_rounds:
                # En cada ronda, cada par de nodos tiene una probabilidad de encontrarse
                for i in range(n_nodes):
                    for j in range(i + 1, n_nodes):
                        if not G.has_edge(i, j) and np.random.random() < encounter_prob:
                            G.add_edge(i, j)
                            if G.number_of_edges() >= target_edges:
                                break
                    if G.number_of_edges() >= target_edges:
                        break
                rounds += 1
                encounter_prob *= 0.9  # Reducir probabilidad en cada ronda
            
            return G
            
    except Exception as e:
        # Fallback a Erdős–Rényi
        p = 2 * n_edges / (n_nodes * (n_nodes - 1)) if n_nodes > 1 else 0.01
        return nx.erdos_renyi_graph(n_nodes, p)

def calculate_basic_metrics_fast_expanded(graph, metrics_to_compare=None):
    """Calcula métricas básicas con selección opcional"""
    n_nodes = len(graph.nodes())
    n_edges = len(graph.edges())
    
    if n_nodes == 0:
        return {}
    
    try:
        degrees = np.array([graph.degree(n) for n in graph.nodes()])
        
        # Métricas base con manejo de errores
        all_metrics = {
            'n_nodes': n_nodes,
            'n_edges': n_edges,
            'density': nx.density(graph),
            'avg_degree': float(degrees.mean()) if len(degrees) > 0 else 0.0,
            'degree_std': float(degrees.std()) if len(degrees) > 0 else 0.0,
            'max_degree': int(degrees.max()) if len(degrees) > 0 else 0,
            'min_degree': int(degrees.min()) if len(degrees) > 0 else 0,
            'degree_cv': float(degrees.std() / degrees.mean()) if degrees.mean() > 0 else 0.0,
            'n_components': nx.number_connected_components(graph),
            'is_connected': nx.is_connected(graph) if not graph.is_directed() else nx.is_strongly_connected(graph),
            'transitivity': nx.transitivity(graph) or 0.0,
            'avg_clustering': nx.average_clustering(graph) or 0.0
        }
        
        # Métricas adicionales para grafos conectados
        if all_metrics['is_connected']:
            try:
                all_metrics['diameter'] = nx.diameter(graph)
                all_metrics['radius'] = nx.radius(graph)
                all_metrics['avg_path_length'] = nx.average_shortest_path_length(graph)
            except:
                all_metrics['diameter'] = 0
                all_metrics['radius'] = 0
                all_metrics['avg_path_length'] = 0.0
        else:
            all_metrics['diameter'] = 0
            all_metrics['radius'] = 0
            all_metrics['avg_path_length'] = 0.0
        
        # Validar que no hay valores None o NaN
        for key, value in all_metrics.items():
            if value is None or (isinstance(value, float) and np.isnan(value)):
                if key in ['n_nodes', 'n_edges', 'max_degree', 'min_degree', 'n_components', 'diameter', 'radius']:
                    all_metrics[key] = 0
                else:
                    all_metrics[key] = 0.0
        
        # Filtrar métricas si se especifica
        if metrics_to_compare:
            return {k: v for k, v in all_metrics.items() if k in metrics_to_compare}
        
        return all_metrics
        
    except Exception as e:
        # En caso de error, retornar métricas básicas completas
        return {
            'n_nodes': n_nodes,
            'n_edges': n_edges,
            'density': 0.0,
            'avg_degree': 0.0,
            'degree_std': 0.0,
            'max_degree': 0,
            'min_degree': 0,
            'degree_cv': 0.0,
            'n_components': 1,
            'is_connected': False,
            'transitivity': 0.0,
            'avg_clustering': 0.0,
            'diameter': 0,
            'radius': 0,
            'avg_path_length': 0.0
        }

def display_comparison_results_cached(graph, comparison_results, show_distributions=True, show_violin_plots=False):
    """Muestra resultados de comparación con visualización mejorada y expandida"""
    st.markdown("#### 📊 Resultados de Comparación Completa")
    
    original = comparison_results['original']
    models = comparison_results['random_models']
    config = comparison_results.get('config', {})
    metrics_compared = comparison_results.get('metrics_compared', list(original.keys()))
    
    # Información de configuración utilizada
    if config:
        with st.expander("⚙️ Configuración Utilizada", expanded=False):
            st.json(config)
    
    # Crear tabla comparativa mejorada
    comparison_data = []
    
    # Agregar original
    row = {'Modelo': '🎯 Red Original', 'Tipo': 'Real'}
    for metric in metrics_compared:
        if metric in original and isinstance(original[metric], (int, float)):
            row[metric] = original[metric]
    comparison_data.append(row)
    
    # Agregar modelos aleatorios con estadísticas
    for model_name, model_results in models.items():
        row = {'Modelo': f'🎲 {model_name}', 'Tipo': 'Aleatorio'}
        
        for metric in metrics_compared:
            if metric in original and isinstance(original[metric], (int, float)):
                values = [r.get(metric, 0) for r in model_results 
                         if metric in r and isinstance(r[metric], (int, float))]
                if values:
                    row[metric] = np.mean(values)
                    row[f'{metric}_std'] = np.std(values)
                    row[f'{metric}_min'] = np.min(values)
                    row[f'{metric}_max'] = np.max(values)
        
        comparison_data.append(row)
    
    # Mostrar tabla principal
    df = pd.DataFrame(comparison_data)
    
    # Formatear números en columnas principales
    display_cols = ['Modelo', 'Tipo'] + [col for col in metrics_compared if col in df.columns]
    df_display = df[display_cols].copy()
    
    for col in metrics_compared:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(
                lambda x: f"{x:.4f}" if isinstance(x, (int, float)) else x
            )
    
    st.dataframe(df_display, use_container_width=True)
    
    

def plot_metric_distributions(original, models, metric, show_violin=False):
    """Crea gráficos de distribución para una métrica específica"""
    
    # Recopilar datos
    plot_data = []
    
    # Agregar valor original
    original_value = original.get(metric, 0)
    
    for model_name, model_results in models.items():
        values = [r.get(metric, 0) for r in model_results 
                 if metric in r and isinstance(r[metric], (int, float))]
        
        for value in values:
            plot_data.append({
                'Modelo': model_name,
                'Valor': value,
                'Tipo': 'Aleatorio'
            })
    
    if not plot_data:
        st.warning(f"No hay datos suficientes para {metric}")
        return
    
    df_plot = pd.DataFrame(plot_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if show_violin:
            # Gráfico de violín
            fig_violin = px.violin(
                df_plot, y='Valor', x='Modelo', 
                title=f"Distribución de {metric.replace('_', ' ').title()}",
                color='Modelo',
                points="all"
            )
            
            # Agregar línea para valor original
            fig_violin.add_hline(
                y=original_value, 
                line_dash="dash", 
                line_color="red",
                annotation_text=f"Original: {original_value:.4f}"
            )
            
            st.plotly_chart(fig_violin, use_container_width=True)
        else:
            # Histogramas por modelo
            fig_hist = make_subplots(
                rows=len(models), cols=1,
                subplot_titles=[f"{model}" for model in models.keys()],
                vertical_spacing=0.1
            )
            
            colors = ['#667eea', '#f093fb', '#4facfe', '#fa709a', '#a8edea']
            
            for i, (model_name, model_results) in enumerate(models.items()):
                values = [r.get(metric, 0) for r in model_results 
                         if metric in r and isinstance(r[metric], (int, float))]
                
                fig_hist.add_trace(
                    go.Histogram(
                        x=values, 
                        name=model_name,
                        marker_color=colors[i % len(colors)],
                        showlegend=False
                    ),
                    row=i+1, col=1
                )
                
                # Línea del valor original
                fig_hist.add_vline(
                    x=original_value,
                    line_dash="dash",
                    line_color="red",
                    row=i+1, col=1
                )
            
            fig_hist.update_layout(
                height=200 * len(models),
                title_text=f"Distribuciones de {metric.replace('_', ' ').title()}"
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # Estadísticas detalladas
        st.markdown(f"**📊 Estadísticas para {metric.replace('_', ' ').title()}:**")
        
        stats_data = []
        stats_data.append({
            'Modelo': 'Original',
            'Valor': f"{original_value:.4f}",
            'Tipo': 'Real'
        })
        
        for model_name, model_results in models.items():
            values = [r.get(metric, 0) for r in model_results 
                     if metric in r and isinstance(r[metric], (int, float))]
            
            if values:
                stats_data.append({
                    'Modelo': model_name,
                    'Media': f"{np.mean(values):.4f}",
                    'Mediana': f"{np.median(values):.4f}",
                    'Desv.Est': f"{np.std(values):.4f}",
                    'Min': f"{np.min(values):.4f}",
                    'Max': f"{np.max(values):.4f}"
                })
        
        st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

def show_anomaly_analysis_expanded(original, models, metrics_compared):
    """Análisis de anomalías expandido"""
    st.markdown("#### 🔍 Análisis de Anomalías Avanzado")
    
    anomalies = []
    
    for metric in metrics_compared:
        if metric in original and isinstance(original[metric], (int, float)):
            original_value = original[metric]
            
            # Recopilar valores aleatorios
            all_random_values = []
            model_stats = {}
            
            for model_name, model_results in models.items():
                values = [r.get(metric, 0) for r in model_results 
                         if metric in r and isinstance(r[metric], (int, float))]
                all_random_values.extend(values)
                
                if values:
                    model_stats[model_name] = {
                        'mean': np.mean(values),
                        'std': np.std(values),
                        'count': len(values)
                    }
            
            if len(all_random_values) > 2:
                mean_random = np.mean(all_random_values)
                std_random = np.std(all_random_values)
                
                if std_random > 0:
                    z_score = (original_value - mean_random) / std_random
                    
                    if abs(z_score) > 1.5:  # Umbral para anomalía
                        if abs(z_score) > 3:
                            anomaly_type = "🔴 Muy Anómalo"
                        elif abs(z_score) > 2:
                            anomaly_type = "🟡 Anómalo"
                        else:
                            anomaly_type = "🟠 Moderadamente Anómalo"
                        
                        direction = "⬆️ Superior" if z_score > 0 else "⬇️ Inferior"
                        
                        # Calcular percentil
                        percentile = (sum(1 for v in all_random_values if v < original_value) / 
                                    len(all_random_values)) * 100
                        
                        anomalies.append({
                            'Métrica': metric.replace('_', ' ').title(),
                            'Valor Real': f"{original_value:.4f}",
                            'Media Aleatoria': f"{mean_random:.4f}",
                            'Z-Score': f"{z_score:.2f}",
                            'Percentil': f"{percentile:.1f}%",
                            'Nivel': anomaly_type,
                            'Dirección': direction
                        })
    
    if anomalies:
        st.markdown("**🚨 Anomalías Detectadas:**")
        anomaly_df = pd.DataFrame(anomalies)
        st.dataframe(anomaly_df, use_container_width=True)
        
        # Interpretación inteligente expandida
        high_anomalies = [a for a in anomalies if "Muy Anómalo" in a['Nivel']]
        moderate_anomalies = [a for a in anomalies if "Moderadamente Anómalo" in a['Nivel']]
        
        if high_anomalies:
            st.error(f"⚠️ Se detectaron {len(high_anomalies)} anomalías críticas que indican estructura muy especial")
            st.markdown("**Posibles interpretaciones:**")
            st.markdown("- La red tiene propiedades estructurales únicas")
            st.markdown("- Existe organización no aleatoria significativa")
            st.markdown("- Los procesos generativos son muy diferentes a los modelos probados")
        elif moderate_anomalies:
            st.warning(f"ℹ️ Se detectaron {len(moderate_anomalies)} anomalías moderadas")
            st.markdown("**Interpretación:** Patrones parcialmente no aleatorios en la red")
        else:
            st.info("ℹ️ Anomalías leves detectadas - algunos patrones no aleatorios presentes")
    else:
        st.success("✅ No se detectaron anomalías significativas - comportamiento similar a modelos aleatorios")

def show_model_similarity_ranking(original, models, metrics_compared):
    """Muestra ranking de similitud entre modelos y el grafo original"""
    st.markdown("#### 🏆 Ranking de Similitud de Modelos")
    
    model_scores = []
    
    for model_name, model_results in models.items():
        total_score = 0
        metric_count = 0
        
        for metric in metrics_compared:
            if metric in original and isinstance(original[metric], (int, float)):
                original_value = original[metric]
                
                values = [r.get(metric, 0) for r in model_results 
                         if metric in r and isinstance(r[metric], (int, float))]
                
                if values:
                    mean_model = np.mean(values)
                    std_model = np.std(values)
                    
                    # Calcular score de similitud (inverso de la distancia normalizada)
                    if std_model > 0:
                        z_score = abs(original_value - mean_model) / std_model
                        score = max(0, 1 - z_score / 3)  # Normalizar para que 3 desvest = score 0
                    else:
                        score = 1 if original_value == mean_model else 0
                    
                    total_score += score
                    metric_count += 1
        
        if metric_count > 0:
            avg_score = total_score / metric_count
            model_scores.append({
                'Modelo': model_name,
                'Score de Similitud': f"{avg_score:.3f}",
                'Similitud %': f"{avg_score * 100:.1f}%",
                'Ranking': 0  # Se asignará después
            })
    
    # Ordenar por score
    model_scores.sort(key=lambda x: float(x['Score de Similitud']), reverse=True)
    
    # Asignar rankings
    for i, model in enumerate(model_scores):
        model['Ranking'] = i + 1
        
        # Añadir emojis de ranking
        if i == 0:
            model['Modelo'] = f"🥇 {model['Modelo']}"
        elif i == 1:
            model['Modelo'] = f"🥈 {model['Modelo']}"
        elif i == 2:
            model['Modelo'] = f"🥉 {model['Modelo']}"
        else:
            model['Modelo'] = f"#{i+1} {model['Modelo']}"
    
    # Mostrar tabla de ranking
    ranking_df = pd.DataFrame(model_scores)
    st.dataframe(ranking_df, use_container_width=True, hide_index=True)
    
    # Interpretación del mejor modelo
    if model_scores:
        best_model = model_scores[0]
        best_score = float(best_model['Score de Similitud'])
        
        if best_score > 0.8:
            st.success(f"🎯 **Mejor coincidencia:** {best_model['Modelo']} con {best_score:.1%} de similitud")
            st.markdown("**Interpretación:** Este modelo captura muy bien las propiedades de la red original")
        elif best_score > 0.6:
            st.info(f"📊 **Mejor coincidencia:** {best_model['Modelo']} con {best_score:.1%} de similitud")
            st.markdown("**Interpretación:** Este modelo tiene similitudes moderadas con la red original")
        else:
            st.warning(f"⚠️ **Mejor coincidencia:** {best_model['Modelo']} con solo {best_score:.1%} de similitud")
            st.markdown("**Interpretación:** Ningún modelo captura bien las propiedades de la red - estructura muy particular")

def show_anomaly_analysis(original, models):
    """Análisis de anomalías mejorado"""
    st.markdown("#### 🔍 Detección de Anomalías Estructurales")
    
    anomalies = []
    
    key_metrics = ['density', 'avg_degree', 'transitivity', 'degree_std']
    
    for metric in key_metrics:
        if metric in original and isinstance(original[metric], (int, float)):
            original_value = original[metric]
            
            # Recopilar valores aleatorios
            all_random_values = []
            for model_results in models.values():
                values = [r.get(metric, 0) for r in model_results 
                         if metric in r and isinstance(r[metric], (int, float))]
                all_random_values.extend(values)
            
            if len(all_random_values) > 2:
                mean_random = np.mean(all_random_values)
                std_random = np.std(all_random_values)
                
                if std_random > 0:
                    z_score = abs(original_value - mean_random) / std_random
                    
                    if z_score > 1.5:  # Umbral más sensible
                        if z_score > 3:
                            anomaly_type = "🔴 Muy Anómalo"
                        elif z_score > 2:
                            anomaly_type = "🟡 Anómalo"
                        else:
                            anomaly_type = "🟠 Moderadamente Anómalo"
                        
                        direction = "⬆️ Superior" if original_value > mean_random else "⬇️ Inferior"
                        
                        anomalies.append({
                            'Métrica': metric.replace('_', ' ').title(),
                            'Valor Real': f"{original_value:.4f}",
                            'Media Aleatoria': f"{mean_random:.4f}",
                            'Z-Score': f"{z_score:.2f}",
                            'Nivel': anomaly_type,
                            'Dirección': direction
                        })
    
    if anomalies:
        st.markdown("**🚨 Anomalías Detectadas:**")
        anomaly_df = pd.DataFrame(anomalies)
        st.dataframe(anomaly_df, use_container_width=True)
        
        # Interpretación inteligente
        high_anomalies = [a for a in anomalies if "Muy Anómalo" in a['Nivel']]
        if high_anomalies:
            st.error(f"⚠️ Se detectaron {len(high_anomalies)} anomalías críticas que sugieren estructura muy especial")
        else:
            st.info("ℹ️ Anomalías detectadas indican patrones no aleatorios en la red")
        
    else:
        st.success("✅ No se detectaron anomalías significativas - comportamiento similar a modelos aleatorios")

# Funciones stub para las otras pestañas (implementar según necesidad)
def show_resilience_analysis_cached(graph, graph_type):
    """Análisis de resiliencia con caché"""
    st.markdown("### 🛡️ Análisis de Resiliencia y Robustez")
    
    cached = get_cached_metrics(graph, graph_type, "resilience")
    if cached:
        st.info("✅ Usando análisis de resiliencia en caché")
        display_resilience_results_cached(cached)
        return
    
    n_nodes = len(graph.nodes())
    
    if n_nodes < 10:
        st.warning("⚠️ Grafo muy pequeño para análisis de resiliencia")
        return
    
    # Configuración
    col1, col2 = st.columns([3, 1])
    
    with col1:
        strategies = st.multiselect(
            "Estrategias de ataque:",
            ["Aleatorio", "Alto Grado", "Alta Intermediación"],
            default=["Aleatorio", "Alto Grado"],
            help="Estrategias de remoción de nodos"
        )
    
    with col2:
        max_removal = st.slider("% máximo remoción", 10, 50, 25, 5)
        
    if st.button("🎯 Análisis de Resiliencia", type="primary"):
        with st.spinner("🛡️ Simulando ataques..."):
            results = perform_resilience_analysis_fast(graph, strategies, max_removal)
            cache_metrics(graph, graph_type, "resilience", results)
            display_resilience_results_cached(results)

def perform_resilience_analysis_fast(graph, strategies, max_removal_pct):
    """Análisis de resiliencia para grafos"""
    n_nodes = len(graph.nodes())
    max_removals = min(int(n_nodes * max_removal_pct / 100), n_nodes // 2)
    
    degrees = dict(graph.degree())
    
    betweenness = {}
    if "Alta Intermediación" in strategies:
        betweenness = nx.betweenness_centrality(graph)
    
    results = {}
    
    for strategy in strategies:
        # Determinar secuencia de remoción
        if strategy == "Aleatorio":
            removal_sequence = np.random.permutation(list(graph.nodes()))
        elif strategy == "Alto Grado":
            removal_sequence = sorted(graph.nodes(), key=lambda x: degrees[x], reverse=True)
        elif strategy == "Alta Intermediación":
            removal_sequence = sorted(graph.nodes(), 
                                    key=lambda x: betweenness.get(x, 0), reverse=True)
        
        # Simulación 
        connectivity_history = []
        temp_graph = graph.copy()
        
        step_size = max(1, max_removals // 20)  
        
        for i in range(0, max_removals, step_size):
            end_idx = min(i + step_size, len(removal_sequence))
            nodes_to_remove = removal_sequence[i:end_idx]
            temp_graph.remove_nodes_from(nodes_to_remove)
            
            if len(temp_graph.nodes()) > 0:
                largest_cc = max(nx.connected_components(temp_graph), key=len, default=set())
                connectivity = len(largest_cc) / n_nodes
            else:
                connectivity = 0
            
            connectivity_history.append(connectivity)
        
        results[strategy] = {
            'connectivity': connectivity_history,
            'steps': list(range(0, max_removals, step_size))
        }
    
    return results

def display_resilience_results_cached(results):
    """Muestra resultados de resiliencia con visualización moderna"""
    st.markdown("#### 📈 Curvas de Resiliencia")

    fig = go.Figure()
    
    colors = ['#667eea', '#f093fb', '#4facfe', '#fa709a', '#a8edea']
    
    for i, (strategy, data) in enumerate(results.items()):
        fig.add_trace(go.Scatter(
            x=data['steps'],
            y=data['connectivity'],
            mode='lines+markers',
            name=strategy,
            line=dict(color=colors[i % len(colors)], width=4),
            marker=dict(size=8, symbol='circle'),
            hovertemplate=f"<b>{strategy}</b><br>" +
                         "Nodos removidos: %{x}<br>" +
                         "Conectividad: %{y:.2%}<extra></extra>"
        ))
    
    fig.update_layout(
        title={
            'text': "Resiliencia de la Red por Estrategia de Ataque",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#2c3e50'}
        },
        xaxis_title="Nodos Removidos",
        yaxis_title="Fracción del Componente Gigante",
        height=500,
        template="plotly_white",
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    resilience_summary = []
    for strategy, data in results.items():
        connectivity = np.array(data['connectivity'])
        auc = np.trapz(connectivity) / len(connectivity) if len(connectivity) > 0 else 0
        
        collapse_point = len(connectivity)
        for i, c in enumerate(connectivity):
            if c < 0.5:
                collapse_point = data['steps'][i] if i < len(data['steps']) else i
                break
        
        resilience_summary.append({
            'Estrategia': strategy,
            'Resiliencia (AUC)': f"{auc:.3f}",
            'Punto Colapso': collapse_point,
            'Vulnerabilidad': "Alta" if auc < 0.3 else "Media" if auc < 0.6 else "Baja"
        })
    
    st.dataframe(pd.DataFrame(resilience_summary), use_container_width=True)

def show_community_diffusion_analysis_cached(graph, graph_type):
    """Análisis de comunidades y difusión"""
    st.markdown("### 🌐 Análisis de Comunidades y Difusión")
    
    cached = get_cached_metrics(graph, graph_type, "communities")
    if cached:
        st.info("✅ Usando análisis de comunidades en caché")
        display_community_results_cached(cached)
        return
    
    if len(graph.nodes()) < 5:
        st.warning("⚠️ Grafo muy pequeño para análisis de comunidades")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        algorithm = st.selectbox(
            "Algoritmo de detección:",
            ["Greedy Modularity", "Label Propagation"],
            help="Algoritmos de detección de comunidades"
        )
    
    with col2:
        min_community_size = st.number_input(
            "Tamaño mínimo comunidad:",
            min_value=2,
            max_value=50,
            value=5,
            help="Filtrar comunidades muy pequeñas"
        )
    
    if st.button("🔍 Detectar Comunidades", type="primary"):
        with st.spinner("🌐 Detectando comunidades..."):
            results = perform_community_analysis_fast(graph, algorithm, min_community_size)
            cache_metrics(graph, graph_type, "communities", results)
            display_community_results_cached(results)

def perform_community_analysis_fast(graph, algorithm, min_size):
    """Detección de comunidades"""
    try:
        # Detectar comunidades
        if algorithm == "Greedy Modularity":
            communities = list(nx.community.greedy_modularity_communities(graph))
        else:  # Label Propagation
            communities = list(nx.community.label_propagation_communities(graph))
        
        # Filtrar por tamaño mínimo
        large_communities = [comm for comm in communities if len(comm) >= min_size]
        
        if large_communities:
            modularity = nx.community.modularity(graph, large_communities)
            sizes = [len(comm) for comm in large_communities]
            
            return {
                'communities': large_communities,
                'modularity': modularity,
                'sizes': sizes,
                'n_communities': len(large_communities),
                'coverage': sum(sizes) / len(graph.nodes()) if len(graph.nodes()) > 0 else 0
            }
        else:
            return {'error': 'No se encontraron comunidades del tamaño mínimo especificado'}
            
    except Exception as e:
        return {'error': f'Error en detección de comunidades: {str(e)}'}

def display_community_results_cached(results):
    """Muestra resultados de análisis de comunidades"""
    if 'error' in results:
        st.error(results['error'])
        return
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🎯 Comunidades", results['n_communities'])
    with col2:
        st.metric("📊 Modularidad", f"{results['modularity']:.3f}")
    with col3:
        st.metric("🏗️ Mayor Comunidad", max(results['sizes']) if results['sizes'] else 0)
    with col4:
        st.metric("📈 Cobertura", f"{results['coverage']:.1%}")
    
    # Distribución de tamaños
    if len(results['sizes']) > 1:
        fig_communities = px.histogram(
            x=results['sizes'],
            nbins=min(15, len(results['sizes'])),
            title="Distribución de Tamaños de Comunidades",
            labels={'x': 'Tamaño de Comunidad', 'y': 'Frecuencia'},
            color_discrete_sequence=['#667eea']
        )
        fig_communities.update_layout(height=350, template="plotly_white")
        st.plotly_chart(fig_communities, use_container_width=True)
    
    # Simulación de difusión básica
    st.markdown("#### 🔄 Simulación de Difusión Entre Comunidades")
    
    if st.button("🚀 Simular Difusión Rápida"):
        diffusion_results = simulate_diffusion_fast(results)
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("🎯 Comunidades Semilla", diffusion_results['seed_communities'])
        with col_b:
            st.metric("📈 Cobertura Estimada", f"{diffusion_results['estimated_coverage']:.1%}")
        with col_c:
            st.metric("⚡ Velocidad Difusión", diffusion_results['diffusion_speed'])

def simulate_diffusion_fast(community_results):
    """Simulación rápida de difusión entre comunidades"""
    n_communities = community_results['n_communities']
    sizes = community_results['sizes']
    
    # Usar una comunidad por cada 3 como semilla
    seed_communities = max(1, n_communities // 3)
    
    # Estimación simple de cobertura basada en tamaños
    if sizes:
        seed_coverage = sum(sorted(sizes, reverse=True)[:seed_communities]) / sum(sizes)
        # Asumir difusión del 60-80% adicional
        estimated_coverage = min(1.0, seed_coverage + 0.7 * (1 - seed_coverage))
    else:
        estimated_coverage = 0
    
    # Velocidad basada en modularidad (menor modularidad = mayor difusión)
    modularity = community_results['modularity']
    if modularity < 0.3:
        speed = "Rápida"
    elif modularity < 0.6:
        speed = "Media"
    else:
        speed = "Lenta"
    
    return {
        'seed_communities': seed_communities,
        'estimated_coverage': estimated_coverage,
        'diffusion_speed': speed
    }

def show_advanced_metrics_cached(graph, graph_type):
    """Métricas avanzadas con caché"""
    st.markdown("### ⚡ Métricas Avanzadas")
    
    # Verificar caché
    cached = get_cached_metrics(graph, graph_type, "advanced_metrics")
    if cached:
        st.info("✅ Usando métricas avanzadas en caché")
        display_advanced_metrics_results(cached)
        return
    
    n_nodes = len(graph.nodes())
    
    # Selección de métricas
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Métricas Disponibles:**")
        centrality_metrics = st.multiselect(
            "Centralidades:",
            ["PageRank", "Harmonic", "Katz", "Betweenness", "Closeness"],
            default=["PageRank", "Betweenness"],
            help="Selecciona centralidades a calcular"
        )
    
    with col2:
        st.markdown("**⚙️ Análisis:**")
        st.info(f"Se analizará el grafo completo ({n_nodes:,} nodos)")
    
    if st.button("⚡ Calcular Métricas Avanzadas", type="primary"):
        with st.spinner("🧮 Calculando métricas especializadas..."):
            results = calculate_advanced_metrics_optimized(
                graph, graph_type, centrality_metrics
            )
            cache_metrics(graph, graph_type, "advanced_metrics", results)
            display_advanced_metrics_results(results)

def calculate_advanced_metrics_optimized(graph, graph_type, centralities):
    """Calcula métricas avanzadas para el grafo completo"""
    n_nodes = len(graph.nodes())
    results = {'sample_size': n_nodes}
    
    # Usar siempre el grafo completo
    analysis_graph = graph
    results['used_sampling'] = False
    
    # Calcular centralidades seleccionadas
    results['centralities'] = {}
    
    try:
        for centrality in centralities:
            if centrality == "PageRank":
                results['centralities']['pagerank'] = nx.pagerank(analysis_graph)
            elif centrality == "Harmonic":
                results['centralities']['harmonic'] = nx.harmonic_centrality(analysis_graph)
            elif centrality == "Katz":
                results['centralities']['katz'] = nx.katz_centrality(analysis_graph, max_iter=1000)
            elif centrality == "Betweenness":
                results['centralities']['betweenness'] = nx.betweenness_centrality(analysis_graph)
            elif centrality == "Closeness":
                results['centralities']['closeness'] = nx.closeness_centrality(analysis_graph)
    except Exception as e:
        results['centrality_error'] = str(e)
    
    # Métricas estructurales adicionales
    try:
        if nx.is_connected(analysis_graph):
            results['diameter'] = nx.diameter(analysis_graph)
            results['radius'] = nx.radius(analysis_graph)
            results['center_size'] = len(nx.center(analysis_graph))
            results['wiener_index'] = nx.wiener_index(analysis_graph)
            
    except Exception as e:
        results['structural_error'] = str(e)
    
    # Métricas específicas por tipo de grafo
    if graph_type == "author":
        # Para redes de colaboración
        try:
            results['avg_clustering'] = nx.average_clustering(analysis_graph)
            results['transitivity'] = nx.transitivity(analysis_graph)
            results['triangles'] = sum(nx.triangles(analysis_graph).values()) // 3
                
        except Exception as e:
            results['collaboration_error'] = str(e)
    
    return results

def display_advanced_metrics_results(results):
    """Muestra resultados de métricas avanzadas"""
    st.markdown("#### 📊 Resultados de Métricas Avanzadas")
    
    # Información del análisis
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if results.get('used_sampling'):
            st.info(f"**Muestra:** {results['sample_size']:,} nodos")
        else:
            st.info("**Análisis:** Completo")
    with col2:
        if 'centralities' in results:
            st.info(f"**Centralidades:** {len(results['centralities'])}")
    with col3:
        st.info("**Estado:** Calculado")
    
    # Mostrar centralidades
    if 'centralities' in results and results['centralities']:
        st.markdown("#### 🎯 Ranking de Centralidades")
        
        # Crear tabla comparativa de top nodos
        centrality_data = []
        
        # Obtener top 5 para cada centralidad
        for cent_name, cent_values in results['centralities'].items():
            top_nodes = sorted(cent_values.items(), key=lambda x: x[1], reverse=True)[:5]
            
            for rank, (node, value) in enumerate(top_nodes, 1):
                centrality_data.append({
                    'Centralidad': cent_name.title(),
                    'Ranking': rank,
                    'Nodo': str(node)[:20],  # Truncar nombres largos
                    'Valor': f"{value:.4f}"
                })
        
        if centrality_data:
            df_centralities = pd.DataFrame(centrality_data)
            
            # Mostrar por centralidad
            for cent_name in results['centralities'].keys():
                cent_data = df_centralities[df_centralities['Centralidad'] == cent_name.title()]
                if not cent_data.empty:
                    st.markdown(f"**{cent_name.title()} - Top 5:**")
                    st.dataframe(
                        cent_data[['Ranking', 'Nodo', 'Valor']].reset_index(drop=True),
                        use_container_width=True,
                        hide_index=True
                    )
    
    # Mostrar métricas estructurales
    structural_metrics = ['diameter', 'radius', 'center_size', 'wiener_index', 
                         'avg_clustering', 'transitivity', 'triangles']
    
    available_structural = {k: v for k, v in results.items() if k in structural_metrics}
    
    if available_structural:
        st.markdown("#### 🏗️ Métricas Estructurales")
        
        # Organizar en columns
        cols = st.columns(min(3, len(available_structural)))
        
        for i, (metric, value) in enumerate(available_structural.items()):
            with cols[i % len(cols)]:
                metric_name = metric.replace('_', ' ').title()
                if isinstance(value, float):
                    st.metric(metric_name, f"{value:.4f}")
                else:
                    st.metric(metric_name, f"{value:,}")
    
    # Mostrar errores si los hay
    error_keys = [k for k in results.keys() if k.endswith('_error')]
    if error_keys:
        with st.expander("⚠️ Errores en Cálculos", expanded=False):
            for error_key in error_keys:
                st.error(f"{error_key}: {results[error_key]}")

# ========================================
# FUNCIONES DE UTILIDAD ADICIONALES
# ========================================

def get_cache_statistics():
    """Obtiene estadísticas del caché"""
    cache = st.session_state.metrics_cache
    
    stats = {
        'total_entries': len(cache),
        'memory_usage_mb': len(str(cache)) / 1024 / 1024,
        'oldest_entry': None,
        'newest_entry': None,
        'metric_types': {}
    }
    
    if cache:
        timestamps = [data['timestamp'] for data in cache.values()]
        stats['oldest_entry'] = time.strftime('%H:%M:%S', time.localtime(min(timestamps)))
        stats['newest_entry'] = time.strftime('%H:%M:%S', time.localtime(max(timestamps)))
        
        # Contar tipos de métricas
        for key in cache.keys():
            parts = key.split('_')
            if len(parts) >= 2:
                metric_type = parts[1]
                stats['metric_types'][metric_type] = stats['metric_types'].get(metric_type, 0) + 1
    
    return stats

def export_cache_summary():
    """Exporta resumen del caché para debugging"""
    stats = get_cache_statistics()
    
    summary = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'cache_statistics': stats,
        'cache_keys': list(st.session_state.metrics_cache.keys())
    }
    
    return summary


def show_network_analysis():
    show_network_analysis_optimized()
