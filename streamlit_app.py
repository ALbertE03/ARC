import streamlit as st
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from build_graph import Graph, ModelPerformanceTracker
from graph_utils import GraphAnalyzer, ModelMetrics, create_advanced_graph_visualization, create_performance_dashboard
import json
import pickle
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import io


st.set_page_config(
    page_title="Visualizador de Grafo de Colaboración de Autores",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Visualizador de Grafo de Colaboración de Autores")
st.markdown("Sistema de resolución y consolidación de autores (ARC)")


@st.cache_data
def load_graph_data():
    """Carga el grafo desde el archivo GraphML"""
    try:
        graph = Graph('data/extract_result.json')
        graph.load_graph('author_collaboration_graph.graphml')
        return graph
    except Exception as e:
        st.error(f"Error al cargar el grafo: {e}")
        return None

@st.cache_data
def load_performance_stats():
    """Carga las estadísticas de rendimiento del modelo"""
    try:
        return ModelPerformanceTracker.load_performance()
    except Exception as e:
        st.error(f"Error al cargar estadísticas: {e}")
        return {}


def create_graph_visualization(graph, layout_type="spring", max_nodes=100):
    """Crea una visualización interactiva del grafo"""
    G = graph.graph
    
    if G.number_of_nodes() > max_nodes:
        degrees = dict(G.degree())
        top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
        G = G.subgraph([node for node, degree in top_nodes])
    
    if layout_type == "spring":
        pos = nx.spring_layout(G, k=3, iterations=50)
    elif layout_type == "circular":
        pos = nx.circular_layout(G)
    elif layout_type == "kamada_kawai":
        pos = nx.kamada_kawai_layout(G)
    else:
        pos = nx.spring_layout(G)

    edge_trace = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        weight = G[edge[0]][edge[1]].get('weight', 1)
        
        edge_trace.append(go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=min(weight, 10), color='rgba(125,125,125,0.5)'),
            hoverinfo='none',
            showlegend=False
        ))
    
    node_x = []
    node_y = []
    node_text = []
    node_size = []
    node_color = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        node_data = G.nodes[node]
        name = node_data.get('name', 'Desconocido')
        paper_count = node_data.get('paper_count', 0)
        all_names = node_data.get('all_names', [])
        
        hover_text = f"<b>{name}</b><br>"
        hover_text += f"Papers: {paper_count}<br>"
        hover_text += f"Colaboradores: {G.degree(node)}<br>"
        if len(all_names) > 1:
            hover_text += f"Otros nombres: {', '.join(all_names[1:])}"
        
        node_text.append(hover_text)
        node_size.append(max(10, min(paper_count * 2, 50)))
        node_color.append(paper_count)
    
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers',
        hoverinfo='text',
        text=node_text,
        marker=dict(
            size=node_size,
            color=node_color,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Número de Papers"),
            line=dict(width=2)
        ),
        showlegend=False
    )
    
    fig = go.Figure(data=edge_trace + [node_trace])
    fig.update_layout(
        title=f"Grafo de Colaboración de Autores ({G.number_of_nodes()} nodos, {G.number_of_edges()} aristas)",
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20,l=5,r=5,t=40),
        annotations=[
            dict(
                text="Tamaño del nodo = Número de papers<br>Color = Número de papers",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor="left", yanchor="bottom",
                font=dict(size=12)
            )
        ],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white'
    )
    
    return fig

