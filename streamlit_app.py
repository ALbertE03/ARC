import streamlit as st
import plotly.express as px
import pandas as pd
from src.graph_utils import GraphAnalyzer, create_advanced_graph_visualization, create_performance_dashboard, create_community_comparison_visualization, create_community_graph_visualization
from src.utils import *

st.set_page_config(
    page_title="Visualizador de Grafo de Colaboración de Autores",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

st.title("📊 Visualizador de Grafo de Colaboración de Autores")
st.markdown("Sistema de resolución y consolidación de autores (ARC)")


def main():
    """Función principal de la aplicación"""
    
    st.sidebar.title("📋 Navegación")
    page = st.sidebar.selectbox(
        "Selecciona una página:",
        ["Visualización del Grafo", "Análisis Avanzado", "Rendimiento del Modelo", "Buscar Autores"]
    )
    
    graph = load_graph_data()
    
    if page == "Visualización del Grafo":
        st.header("Visualización del Grafo de Colaboración")
        
        if graph:
            st.sidebar.subheader("Configuración")
            layout_type = st.sidebar.selectbox(
                "Tipo de layout:",
                ["spring", "circular", "kamada_kawai"]
            )
            
            max_nodes = st.sidebar.slider(
                "Máximo número de nodos:",
                min_value=50,
                max_value=500,
                value=100,
                step=50
            )
            
            with st.spinner("Creando visualización..."):
                fig = create_graph_visualization(graph, layout_type, max_nodes)
                st.plotly_chart(fig, use_container_width=True)
            
            show_graph_statistics(graph)
        else:
            st.error("No se pudo cargar el grafo. Asegúrate de que el archivo 'author_collaboration_graph.graphml' existe.")
    
    elif page == "Análisis Avanzado":
        st.header("Análisis Avanzado del Grafo")
        
        if graph:
            analyzer = GraphAnalyzer(graph)
            
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["Comunidades", "Centralidad", "Patrones de Colaboración", "Análisis de Pesos", "Análisis de Investigación"])
            
            with tab1:
                st.markdown("### Detección de Comunidades de Investigación")
                st.markdown("---")

                with st.container():
                    st.markdown("#### ⚙️ Configuración del Análisis")
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        method = st.selectbox(
                            "🔍 Método de detección:",
                            ["louvain", "weighted_louvain", "leiden", "edge_betweenness", 
                             "girvan_newman", "strong_ties", "weak_ties"],
                            help="Diferentes algoritmos para detectar comunidades de investigación",
                            format_func=lambda x: {
                                "louvain": "Comunidades Generales (Rápido)",
                                "weighted_louvain": "Por Intensidad de Colaboración",
                                "leiden": "Detección de Alta Precisión",
                                "edge_betweenness": "Por Puentes de Conexión",
                                "girvan_newman": "División Jerárquica",
                                "strong_ties": "Solo Colaboraciones Intensas",
                                "weak_ties": "Solo Colaboraciones Ocasionales"
                            }[x]
                        )
                    
                    with col2:
                        weight_threshold = st.slider(
                            "🔗 Umbral de colaboración:",
                            min_value=1,
                            max_value=10,
                            value=1,
                            help="Considerar solo colaboraciones con peso >= umbral"
                        )
                    
                    with col3:
                        if method in ["louvain", "weighted_louvain", "leiden"]:
                            resolution = st.slider(
                                "🎚️ Resolución:",
                                min_value=0.1,
                                max_value=3.0,
                                value=1.0,
                                step=0.1,
                                help="Controla el tamaño de las comunidades"
                            )
                        else:
                            resolution = 1.0
                
                with st.spinner("🔍 Detectando comunidades de investigación..."):
                    threshold = None if method in ["strong_ties", "weak_ties"] else weight_threshold
                    communities = analyzer.detect_communities(
                        method=method, 
                        weight_threshold=threshold,
                        resolution=resolution
                    )
                    
                if communities:
                    community_analysis = analyzer.get_community_analysis(communities)
                    
                    st.markdown("---")
                    st.markdown("### Resultados del Análisis")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Comunidades",
                            community_analysis['num_communities'],
                            help="Número total de comunidades detectadas"
                        )
                    
                    with col2:
                        modularity = community_analysis['modularity']
                        modularity_color = "🟢" if modularity > 0.3 else "🟡" if modularity > 0.1 else "🔴"
                        st.metric(
                            f"{modularity_color} Modularidad",
                            f"{modularity:.3f}",
                            help="Calidad de la división en comunidades (0-1, mejor > 0.3)"
                        )
                    
                    with col3:
                        largest_community_size = max(stats['size'] for stats in community_analysis['communities'].values())
                        st.metric(
                            "👥 Mayor Comunidad",
                            f"{largest_community_size} miembros",
                            help="Tamaño de la comunidad más grande"
                        )
                    
                    with col4:
                        avg_community_size = sum(stats['size'] for stats in community_analysis['communities'].values()) / len(community_analysis['communities'])
                        st.metric(
                            "📊 Tamaño Promedio",
                            f"{avg_community_size:.1f} miembros",
                            help="Tamaño promedio de las comunidades"
                        )
 
                    
                    st.markdown("---")
                    
                    with st.expander("#### Detalles de las Comunidades"):
                        sorted_communities = sorted(
                            community_analysis['communities'].items(),
                            key=lambda x: x[1]['size'],
                            reverse=True
                        )
                        
                        comm_data = []
                        for comm_id, stats in sorted_communities:
                            density = stats['internal_edges'] / (stats['size'] * (stats['size'] - 1) / 2) if stats['size'] > 1 else 0
                            comm_data.append({
                                '🏷️ Comunidad': f"Grupo {comm_id}",
                                '👥 Miembros': stats['size'],
                                '🔗 Conexiones Internas': stats['internal_edges'],
                                '🌐 Conexiones Externas': stats['external_edges'],
                                '⚖️ Peso Promedio': f"{stats['avg_weight']:.2f}",
                                '🎯 Densidad': f"{density:.3f}"
                            })
                        
                        df_communities = pd.DataFrame(comm_data)
                        st.dataframe(df_communities, use_container_width=True)

                    st.markdown("---")
                    st.markdown("### 🔍 Explorar Comunidades")
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        sorted_community_options = sorted(
                            community_analysis['communities'].keys(),
                            key=lambda x: community_analysis['communities'][x]['size'],
                            reverse=True
                        )
                        
                        selected_community = st.selectbox(
                            "Seleccionar comunidad (ordenadas por tamaño):",
                            options=sorted_community_options,
                            format_func=lambda x: f"Grupo {x} ({community_analysis['communities'][x]['size']} miembros) - Rank #{sorted_community_options.index(x) + 1}"
                        )
                    
                    if selected_community is not None:
                        comm_stats = community_analysis['communities'][selected_community]
                        
                        with col2:
                            col_a, col_b, col_c = st.columns(3)
                            
                            with col_a:
                                st.metric("👥 Miembros", comm_stats['size'])
                            
                            with col_b:
                                st.metric("🔗 Conexiones", comm_stats['internal_edges'])
                            
                            with col_c:
                                st.metric("⚖️ Peso Prom.", f"{comm_stats['avg_weight']:.2f}")

                        with st.container():
                            st.markdown(f"#### 🏷️ Detalles del Grupo {selected_community}")
    
                            density = comm_stats['internal_edges'] / (comm_stats['size'] * (comm_stats['size'] - 1) / 2) if comm_stats['size'] > 1 else 0
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.info(f"""
                                **📊 Estadísticas Estructurales**
                                - 🔗 Conexiones internas: {comm_stats['internal_edges']}
                                - 🌐 Conexiones externas: {comm_stats['external_edges']}
                                - 🎯 Densidad interna: {density:.3f}
                                """)
                            
                            with col2:
                                cohesion_level = "🟢 Alta" if density > 0.5 else "🟡 Media" if density > 0.2 else "🔴 Baja"
                                connectivity = "🟢 Bien conectado" if comm_stats['avg_weight'] > 2 else "🟡 Moderado" if comm_stats['avg_weight'] > 1 else "🔴 Poco conectado"
                                
                                st.success(f"""
                                **🎯 Análisis de Calidad**
                                - Cohesión: {cohesion_level}
                                - Conectividad: {connectivity}
                                - Tamaño: {'🟢 Óptimo' if 5 <= comm_stats['size'] <= 15 else '🟡 Grande' if comm_stats['size'] > 15 else '🔴 Pequeño'}
                                """)

                        st.markdown("#### 👥 Miembros de la Comunidad")
                        
                        members_info = []
                        for node in comm_stats['nodes']: 
                            node_data = graph.graph.nodes[node]
                            members_info.append({
                                '👤 Investigador': node_data.get('name', 'Desconocido'),
                                '📄 Papers': node_data.get('paper_count', 0),
                                '🤝 Colaboradores': graph.graph.degree(node),
                            })
                        
                        df_members = pd.DataFrame(members_info)
                        st.dataframe(df_members, use_container_width=True)
                        
                else:
                    st.error("❌ No se pudieron detectar comunidades con los parámetros seleccionados. Intenta ajustar los parámetros.")
            
            with tab2:
                st.markdown("### 🎯 Análisis de Centralidades en la Red de Investigación")
                st.markdown("---")
                
                with st.container():
                    st.markdown("#### ⚙️ Configuración del Análisis")
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        centrality_type = st.selectbox(
                            "🔍 Selecciona el tipo de análisis:",
                            ["degree", "betweenness", "closeness", "eigenvector"],
                            help="Diferentes métricas para identificar investigadores influyentes",
                            format_func=lambda x: {
                                "degree": "🔗 Conectividad Social - Investigadores con más colaboradores directos",
                                "betweenness": "🌉 Puentes de Conocimiento - Intermediarios que conectan diferentes grupos",
                                "closeness": "⚡ Acceso a Información - Cercanía promedio a todos los investigadores",
                                "eigenvector": "👑 Influencia por Prestigio - Conectados con otros investigadores importantes"
                            }[x]
                        )
                    
                    with col2:
                        show_stats = st.checkbox("📊 Mostrar estadísticas", value=True)
                
                with st.spinner("🔍 Analizando posiciones en la red..."):
                    centralities = analyzer.get_centrality_measures()
                
                if centralities:
                    centrality_key = f"{centrality_type}_centrality"
                    
                    if centrality_key in centralities:
                        centrality_data = centralities[centrality_key]
                      
                        centrality_values = list(centrality_data.values())
                        avg_centrality = sum(centrality_values) / len(centrality_values)
                        max_centrality = max(centrality_values)
                        min_centrality = min(centrality_values)
                        std_centrality = (sum((x - avg_centrality) ** 2 for x in centrality_values) / len(centrality_values)) ** 0.5
                        
                        if show_stats:
                            st.markdown("---")
                            st.markdown("### 📊 Estadísticas de la Red")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric(
                                    "📈 Valor Máximo",
                                    f"{max_centrality:.4f}",
                                    help="El valor más alto de centralidad en la red"
                                )
                            
                            with col2:
                                st.metric(
                                    "📊 Promedio",
                                    f"{avg_centrality:.4f}",
                                    help="Valor promedio de centralidad"
                                )
                            
                            with col3:
                                st.metric(
                                    "📉 Valor Mínimo",
                                    f"{min_centrality:.4f}",
                                    help="El valor más bajo de centralidad en la red"
                                )
                            
                            with col4:
                                st.metric(
                                    "📏 Desviación Est.",
                                    f"{std_centrality:.4f}",
                                    help="Dispersión de los valores de centralidad"
                                )

                        top_central = sorted(
                            centrality_data.items(),
                            key=lambda x: x[1],
                            reverse=True
                        )[:50]

                        df_central = []
                        for i, (node_id, centrality_score) in enumerate(top_central):
                            node_data = graph.graph.nodes[node_id]
                            
                            df_central.append({
                                'Rank': i + 1,
                                'Investigador': node_data.get('name', 'Desconocido'),
                                'Puntuación': centrality_score,
                                'Papers': node_data.get('paper_count', 0),
                                'Colaboradores': graph.graph.degree(node_id),
                                'Ratio': f"{centrality_score/avg_centrality:.1f}x" if avg_centrality > 0 else "N/A"
                            })
                        
                        df_central = pd.DataFrame(df_central)
                        
                        st.markdown("---")
                        st.markdown("### Ranking de Investigadores Destacados")
                                 
                        st.dataframe(df_central, use_container_width=True, height=400)
                        
                        st.markdown("---")
                        st.markdown("### 🔍 Análisis Detallado")
                        
                        analysis_tab1,analysis_tab3 = st.tabs([
                            "Distribución", 
                            "Casos Específicos"
                        ])
                        
                        with analysis_tab1:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                fig_hist = px.histogram(
                                    x=centrality_values,
                                    nbins=30,
                                    labels={'x': 'Valor de Centralidad', 'y': 'Número de Investigadores'}
                                )
                                fig_hist.add_vline(x=avg_centrality, line_dash="dash", annotation_text="Promedio",line_color='red')
                                st.plotly_chart(fig_hist, use_container_width=True)
                            
                            with col2:
                                fig_box = px.box(
                                    y=centrality_values,
                                    title="Distribución y Valores Atípicos",
                                    labels={'y': 'Valor de Centralidad'}
                                )
                                st.plotly_chart(fig_box, use_container_width=True)
                      
                        
                        with analysis_tab3:
                            st.subheader("🎯 Análisis de Casos Específicos")
                            
                            # Clasificar investigadores en categorías
                            high_threshold = avg_centrality + std_centrality
                            low_threshold = avg_centrality - std_centrality
                            
                            high_central = [(k, v) for k, v in centrality_data.items() if v > high_threshold]
                            low_central = [(k, v) for k, v in centrality_data.items() if v < low_threshold]
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("#### 🌟 Investigadores de Alto Impacto")
                                st.info(f"Investigadores con centralidad > {high_threshold:.4f}")
                                
                                high_analysis = []
                                for node_id, centrality_score in sorted(high_central, key=lambda x: x[1], reverse=True)[:10]:
                                    node_data = graph.graph.nodes[node_id]
                                    high_analysis.append({
                                        'Investigador': node_data.get('name', 'Desconocido'),
                                        'Puntuación': f"{centrality_score:.4f}",
                                        'Papers': node_data.get('paper_count', 0)
                                    })
                                
                                if high_analysis:
                                    st.dataframe(pd.DataFrame(high_analysis), use_container_width=True)
                            
                            with col2:
                                st.markdown("#### 🔍 Investigadores Emergentes")
                                st.info("Investigadores con baja centralidad pero alta productividad")
                                
                                emerging = []
                                for node_id, centrality_score in centrality_data.items():
                                    node_data = graph.graph.nodes[node_id]
                                    papers = node_data.get('paper_count', 0)
                                    if centrality_score < avg_centrality and papers > 5:  
                                        emerging.append({
                                            'Investigador': node_data.get('name', 'Desconocido'),
                                            'Puntuación': f"{centrality_score:.4f}",
                                            'Papers': papers,
                                            'Potencial': papers / (centrality_score + 0.001)  
                                        })
                                
                                emerging_sorted = sorted(emerging, key=lambda x: x['Potencial'], reverse=True)[:10]
                                if emerging_sorted:
                                    emerging_df = pd.DataFrame(emerging_sorted)
                                    emerging_df = emerging_df[['Investigador', 'Puntuación', 'Papers']]  # Excluir columna interna
                                    st.dataframe(emerging_df, use_container_width=True)
                                else:
                                    st.warning("No se encontraron investigadores emergentes con los criterios actuales")

                        st.markdown("---")
                        st.markdown("### 🌐 Visualización de Red por Centralidad")
                        
                         
                        st.markdown("#### ⚙️ Configuración")
                        max_nodes_viz = st.slider(
                                "Nodos a mostrar:",
                                min_value=50,
                                max_value=200,
                                value=100,
                                step=25
                            )
                        
                        fig_network = create_advanced_graph_visualization(
                            graph, 
                            centrality_measure=centrality_data,
                            max_nodes=max_nodes_viz
                        )
                        if fig_network:
                            st.plotly_chart(fig_network, use_container_width=True)
                
                else:
                    st.error("❌ No se pudieron calcular las centralidades. Verifica que el grafo esté correctamente cargado.")
            
            with tab3:
                st.subheader("Patrones de Colaboración")
                
                patterns = analyzer.get_collaboration_patterns()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Colaboraciones Fuertes", len(patterns['strong_collaborations']))
                
                with col2:
                    st.metric("Colaboraciones Débiles", len(patterns['weak_collaborations']))
                
                with col3:
                    st.metric("Promedio de Colaboraciones", f"{patterns['avg_collaborations']:.2f}")
                
                st.subheader("Distribución de Colaboraciones")
                
                collab_counts = list(patterns['collaboration_distribution'].values())
                fig_dist = px.histogram(
                    x=collab_counts,
                    nbins=20,
                    title="Distribución del Número de Colaboraciones por Autor"
                )
                st.plotly_chart(fig_dist, use_container_width=True)
                
                if patterns['strong_collaborations']:
                    st.subheader("Colaboraciones Más Fuertes")
                    
                    strong_collab_df = []
                    for u, v, weight in patterns['strong_collaborations'][:10]:
                        name_u = graph.graph.nodes[u].get('name', 'Desconocido')
                        name_v = graph.graph.nodes[v].get('name', 'Desconocido')
                        strong_collab_df.append({
                            'Autor 1': name_u,
                            'Autor 2': name_v,
                            'Colaboraciones': weight
                        })
                    
                    df_strong = pd.DataFrame(strong_collab_df)
                    st.dataframe(df_strong)
            
            with tab4:
                st.subheader("⚖️ Análisis de Pesos de Colaboración")
                
                # Aquí se puede añadir análisis específico de pesos
                st.info("Funcionalidad en desarrollo - análisis detallado de pesos de colaboración")
            
            with tab5:
                st.subheader("🔬 Análisis de Tendencias de Investigación")
                
                # Importar y usar el analizador de keywords
                from src.graph_utils import KeywordAnalyzer, create_keyword_analysis_visualization, create_keyword_network_visualization
                
                keyword_analyzer = KeywordAnalyzer()
                
                if keyword_analyzer.keywords_graph:
                    # Estadísticas generales
                    keyword_stats = keyword_analyzer.get_keyword_statistics()
                    
                    if keyword_stats:
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Temas de Investigación", keyword_stats['total_keywords'])
                        
                        with col2:
                            st.metric("Investigadores Activos", keyword_stats['total_authors'])
                        
                        with col3:
                            st.metric("Conexiones Temáticas", keyword_stats['total_connections'])
                        
                        with col4:
                            st.metric("Promedio Frecuencia", f"{keyword_stats['avg_keyword_frequency']:.1f}")
                        
                        # Visualización principal
                        st.subheader("📊 Panorama de Investigación")
                        keyword_viz = create_keyword_analysis_visualization(keyword_stats)
                        if keyword_viz:
                            st.plotly_chart(keyword_viz, use_container_width=True)
                        
                        # Sub-tabs para diferentes análisis
                        subtab1, subtab2, subtab3, subtab4 = st.tabs([
                            "🏷️ Temas Principales", 
                            "🔗 Red Temática", 
                            "📈 Tendencias", 
                            "👥 Perfiles de Investigación"
                        ])
                        
                        with subtab1:
                            st.subheader("Temas de Investigación Más Relevantes")
                            
                            # Top keywords
                            top_keywords_df = pd.DataFrame(keyword_stats['keyword_frequencies'][:20])
                            top_keywords_df.columns = ['Tema', 'Frecuencia', 'Papers', 'Investigadores']
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.dataframe(top_keywords_df, height=400)
                            
                            with col2:
                                # Clustering de keywords
                                clusters = keyword_analyzer.get_keyword_clusters()
                                if clusters:
                                    st.subheader("Agrupaciones Temáticas")
                                    
                                    cluster_data = []
                                    for cluster in clusters[:10]:
                                        cluster_data.append({
                                            'Cluster': f"Grupo {cluster['cluster_id']}",
                                            'Temas': cluster['size'],
                                            'Relevancia': cluster['total_frequency'],
                                            'Cohesión': f"{cluster['avg_weight']:.2f}"
                                        })
                                    
                                    cluster_df = pd.DataFrame(cluster_data)
                                    st.dataframe(cluster_df)
                                    
                                    # Mostrar detalles del cluster seleccionado
                                    selected_cluster = st.selectbox(
                                        "Ver detalles del grupo:",
                                        range(min(len(clusters), 10)),
                                        format_func=lambda x: f"Grupo {clusters[x]['cluster_id']} ({clusters[x]['size']} temas)"
                                    )
                                    
                                    if selected_cluster is not None:
                                        cluster_info = clusters[selected_cluster]
                                        st.write("**Temas en este grupo:**")
                                        st.write(", ".join(cluster_info['keywords'][:10]))
                                        if len(cluster_info['keywords']) > 10:
                                            st.info(f"Y {len(cluster_info['keywords']) - 10} temas más...")
                        
                        with subtab2:
                            st.subheader("Red de Conexiones Temáticas")
                            
                            max_nodes_network = st.slider(
                                "Número máximo de elementos en la red:",
                                min_value=50,
                                max_value=200,
                                value=100,
                                step=25
                            )
                            
                            network_fig = create_keyword_network_visualization(
                                keyword_analyzer.keywords_graph, 
                                max_nodes=max_nodes_network
                            )
                            
                            if network_fig:
                                st.plotly_chart(network_fig, use_container_width=True)
                                st.info("💡 Los nodos azules representan temas de investigación, los coral representan investigadores. El tamaño indica la relevancia/productividad.")
                        
                        with subtab3:
                            st.subheader("Tendencias Emergentes")
                            
                            trending = keyword_analyzer.get_trending_keywords()
                            if trending:
                                trending_df = pd.DataFrame(trending[:15])
                                trending_df.columns = ['Tema', 'Puntuación', 'Frecuencia', 'Investigadores', 'Intensidad', 'Papers']
                                trending_df = trending_df[['Tema', 'Puntuación', 'Frecuencia', 'Investigadores']]
                                
                                # Gráfico de tendencias
                                fig_trending = px.scatter(
                                    trending_df,
                                    x='Frecuencia',
                                    y='Investigadores',
                                    size='Puntuación',
                                    hover_name='Tema',
                                    title="Mapa de Tendencias de Investigación",
                                    labels={
                                        'Frecuencia': 'Frecuencia en Literatura',
                                        'Investigadores': 'Número de Investigadores'
                                    }
                                )
                                
                                st.plotly_chart(fig_trending, use_container_width=True)
                                
                                st.subheader("Ranking de Tendencias")
                                st.dataframe(trending_df)
                        
                        with subtab4:
                            st.subheader("Perfiles de Investigación")
                            
                            author_analysis = keyword_analyzer.get_author_keyword_analysis()
                            if author_analysis:
                                # Buscar investigador específico
                                search_author = st.text_input("Buscar investigador:", placeholder="Ingresa el nombre del investigador")
                                
                                if search_author:
                                    # Filtrar por nombre
                                    filtered_authors = [
                                        auth for auth in author_analysis 
                                        if search_author.lower() in auth['author'].lower()
                                    ]
                                    
                                    if filtered_authors:
                                        st.subheader(f"Resultados para '{search_author}':")
                                        for author in filtered_authors[:5]:
                                            with st.expander(f"👨‍🔬 {author['author']}"):
                                                col1, col2 = st.columns(2)
                                                
                                                with col1:
                                                    st.metric("Diversidad Temática", author['keyword_diversity'])
                                                    st.metric("Papers", author['papers_count'])
                                                
                                                with col2:
                                                    st.write("**Temas principales:**")
                                                    for kw in author['top_keywords']:
                                                        st.write(f"• {kw['keyword']} (relevancia: {kw['weight']})")
                                    else:
                                        st.warning("No se encontraron investigadores con ese nombre")
                                
                                # Top investigadores por diversidad
                                st.subheader("Investigadores con Mayor Diversidad Temática")
                                
                                diversity_data = []
                                for author in author_analysis[:15]:
                                    diversity_data.append({
                                        'Investigador': author['author'],
                                        'Diversidad': author['keyword_diversity'],
                                        'Total Temas': author['total_keywords'],
                                        'Papers': author['papers_count']
                                    })
                                
                                diversity_df = pd.DataFrame(diversity_data)
                                st.dataframe(diversity_df)
                                
                                # Gráfico de diversidad vs productividad
                                fig_diversity = px.scatter(
                                    diversity_df,
                                    x='Papers',
                                    y='Diversidad',
                                    size='Total Temas',
                                    hover_name='Investigador',
                                    title="Diversidad Temática vs Productividad",
                                    labels={
                                        'Papers': 'Número de Papers',
                                        'Diversidad': 'Diversidad Temática'
                                    }
                                )
                                
                                st.plotly_chart(fig_diversity, use_container_width=True)
                        
                        # Buscador de temas relacionados
                        st.markdown("---")
                        st.subheader("🔍 Explorador Temático")
                        
                        search_query = st.text_input(
                            "Buscar temas relacionados:",
                            placeholder="Ej: machine learning, neural networks, etc."
                        )
                        
                        if search_query:
                            related_results = keyword_analyzer.search_related_keywords(search_query)
                            
                            if related_results:
                                st.success(f"Temas encontrados para '{search_query}':")
                                
                                if related_results['matching_keywords']:
                                    st.write("**Coincidencias exactas:**")
                                    for match in related_results['matching_keywords']:
                                        st.write(f"• {match}")
                                
                                if related_results['related_keywords']:
                                    st.write("**Temas relacionados:**")
                                    
                                    related_df = pd.DataFrame(related_results['related_keywords'])
                                    related_df.columns = ['Tema', 'Peso Total', 'Conexiones', 'Frecuencia', 'Relevancia']
                                    related_df = related_df[['Tema', 'Relevancia', 'Frecuencia', 'Conexiones']]
                                    
                                    st.dataframe(related_df)
                            else:
                                st.warning("No se encontraron temas relacionados con esa búsqueda")
                    
                    else:
                        st.warning("No se pudieron cargar las estadísticas de investigación")
                else:
                    st.error("No se pudo acceder al análisis de tendencias de investigación. Verifica que el sistema esté correctamente configurado.")
        else:
            st.error("No se pudo cargar el grafo.")
    
    elif page == "Rendimiento del Modelo":
        st.header("Rendimiento del Modelo")
        stats = load_performance_stats()
        
        if stats:
            st.subheader("Dashboard de Rendimiento")
            
            dashboard_fig = create_performance_dashboard(stats)
            if dashboard_fig:
                st.plotly_chart(dashboard_fig, use_container_width=True)
 
        
        show_model_performance(stats)
        
        st.markdown("---")
        show_difficult_cases(graph)
    
    elif page == "Buscar Autores":
        if graph:
            search_authors(graph)
        else:
            st.error("No se pudo cargar el grafo.")
    
if __name__ == "__main__":
    main()
