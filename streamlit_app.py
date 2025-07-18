import streamlit as st
import plotly.express as px
import pandas as pd
from src.graph_utils import GraphAnalyzer, create_advanced_graph_visualization, create_performance_dashboard, create_community_comparison_visualization, create_community_graph_visualization, create_wordcloud_visualization
from src.utils import *

from src.graph_utils import KeywordAnalyzer, create_keyword_analysis_visualization, create_keyword_network_visualization
                
st.set_page_config(
    page_title="Visualizador de Grafo de Colaboración de Autores",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

st.title("🌐 Plataforma de Análisis de Redes de Investigación")


def main():
    """Función principal de la aplicación"""
    
    st.sidebar.title("📋 Navegación")
    page = st.sidebar.selectbox(
        "Selecciona una página:",
        ["Visualización del Grafo", "Análisis Avanzado", "Predicción de Colaboraciones", "Rendimiento del Modelo", "Buscar Autores"]
    )
    
    graph = load_graph_data()
    if page =='Predicción de Colaboraciones':
        analyzer = GraphAnalyzer(graph)
        keyword_analyzer1 = KeywordAnalyzer()
        st.subheader("Predicción de Futuras Colaboraciones")
        st.markdown("""
        Este sistema recomienda potenciales colaboradores para un investigador basándose en **intereses de investigación compartidos**. 
        Analiza las palabras clave de las publicaciones para encontrar expertos en temas similares que aún no han colaborado directamente.
        """)
        st.markdown("---")

        if keyword_analyzer1.keywords_graph:
            # Obtener lista de autores del grafo de keywords
            author_nodes = [
                data.get('name', 'Desconocido').replace(")","").replace("(", "").replace(".", "") 
                for node, data in keyword_analyzer1.keywords_graph.nodes(data=True) 
                if data.get('type') == 'author'
            ]
            author_nodes = sorted(list(set(author_nodes)))

            col1, col2 = st.columns([3, 1])

            with col1:
                selected_author = st.selectbox(
                    "Selecciona un investigador para obtener recomendaciones:",
                    options=author_nodes,
                    help="Elige un autor para ver con quién podría colaborar en el futuro."
                )
            
            with col2:
                top_n = st.slider(
                    "Número de recomendaciones:",
                    min_value=3,
                    max_value=15,
                    value=5,
                    help="¿Cuántos colaboradores potenciales deseas ver?"
                )

            if st.button("🔍 Encontrar Colaboradores Potenciales", use_container_width=True):
                if selected_author:
                    with st.spinner(f"Buscando recomendaciones para {selected_author}..."):
                        
                        # Pasamos el grafo principal para excluir colaboradores existentes
                        recommendations = keyword_analyzer1.recommend_collaborators(
                            selected_author,
                            graph.graph, # El grafo de colaboración principal
                            top_n=top_n
                        )

                    st.markdown("---")
                    
                    if recommendations:
                        st.success(f"**Top {len(recommendations)} recomendaciones para {selected_author}:**")
                        
                        for i, rec in enumerate(recommendations):
                            st.markdown(f"### **{i+1}. {rec['name']}**")
                            
                            col_a, col_b = st.columns(2)
                            
                            with col_a:
                                st.metric(
                                    label="Puntuación de Relevancia",
                                    value=f"{rec['score']:.2f}",
                                    help="Puntuación basada en intereses compartidos y productividad."
                                )
                            
                            with col_b:
                                st.metric(
                                    label="Papers Publicados",
                                    value=rec['paper_count']
                                )
                            
                            with st.expander("🔬 **Intereses de investigación compartidos (Palabras Clave)**"):
                                st.info(f"Ambos investigadores han trabajado en temas como:")
                                # Usamos markdown para una lista más compacta
                                keywords_list = " | ".join(f"`{kw}`" for kw in rec['reason_keywords'])
                                st.markdown(keywords_list)
                            
                            st.markdown("---")

                    else:
                        st.info(f"No se encontraron nuevas recomendaciones para {selected_author}")
                else:
                    st.warning("Por favor, selecciona un autor de la lista.")
        else:
            st.error("No se pudo cargar el grafo de palabras clave necesario para las recomendaciones.")
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
                st.subheader(" Análisis de Tendencias de Investigación")
                st.markdown("Un análisis profundo de los temas, conexiones y futuras direcciones de la investigación basado en las palabras clave de las publicaciones.")

                try:
                    keyword_analyzer = KeywordAnalyzer()
                    if not keyword_analyzer.keywords_graph:
                        st.error("No se pudo cargar el grafo de keywords. El análisis no puede continuar.")
                        st.stop() 
                    
                    keyword_stats = keyword_analyzer.get_keyword_statistics()
                    if not keyword_stats:
                        st.warning("No se pudieron generar las estadísticas de keywords.")
                        st.stop()
                except Exception as e:
                    st.error(f"Ocurrió un error crítico al inicializar el análisis de keywords: {e}")
                    st.stop()

                subtab1, subtab2, subtab3, subtab4 = st.tabs([
                    "**Panorama General**", 
                    "**Nube de Palabras**",
                    "**Red de Co-ocurrencia**", 
                    "**Tendencias Emergentes**"
                ])
                


                with subtab1:
                    st.subheader("Temas de Investigación Más Relevantes")
                    st.info("Visualización de los temas más frecuentes y cómo se agrupan en clústeres de investigación.")

                    clusters = keyword_analyzer.get_keyword_clusters()

                    def get_largest_cluster(clusters):
                        if not clusters:
                            return None
                        return max(clusters, key=lambda x: x['size'])
  
                    if 'selected_cluster_id' not in st.session_state:
                        largest_cluster = get_largest_cluster(clusters)
                        st.session_state.selected_cluster_id = largest_cluster['cluster_id'] if largest_cluster else None

                    def update_selected_cluster():

                        selected_id = st.session_state.cluster_selector_key
                        valid_clusters = [c['cluster_id'] for c in clusters]
                        if selected_id in valid_clusters:
                            st.session_state.selected_cluster_id = selected_id
                        else:

                            largest_cluster = get_largest_cluster(clusters)
                            st.session_state.selected_cluster_id = largest_cluster['cluster_id'] if largest_cluster else None

                    keyword_viz = create_keyword_analysis_visualization(keyword_stats)
                    if keyword_viz:
                        st.plotly_chart(keyword_viz, use_container_width=True)
                    
                    with st.expander("🏆 Ver el Top 20 de Temas en una tabla"):
                        top_keywords_df = pd.DataFrame(keyword_stats['keyword_frequencies'][:20])
                        df_display = top_keywords_df.rename(columns={
                            'keyword': 'Tema', 'frequency': 'Frecuencia', 
                            'papers': 'N° Papers', 'author_connections': 'N° Investigadores'
                        })
                        st.dataframe(df_display, use_container_width=True)

                    st.markdown("---")
                    st.subheader("Agrupaciones Temáticas (Clústeres)")
                    st.info("Algoritmos de comunidad detectan grupos de temas que suelen investigarse juntos.")

                    if clusters:
                        sorted_clusters = sorted(clusters, key=lambda x: x['size'], reverse=True)
                        
                        col1, col2 = st.columns([1, 2], gap="large")
                        with col1:
                            st.write("**Principales Grupos Temáticos:**")
                            cluster_data = [{
                                'Grupo': f"Grupo {c['cluster_id']}", 
                                'N° Temas': c['size'], 
                                'Relevancia': c['total_frequency']
                            } for c in sorted_clusters[:20]]
                            cluster_df = pd.DataFrame(cluster_data)
                            st.dataframe(cluster_df, hide_index=True, use_container_width=True)

                        with col2:

                            cluster_options = [c['cluster_id'] for c in sorted_clusters[:20]]
                            options_labels = [
                                f"Grupo {c['cluster_id']} ({c['size']} temas)" 
                                for c in sorted_clusters[:20]
                            ]
                            

                            current_value = (
                                st.session_state.selected_cluster_id 
                                if st.session_state.selected_cluster_id in cluster_options
                                else cluster_options[0]  
                            )

                            selected_id = st.selectbox(
                                "Explora un grupo temático:",
                                options=cluster_options,
                                index=cluster_options.index(current_value),
                                format_func=lambda x: options_labels[cluster_options.index(x)],
                                key="cluster_selector_key",
                                on_change=update_selected_cluster
                            )
                            

                            st.session_state.selected_cluster_id = selected_id

                            cluster_info = next((c for c in clusters if c['cluster_id'] == selected_id), None)
                            
                            if cluster_info:
                                st.write(f"**Importancia de los temas dentro del Grupo {selected_id}:**")
                                
                                cluster_weights = keyword_analyzer.get_keyword_weights_within_cluster(cluster_info['keywords'])

                                with st.expander("🕵️‍♂️ Ver Panel"):
                                    st.write(f"**Número de temas en este clúster:** `{len(cluster_weights)}`")
                                    st.write("**Pesos calculados para la nube de palabras**")
                                    st.json({k: v for i, (k, v) in enumerate(cluster_weights.items())})

                                if cluster_weights:
                                    cluster_keywords_data = [{'keyword': kw, 'frequency': weight} for kw, weight in cluster_weights.items()]
                                    cluster_stats_for_wc = {'keyword_frequencies': cluster_keywords_data}
                                    
                                    with st.spinner(f"🎨 Generando nube de palabras para el Grupo {selected_id}..."):
                                        cluster_wc_fig = create_wordcloud_visualization(
                                            cluster_stats_for_wc,
                                            max_words=len(cluster_info['keywords']),
                                            colormap='cividis'
                                        )
                                        if cluster_wc_fig:
                                            st.plotly_chart(cluster_wc_fig, use_container_width=True, config={'displayModeBar': False})
                                        else:
                                            st.warning("No se pudo generar la nube de palabras para este clúster.")
                                else:
                                    st.warning("No se pudieron calcular los pesos internos para este clúster.")
                    else:
                        st.warning("No se pudieron generar clústeres temáticos.")
                with subtab2:
                    st.subheader("Visualización Intuitiva de Temas Populares")
                    st.info("Una forma rápida de identificar los temas más dominantes en el campo de investigación. El tamaño de la palabra es proporcional a su frecuencia.")
                    
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        st.markdown("##### Configuración")
                        max_words = st.slider("Máximo de palabras:", 20, 200, 75, 5)
                        colormap = st.selectbox("Esquema de color:", ["viridis", "plasma", "cividis", "Blues", "YlOrRd"])

                    with col1:
                        with st.spinner("🎨 Generando nube de palabras..."):
                            wordcloud_fig = create_wordcloud_visualization(keyword_stats, max_words=max_words, colormap=colormap)
                            if wordcloud_fig:
                                st.plotly_chart(wordcloud_fig, use_container_width=True, config={'displayModeBar': False})
                            else:
                                st.error("No se pudo generar la nube de palabras. Asegúrate de que la librería 'wordcloud' esté instalada.")
                with subtab3:
                    st.subheader("Conexiones Entre Temas de Investigación")
                    
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        st.markdown("##### Configuración")
                        net_max_nodes = st.slider("Nodos a mostrar:", 25, 200, 75, 5, key="net_nodes")
                        weight_threshold = st.slider("Umbral de conexión:", 1, 10, 1, key="net_weight", help="Mostrar solo conexiones con un peso mayor o igual a este valor.")

                    with col1:
                        with st.spinner("🕸️ Construyendo la red de temas..."):
                            # Filtrar el grafo para la visualización
                            kw_graph = keyword_analyzer.keywords_graph.copy()
                            edges_to_remove = [(u, v) for u, v, data in kw_graph.edges(data=True) if data.get('weight', 0) < weight_threshold]
                            kw_graph.remove_edges_from(edges_to_remove)
                            
                            network_fig = create_keyword_network_visualization(kw_graph, max_nodes=net_max_nodes)
                            if network_fig:
                                st.plotly_chart(network_fig, use_container_width=True, height=700)
                            else:
                                st.warning("No se pudo generar la red temática.")

                with subtab4:
                    st.subheader("Identificación de Temas en Ascenso")
                    trending = keyword_analyzer.get_trending_keywords()
                    if trending:
                        trending_df = pd.DataFrame(trending)
                        trending_df_display = trending_df[['keyword', 'trending_score', 'frequency', 'author_connections']].rename(columns={
                            'keyword': 'Tema Emergente', 'trending_score': 'Puntuación de Tendencia',
                            'frequency': 'Frecuencia Actual', 'author_connections': 'N° Investigadores'
                        })

                        fig_trending = px.scatter(
                            trending_df_display,
                            x='Frecuencia Actual',
                            y='N° Investigadores',
                            size='Puntuación de Tendencia',
                            color='Puntuación de Tendencia',
                            hover_name='Tema Emergente',
                            color_continuous_scale='viridis',
                            size_max=60,
                            title="Mapa de Tendencias de Investigación"
                        )
                        st.plotly_chart(fig_trending, use_container_width=True)

                        with st.expander("🏆 Ver Ranking Detallado de Tendencias"):
                            st.dataframe(trending_df_display, use_container_width=True, hide_index=True)
                    else:
                        st.warning("No se pudieron calcular las tendencias emergentes.")
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