def show_model_performance(stats):
    """Muestra estadísticas de rendimiento del modelo"""
    if not stats:
        st.warning("No hay estadísticas de rendimiento disponibles")
        return
    
    st.subheader("📈 Estadísticas de Rendimiento del Modelo")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Predicciones", stats.get('total_predictions', 0))
    
    with col2:
        st.metric("Casos Difíciles", stats.get('difficult_cases', 0))
    
    with col3:
        st.metric("Predicciones Positivas", stats.get('positive_predictions', 0))
    
    with col4:
        st.metric("Predicciones Negativas", stats.get('negative_predictions', 0))
    
    if 'predictions_data' in stats and stats['predictions_data']:
        st.subheader("📊 Distribución de Probabilidades")
        
        probs = [p['probability'] for p in stats['predictions_data']]
        
        fig_hist = px.histogram(
            x=probs,
            nbins=20,
            title="Distribución de Probabilidades de Predicción",
            labels={'x': 'Probabilidad', 'y': 'Frecuencia'}
        )
        fig_hist.add_vline(x=0.85, line_dash="dash", line_color="red", 
                          annotation_text="Umbral (0.85)")
        st.plotly_chart(fig_hist, use_container_width=True)

        if len(stats['predictions_data']) > 1:
            st.subheader("⏱️ Evolución Temporal")
            
            df_preds = pd.DataFrame(stats['predictions_data'])
            df_preds['timestamp'] = pd.to_datetime(df_preds['timestamp'])
            
            fig_time = px.line(
                df_preds,
                x='timestamp',
                y='probability',
                title="Evolución de Probabilidades en el Tiempo",
                labels={'timestamp': 'Tiempo', 'probability': 'Probabilidad'}
            )
            fig_time.add_hline(y=0.85, line_dash="dash", line_color="red")
            st.plotly_chart(fig_time, use_container_width=True)

def show_difficult_cases():
    """Muestra casos difíciles para revisión manual"""
    st.subheader("🤔 Casos Difíciles para Revisión Manual")

    stats = load_performance_stats()
    if not stats or 'difficult_cases_data' not in stats:
        st.info("No hay casos difíciles para revisar")
        return
    
    difficult_cases = stats['difficult_cases_data']
    
    if not difficult_cases:
        st.info("No hay casos difíciles para revisar")
        return
    
    st.info(f"Se encontraron {len(difficult_cases)} casos difíciles (probabilidad cercana al umbral)")
    
    for i, case in enumerate(difficult_cases):
        with st.expander(f"Caso {i+1}: {case['name1']} vs {case['name2']} (Prob: {case['probability']:.3f})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Nombre 1:**", case['name1'])
                st.write("**Nombre 2:**", case['name2'])
                st.write("**Probabilidad:**", f"{case['probability']:.3f}")
                st.write("**Umbral:**", f"{case['threshold']:.3f}")
                st.write("**Predicción del modelo:**", "Mismo autor" if case['prediction'] else "Diferente autor")
            
            with col2:
                st.write("**Decisión Manual:**")
                manual_decision = st.radio(
                    "¿Son el mismo autor?",
                    ["Sin decidir", "Sí, mismo autor", "No, diferente autor"],
                    key=f"decision_{i}",
                    index=0
                )
                
                if manual_decision != "Sin decidir":
                    if st.button(f"Guardar decisión", key=f"save_{i}"):
                        decision_value = manual_decision == "Sí, mismo autor"
                        st.success(f"Decisión guardada: {'Mismo autor' if decision_value else 'Diferente autor'}")

                        st.info("Funcionalidad de guardado en desarrollo")

