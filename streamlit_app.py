import streamlit as st
import plotly.express as px
import pandas as pd
from src.graph_utils import GraphAnalyzer, create_advanced_graph_visualization, create_performance_dashboard, create_community_comparison_visualization, create_community_graph_visualization, create_wordcloud_visualization
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

            tab1, tab2, tab5 = st.tabs(["Comunidades", "Centralidad", "Análisis de Investigación"])

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
                                    labels={'x': 'Valor de Centralidad', 'y': 'Número de Investigadores'},
                                    title="Distribución de Centralidad en la Red"
                                )
                                fig_hist.add_vline(
                                    x=avg_centrality, 
                                    line_dash="dash", 
                                    annotation_text=f"📊 Promedio: {avg_centrality:.4f}",
                                    line_color='red',
                                    annotation_bordercolor="red",
                                    annotation_font_size=10
                                )
                                st.plotly_chart(fig_hist, use_container_width=True)
                            
                            with col2:
                                fig_box = px.box(
                                    y=centrality_values,
                                    title="Distribución y Valores Atípicos",
                                    labels={'y': 'Valor de Centralidad'}
                                )
                                st.plotly_chart(fig_box, use_container_width=True)
                      
                        
                        with analysis_tab3:
                            st.subheader("Análisis de Casos Específicos")

                            high_threshold = avg_centrality + std_centrality
                            low_threshold = avg_centrality - std_centrality
                            
                            high_central = [(k, v) for k, v in centrality_data.items() if v > high_threshold]
                            low_central = [(k, v) for k, v in centrality_data.items() if v < low_threshold]
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("#### Investigadores de Alto Impacto")
                                st.info(f"Investigadores con centralidad > {high_threshold:.4f} (std + avg)")
                                
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
                                max_value=len(graph.graph.nodes()),
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
            
          
            with tab5:
                st.subheader("🔬 Análisis de Tendencias de Investigación")

                from src.graph_utils import KeywordAnalyzer, create_keyword_analysis_visualization, create_keyword_network_visualization
                
                keyword_analyzer = KeywordAnalyzer()
                
                if keyword_analyzer.keywords_graph:
                    keyword_stats = keyword_analyzer.get_keyword_statistics()
                    
                    if keyword_stats:
                        # Métricas principales
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Temas de Investigación", keyword_stats['total_keywords'])
                        
                        with col2:
                            st.metric("Investigadores Activos", keyword_stats['total_authors'])
                        
                        with col3:
                            st.metric("Conexiones Temáticas", keyword_stats['total_connections'])
                        
                        with col4:
                            st.metric("Promedio Frecuencia", f"{keyword_stats['avg_keyword_frequency']:.1f}")

                        subtab1, subtab2, subtab3, subtab4 = st.tabs([
                            "🏷️ Temas Principales", 
                            "☁️ Nube de Palabras",
                            "🔗 Red Temática", 
                            "👥 Perfiles de Investigación"
                        ])
                        
                        with subtab1:
                            st.subheader("Temas de Investigación Más Relevantes")

                            try:
                                if keyword_stats['keyword_frequencies']:
                                    # Mostrar el panorama general primero
                                    st.subheader("📊 Panorama General")
                                    keyword_viz = create_keyword_analysis_visualization(keyword_stats)
                                    if keyword_viz:
                                        st.plotly_chart(keyword_viz, use_container_width=True)
                                    
                                    st.markdown("---")
                                    
                                    # Tabla de temas principales
                                    top_keywords_df = pd.DataFrame(keyword_stats['keyword_frequencies'][:20])
                                    top_keywords_df.columns = ['Tema', 'Frecuencia', 'Papers', 'Investigadores']
                                    
                                    
                                    
                                    st.subheader("🏆 Top 20 Temas")
                                    st.dataframe(top_keywords_df, height=400)
                                else:
                                    st.warning("No hay datos de keywords disponibles")
                                    col1, col2 = st.columns(2)
                            except Exception as e:
                                st.error(f"Error al procesar keywords: {e}")
                                col1, col2 = st.columns(2)
                            
                            
                            clusters = keyword_analyzer.get_keyword_clusters()
                            if clusters:
                                st.subheader("Agrupaciones Temáticas")
                                    
                                cluster_data = []
                                for cluster in clusters[:20]:
                                        cluster_data.append({
                                            'Cluster': f"Grupo {cluster['cluster_id']}",
                                            'Temas': cluster['size'],
                                            'Relevancia': cluster['total_frequency'],
                                            'Cohesión': f"{cluster['avg_weight']:.2f}"
                                        })
                                    
                                cluster_df = pd.DataFrame(cluster_data)
                                st.dataframe(cluster_df)

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
                        
                        with subtab3:
                            st.subheader("☁️ Nube de Palabras Clave")
                            st.markdown("Visualización interactiva de los temas de investigación más utilizados")
                            
                            col1, col2 = st.columns([3, 1])
                            
                            with col2:
                                st.markdown("**⚙️ Configuración:**")
                                
                                max_words = st.slider(
                                    "Número de palabras:",
                                    min_value=20,
                                    max_value=150,
                                    value=80,
                                    step=10,
                                    help="Controla cuántos temas mostrar en la nube"
                                )
                                
                                colormap_option = st.selectbox(
                                    "Esquema de colores:",
                                    ["viridis", "plasma", "inferno", "magma", "Blues", "Reds", "YlOrRd"],
                                    help="Diferentes paletas de colores para la visualización"
                                )
                                
                                st.markdown("**📊 Estadísticas rápidas:**")
                                total_unique_keywords = len(keyword_stats['keyword_frequencies'])
                                st.info(f"🏷️ **{total_unique_keywords}** temas únicos en total")
                                
                                if keyword_stats['keyword_frequencies'] and len(keyword_stats['keyword_frequencies']) > 0:
                                    try:
                                        top_keyword = keyword_stats['keyword_frequencies'][0]
                                        if isinstance(top_keyword, (list, tuple)) and len(top_keyword) >= 2:
                                            st.success(f"👑 Tema más frecuente: **{top_keyword[0]}** ({top_keyword[1]} apariciones)")
                                        else:
                                            st.warning("Estructura de datos de keywords no válida")
                                    except (IndexError, TypeError) as e:
                                        st.warning(f"Error al acceder a los datos de keywords: {e}")
                            

                            with col1:
                                with st.spinner("🎨 Generando nube de palabras..."):
                                    
                                    wordcloud_fig = create_wordcloud_visualization(
                                        keyword_stats, 
                                        max_words=max_words,
                                        colormap=colormap_option
                                    )
                                    
                                    if wordcloud_fig:
                                        st.plotly_chart(wordcloud_fig, use_container_width=True)
                                        
                                        # Información adicional sobre la nube de palabras
                                        st.markdown("---")
                                        col_a, col_b, col_c = st.columns(3)
                                        
                                        with col_a:
                                            st.metric(
                                                "Palabras mostradas", 
                                                min(max_words, len(keyword_stats['keyword_frequencies'])),
                                                help="Número de temas incluidos en la visualización"
                                            )
                                        
                                        with col_b:
                                            if keyword_stats['keyword_frequencies']:
                                                try:
                                                    coverage = sum(kw[1] for kw in keyword_stats['keyword_frequencies'][:max_words] if isinstance(kw, (list, tuple)) and len(kw) >= 2)
                                                    total_freq = sum(kw[1] for kw in keyword_stats['keyword_frequencies'] if isinstance(kw, (list, tuple)) and len(kw) >= 2)
                                                    coverage_pct = (coverage / total_freq * 100) if total_freq > 0 else 0
                                                    st.metric(
                                                        "Cobertura", 
                                                        f"{coverage_pct:.1f}%",
                                                        help="Porcentaje de frecencia total representada"
                                                    )
                                                except (IndexError, TypeError):
                                                    st.metric("Cobertura", "N/A", help="Error en datos")
                                        
                                        with col_c:
                                            if keyword_stats['keyword_frequencies']:
                                                try:
                                                    valid_keywords = [kw for kw in keyword_stats['keyword_frequencies'][:max_words] if isinstance(kw, (list, tuple)) and len(kw) >= 2]
                                                    if valid_keywords:
                                                        avg_freq_shown = sum(kw[1] for kw in valid_keywords) / len(valid_keywords)
                                                        st.metric(
                                                            "Freq. promedio", 
                                                            f"{avg_freq_shown:.1f}",
                                                            help="Frecuencia promedio de los temas mostrados"
                                                        )
                                                    else:
                                                        st.metric("Freq. promedio", "N/A", help="No hay datos válidos")
                                                except (IndexError, TypeError, ZeroDivisionError):
                                                    st.metric("Freq. promedio", "N/A", help="Error en datos")
                                    else:
                                        st.error("❌ No se pudo generar la nube de palabras. Instala la librería 'wordcloud' para una mejor experiencia.")
                                        st.code("pip install wordcloud", language="bash")
                            

                            # Tabla de los temas más frecuentes para referencia
                            with st.expander("📋 Ver lista detallada de temas"):
                                try:
                                    if keyword_stats['keyword_frequencies']:
                                        detailed_df = pd.DataFrame(keyword_stats['keyword_frequencies'][:max_words])
                                        detailed_df.columns = ['🏷️ Tema', '📊 Frecuencia', '📄 Papers', '👥 Investigadores']
                                        detailed_df.index = range(1, len(detailed_df) + 1)
                                        st.dataframe(detailed_df, use_container_width=True)
                                    else:
                                        st.warning("No hay datos de keywords disponibles")
                                except Exception as e:
                                    st.error(f"Error al mostrar la tabla: {e}")
                        
                        with subtab4:
                            st.subheader("Tendencias Emergentes")
                            
                            trending = keyword_analyzer.get_trending_keywords()
                            if trending:
                                trending_df = pd.DataFrame(trending[:15])
                                trending_df.columns = ['Tema', 'Puntuación', 'Frecuencia', 'Investigadores', 'Intensidad', 'Papers']
                                trending_df = trending_df[['Tema', 'Puntuación', 'Frecuencia', 'Investigadores']]

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
       
            st.error("No se pudo cargar el grafo.")
    
if __name__ == "__main__":
    main()