def show_graph_statistics(graph):
    """Muestra estadísticas del grafo"""
    if not graph:
        return
    
    stats = graph.get_statistics()
    
    st.subheader("📊 Estadísticas del Grafo")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total de Autores", stats['total_authors'])
    
    with col2:
        st.metric("Total de Colaboraciones", stats['total_collaborations'])
    
    with col3:
        st.metric("Promedio de Colaboradores", f"{stats['average_collaborators']:.2f}")

    st.subheader("🌟 Autores Más Prolíficos")
    
    prolific_authors = stats['most_prolific_authors'][:10]
    if prolific_authors:
        df_prolific = pd.DataFrame(prolific_authors, columns=['Autor', 'Número de Papers'])
        
        fig_bar = px.bar(
            df_prolific,
            x='Número de Papers',
            y='Autor',
            orientation='h',
            title="Top 10 Autores Más Prolíficos"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

def search_authors(graph):
    """Interfaz para buscar autores específicos"""
    st.subheader("🔍 Buscar Autor")
    
    search_term = st.text_input("Ingresa el nombre del autor a buscar:")
    
    if search_term:
        author_info = graph.get_author_info(search_term)
        
        if author_info:
            st.success(f"Autor encontrado: {author_info['representative_name']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Información del Autor:**")
                st.write(f"- Nombre representativo: {author_info['representative_name']}")
                st.write(f"- Número de papers: {author_info['paper_count']}")
                st.write(f"- Todas las variantes del nombre:")
                for name in author_info['all_names']:
                    st.write(f"  • {name}")
            
            with col2:
                st.write("**Colaboradores:**")
                collaborators = graph.get_collaborators(search_term)
                
                if collaborators:
                    for collab in collaborators[:10]:  # Mostrar solo los primeros 10
                        st.write(f"- {collab['name']} ({collab['collaboration_count']} colaboraciones)")
                else:
                    st.info("No se encontraron colaboradores")
        else:
            st.error("Autor no encontrado")


def main():
    """Función principal de la aplicación"""
    
    st.sidebar.title("📋 Navegación")
    page = st.sidebar.selectbox(
        "Selecciona una página:",
        ["Visualización del Grafo", "Análisis Avanzado", "Rendimiento del Modelo", "Casos Difíciles", "Buscar Autores", "Recomendaciones"]
    )
    
    graph = load_graph_data()
    
    if page == "Visualización del Grafo":
        st.header("📊 Visualización del Grafo de Colaboración")
        
        if graph:
            st.sidebar.subheader("⚙️ Configuración")
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
        st.header("🔬 Análisis Avanzado del Grafo")
        
        if graph:
            analyzer = GraphAnalyzer(graph)
            
            tab1, tab2, tab3 = st.tabs(["Comunidades", "Centralidad", "Patrones de Colaboración"])
            
            with tab1:
                st.subheader("🏘️ Detección de Comunidades")
                with st.spinner("Detectando comunidades..."):
                    communities = analyzer.detect_communities()
                    
                if communities:
                    st.success(f"Se detectaron {len(set(communities.values()))} comunidades")
                    
                    community_sizes = defaultdict(int)
                    for node, comm in communities.items():
                        community_sizes[comm] += 1
                    
                    df_communities = pd.DataFrame(
                        list(community_sizes.items()),
                        columns=['Comunidad', 'Tamaño']
                    )
                    
                    fig_comm = px.bar(
                        df_communities,
                        x='Comunidad',
                        y='Tamaño',
                        title="Distribución de Comunidades"
                    )
                    st.plotly_chart(fig_comm, use_container_width=True)

                    st.subheader("Visualización con Comunidades")
                    fig_adv = create_advanced_graph_visualization(graph, communities=communities)
                    st.plotly_chart(fig_adv, use_container_width=True)
                else:
                    st.warning("No se pudieron detectar comunidades")
            
            with tab2:
                st.subheader("🎯 Medidas de Centralidad")
                
                centrality_type = st.selectbox(
                    "Selecciona el tipo de centralidad:",
                    ["Degree", "Betweenness", "Closeness", "Eigenvector"]
                )
                
                with st.spinner("Calculando centralidades..."):
                    centralities = analyzer.get_centrality_measures()
                
                if centralities:
                    centrality_key = f"{centrality_type.lower()}_centrality"
                    
                    if centrality_key in centralities:
                        centrality_data = centralities[centrality_key]

                        top_central = sorted(
                            centrality_data.items(),
                            key=lambda x: x[1],
                            reverse=True
                        )[:10]

                        df_central = []
                        for node_id, centrality_score in top_central:
                            node_data = graph.graph.nodes[node_id]
                            df_central.append({
                                'Autor': node_data.get('name', 'Desconocido'),
                                'Centralidad': centrality_score,
                                'Papers': node_data.get('paper_count', 0)
                            })
                        
                        df_central = pd.DataFrame(df_central)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader(f"Top 10 - {centrality_type} Centrality")
                            st.dataframe(df_central)
                        
                        with col2:
                            fig_central = px.bar(
                                df_central,
                                x='Centralidad',
                                y='Autor',
                                orientation='h',
                                title=f"Top 10 por {centrality_type} Centrality"
                            )
                            st.plotly_chart(fig_central, use_container_width=True)

                        st.subheader("Visualización por Centralidad")
                        fig_cent = create_advanced_graph_visualization(
                            graph, 
                            centrality_measure=centrality_data
                        )
                        st.plotly_chart(fig_cent, use_container_width=True)
                else:
                    st.warning("No se pudieron calcular las centralidades")
            
            with tab3:
                st.subheader("🤝 Patrones de Colaboración")
                
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
        else:
            st.error("No se pudo cargar el grafo.")
    
    elif page == "Recomendaciones":
        st.header("💡 Recomendaciones de Colaboración")
        
        if graph:
            st.subheader("🔍 Buscar Recomendaciones para un Autor")

            author_input = st.text_input("Ingresa el nombre del autor:")
            
            if author_input:
                analyzer = GraphAnalyzer(graph)
                
                with st.spinner("Generando recomendaciones..."):
                    recommendations = analyzer.get_author_recommendations(author_input)
                
                if recommendations:
                    st.success(f"Recomendaciones para {author_input}:")

                    for i, rec in enumerate(recommendations, 1):
                        with st.expander(f"{i}. {rec['name']} (Score: {rec['score']:.2f})"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**Conexiones mutuas:** {rec['mutual_connections']}")
                                st.write(f"**Papers:** {rec['paper_count']}")
                            
                            with col2:
                                st.write(f"**Puntaje de recomendación:** {rec['score']:.2f}")
 
                                if rec['mutual_connections'] > 0:
                                    st.write(f"✅ Tiene {rec['mutual_connections']} colaboradores en común")
                                if rec['paper_count'] > 5:
                                    st.write(f"✅ Autor prolífico con {rec['paper_count']} papers")
                else:
                    st.warning("No se encontraron recomendaciones para este autor.")
        else:
            st.error("No se pudo cargar el grafo.")
    
    elif page == "Rendimiento del Modelo":
        st.header("📈 Rendimiento del Modelo")
        stats = load_performance_stats()
        
        if stats:
            st.subheader("📊 Dashboard de Rendimiento")
            dashboard_fig = create_performance_dashboard(stats)
            if dashboard_fig:
                st.plotly_chart(dashboard_fig, use_container_width=True)
 
            metrics = ModelMetrics(stats)
            
            confusion_matrix = metrics.calculate_confusion_matrix()
            if confusion_matrix:
                st.subheader("🎯 Matriz de Confusión")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    matrix_data = [
                        ['Verdadero Positivo', confusion_matrix['tp']],
                        ['Falso Positivo', confusion_matrix['fp']],
                        ['Verdadero Negativo', confusion_matrix['tn']],
                        ['Falso Negativo', confusion_matrix['fn']]
                    ]
                    
                    df_matrix = pd.DataFrame(matrix_data, columns=['Tipo', 'Cantidad'])
                    st.dataframe(df_matrix)
                
                with col2:
                    st.metric("Precisión", f"{confusion_matrix['precision']:.3f}")
                    st.metric("Recall", f"{confusion_matrix['recall']:.3f}")
                    st.metric("Exactitud", f"{confusion_matrix['accuracy']:.3f}")
            
            st.subheader("⚖️ Análisis de Umbrales")
            threshold_analysis = metrics.get_threshold_analysis()
            
            if threshold_analysis:
                df_threshold = pd.DataFrame(threshold_analysis)
                
                fig_threshold = px.line(
                    df_threshold,
                    x='threshold',
                    y=['precision', 'recall', 'f1'],
                    title="Rendimiento por Umbral"
                )
                st.plotly_chart(fig_threshold, use_container_width=True)
        
        show_model_performance(stats)
    
    elif page == "Casos Difíciles":
        st.header("🤔 Casos Difíciles")
        show_difficult_cases()
    
    elif page == "Buscar Autores":
        st.header("🔍 Buscar Autores")
        if graph:
            search_authors(graph)
        else:
            st.error("No se pudo cargar el grafo.")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ Información")
    st.sidebar.markdown("Esta aplicación visualiza el grafo de colaboración de autores y permite revisar el rendimiento del modelo de resolución de entidades.")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Regenerar Grafo"):
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()
