import streamlit as st
import networkx as nx
import plotly.graph_objects as go
import math
import plotly.express as px
import pandas as pd 
import numpy as np
from src.build_graph import Graph, ModelPerformanceTracker


@st.cache_data
def load_graph_data():
    """Carga el grafo desde el archivo GraphML"""
    try:
        graph = Graph('data/extract_result.json')
        graph.load_graph('author_collaboration_graph.graphml')
        return graph
    except Exception as e:
        graph.build_graph()
        graph.debug_graph_structure()
        graph.save_graph('author_collaboration_graph.graphml')
        st.rerun()

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

def apply_manual_decision(original_index, manual_decision,graph,stats):
    case_d = stats.get("difficult_cases_data")[original_index]
    name1 = case_d.get('name1')
    name2 = case_d.get('name2')
    data1 = graph.nodes[name1]
    data2 = graph.nodes[name2]
    if manual_decision =='No, diferente autor':
        return True
    merged_data = data1.copy()

    all_names1 = set(data1.get('all_names', []))
    all_names2 = set(data2.get('all_names', []))
    merged_names = all_names1.union(all_names2)

    if len(data1.get('name', '')) >= len(data2.get('name', '')):
        merged_data['name'] = data1.get('name', '')
    else:
        merged_data['name'] = data2.get('name', '')
        
    merged_data['all_names'] = list(merged_names)

    papers1 = set(data1.get('papers', []))
    papers2 = set(data2.get('papers', []))
    merged_papers = papers1.union(papers2)
    merged_data['papers'] = list(merged_papers)
    merged_data['paper_count'] = len(merged_papers)
    edges_to_transfer = list(graph.edges(data2, data=True))

    """for _, neighbor, edge_data in edges_to_transfer:
            if neighbor != node1:  
                if graph.has_edge(node1, neighbor):

                    current_weight = graph[node1][neighbor].get('weight', 1)
                    new_weight = edge_data.get('weight', 1)
                    graph[node1][neighbor]['weight'] = current_weight + new_weight
                else:
                    graph.add_edge(node1, neighbor, **edge_data)
        

        graph.remove_node(node2)

        graph.nodes[node1].update(merged_data)"""
def create_author_collaboration_graph(graph, author_name, collaborators):
    """Crea un grafo centrado en un autor específico y sus colaboradores"""
    if not collaborators:
        return None
    
    author_info = graph.get_author_info(author_name)
    if not author_info:
        return None
    
    author_pos = (0, 0)
    
    num_collaborators = min(len(collaborators),500) 
    angles = [2 * math.pi * i / num_collaborators for i in range(num_collaborators)]
    
    node_x = [author_pos[0]]
    node_y = [author_pos[1]]
    node_text = [f"<b>{author_info['representative_name']}</b><br>Papers: {author_info['paper_count']}<br>Colaboradores: {len(collaborators)}"]
    node_size = [40]  
    node_color = ['red']  
    
    edge_x = []
    edge_y = []
    

    for i, collab in enumerate(collaborators[:num_collaborators]):

        collab_x = 2 * math.cos(angles[i])
        collab_y = 2 * math.sin(angles[i])
        
        node_x.append(collab_x)
        node_y.append(collab_y)

        collab_text = f"<b>{collab['name']}</b><br>"
        collab_text += f"Colaboraciones: {collab['collaboration_count']}<br>"
        collab_text += f"Papers compartidos: {len(collab.get('shared_papers', []))}"
        
        node_text.append(collab_text)

        size = max(15, min(collab['collaboration_count'] * 3, 30))
        node_size.append(size)
        
        node_color.append(collab['collaboration_count'])

        edge_x.extend([author_pos[0], collab_x, None])
        edge_y.extend([author_pos[1], collab_y, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode='lines',
        line=dict(width=2, color='rgba(125,125,125,0.5)'),
        hoverinfo='none',
        showlegend=False
    )
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        text=node_text,
        marker=dict(
            size=node_size,
            color=node_color,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Colaboraciones", x=1.1),
            line=dict(width=2, color='white')
        ),
        showlegend=False
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    
    fig.update_layout(
        title=f"Red de Colaboración de {author_info['representative_name']}",
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        annotations=[
            dict(
                text=f"Autor principal (centro) conectado a colaboradores directos<br>Tamaño = intensidad de colaboración",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor="left", yanchor="bottom",
                font=dict(size=10)
            )
        ],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        height=400
    )
    
    return fig


def show_model_performance(stats):
    """Muestra estadísticas de rendimiento del modelo"""
    if not stats:
        st.warning("No hay estadísticas de rendimiento disponibles")
        return
    
    st.subheader("Estadísticas de Rendimiento del Modelo")
    
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
        st.subheader("Distribución de Probabilidades")
        
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
            st.subheader("⏱Evolución Temporal")
            
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

def show_difficult_cases(graph):
    """Muestra casos difíciles para revisión manual"""
    st.subheader("Casos Difíciles para Revisión Manual")

    stats = load_performance_stats()
    if not stats or 'difficult_cases_data' not in stats:
        st.info("No hay casos difíciles para revisar")
        return
    
    difficult_cases = stats['difficult_cases_data']
    
    if not difficult_cases:
        st.info("No hay casos difíciles para revisar")
        return
    
    st.info(f"Se encontraron {len(difficult_cases)} casos difíciles (probabilidad cercana al umbral)")

    col1, col2 = st.columns(2)
    with col1:
        show_filter = st.selectbox(
            "Mostrar casos:",
            ["Todos", "Solo pendientes", "Solo revisados"],
            index=0
        )
    
    with col2:
        if st.button("🔄 Actualizar datos"):
            load_graph_data.clear()
            load_performance_stats.clear()
            st.rerun()
    
    if show_filter == "Solo pendientes":
        filtered_cases = [case for case in difficult_cases if case.get('manual_decision') in [None, 'Sin decidir']]
    elif show_filter == "Solo revisados":
        filtered_cases = [case for case in difficult_cases if case.get('manual_decision') not in [None, 'Sin decidir']]
    else:
        filtered_cases = difficult_cases
    
    table_data = []
    for i, case in enumerate(filtered_cases):

        original_index = difficult_cases.index(case)
        
        table_data.append({
            'Caso': original_index + 1,
            'Nombre 1': case['name1'],
            'Nombre 2': case['name2'],
            'Probabilidad': f"{case['probability']:.3f}",
            'Umbral': f"{case['threshold']:.3f}",
            'Predicción': "Mismo autor" if case['prediction'] else "Diferente autor",
            'Decisión Manual': case.get('manual_decision', 'Sin decidir'),
            'Estado': '✅ Revisado' if case.get('manual_decision') not in [None, 'Sin decidir'] else '⏳ Pendiente'
        })
    

    if table_data:
        df_difficult = pd.DataFrame(table_data)
        st.dataframe(df_difficult, use_container_width=True)
        st.info(f"Mostrando {len(filtered_cases)} de {len(difficult_cases)} casos")
    else:
        st.info(f"No hay casos en la categoría '{show_filter}'")
    
    pending_cases = [case for case in difficult_cases if case.get('manual_decision') in [None, 'Sin decidir']]
    
    if pending_cases:
        st.subheader("Revisión Manual")
        
        case_options = [f"Caso {difficult_cases.index(case)+1}: {case['name1']} vs {case['name2']}" for case in pending_cases]
        selected_case_index = st.selectbox(
            "Seleccionar caso pendiente para revisar:",
            range(len(case_options)),
            format_func=lambda x: case_options[x]
        )
        
        if selected_case_index is not None:
            case = pending_cases[selected_case_index]
            original_index = difficult_cases.index(case)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Detalles del Caso:**")
                st.write(f"**Nombre 1:** {case['name1']}")
                st.write(f"**Nombre 2:** {case['name2']}")
                st.write(f"**Probabilidad:** {case['probability']:.3f}")
                st.write(f"**Umbral:** {case['threshold']:.3f}")
                st.write(f"**Predicción:** {'Mismo autor' if case['prediction'] else 'Diferente autor'}")

                if 'features' in case:
                    st.write("**Características:**")
                    for feature, value in case['features'].items():
                        st.write(f"  - {feature}: {value}")
            
            with col2:
                st.write("**Decisión Manual:**")
                current_decision = case.get('manual_decision', 'Sin decidir')
                
                manual_decision = st.radio(
                    "¿Son el mismo autor?",
                    ["Sin decidir", "Sí, mismo autor", "No, diferente autor"],
                    key=f"decision_{original_index}",
                    index=["Sin decidir", "Sí, mismo autor", "No, diferente autor"].index(current_decision) if current_decision in ["Sin decidir", "Sí, mismo autor", "No, diferente autor"] else 0
                )
                
                if manual_decision != "Sin decidir":
                    if st.button(f"Guardar decisión", key=f"save_{original_index}"):
                        decision_value = manual_decision == "Sí, mismo autor"
                        
                       
                        if graph:
                            success = apply_manual_decision(original_index, manual_decision,graph,stats)
                            if success:
                                st.success(f"Decisión aplicada: {'Mismo autor' if decision_value else 'Diferente autor'}")
                                st.success("Grafo actualizado correctamente")
                                st.info("🔄 Recargando la página para mostrar cambios...")
     
                                load_graph_data.clear()
                                load_performance_stats.clear()

                                st.rerun()
                            else:
                                st.error("Error al aplicar la decisión al grafo")
                        else:
                            st.error("Error al cargar el grafo")
    else:
        st.info("🎉 ¡Todos los casos difíciles han sido revisados!")
        st.success("No hay casos pendientes para revisar")
    
    st.subheader("Estadísticas de Revisión")
    
    reviewed_cases = [case for case in difficult_cases if case.get('manual_decision') not in [None, 'Sin decidir']]
    pending_cases_count = len(difficult_cases) - len(reviewed_cases)
    
    same_author_decisions = sum(1 for case in reviewed_cases if case.get('manual_decision') == 'Sí, mismo autor')
    different_author_decisions = sum(1 for case in reviewed_cases if case.get('manual_decision') == 'No, diferente autor')

    model_agreements = 0
    model_disagreements = 0
    
    for case in reviewed_cases:
        model_prediction = case.get('prediction', False)
        manual_decision = case.get('manual_decision') == 'Sí, mismo autor'
        
        if model_prediction == manual_decision:
            model_agreements += 1
        else:
            model_disagreements += 1
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Casos", len(difficult_cases))
    
    with col2:
        st.metric("Casos Revisados", len(reviewed_cases))
    
    with col3:
        st.metric("Casos Pendientes", pending_cases_count)
    
    with col4:
        progress_percentage = (len(reviewed_cases) / len(difficult_cases)) * 100 if difficult_cases else 0
        st.metric("Progreso", f"{progress_percentage:.1f}%")

    if reviewed_cases:
        st.subheader("Concordancia con el Modelo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Acuerdos con Modelo", model_agreements)
            st.metric("Desacuerdos con Modelo", model_disagreements)
        
        with col2:
            if len(reviewed_cases) > 0:
                agreement_rate = (model_agreements / len(reviewed_cases)) * 100
                st.metric("Tasa de Acuerdo", f"{agreement_rate:.1f}%")
        

        st.subheader("Distribución de Decisiones Manuales")
        
        col1, col2 = st.columns(2)
        
        with col1:
            decision_data = pd.DataFrame({
                'Decisión': ['Mismo autor', 'Diferente autor'],
                'Cantidad': [same_author_decisions, different_author_decisions]
            })
            
            if same_author_decisions > 0 or different_author_decisions > 0:
                fig_decisions = px.pie(
                    decision_data,
                    values='Cantidad',
                    names='Decisión',
                    title="Distribución de Decisiones Manuales"
                )
                st.plotly_chart(fig_decisions, use_container_width=True)
        
        with col2:
            discrepancy_cases = []
            for case in reviewed_cases:
                model_pred = case.get('prediction', False)
                manual_dec = case.get('manual_decision') == 'Sí, mismo autor'
                if model_pred != manual_dec:
                    discrepancy_cases.append({
                        'Caso': f"{case['name1']} vs {case['name2']}",
                        'Prob.': f"{case['probability']:.3f}",
                        'Modelo': "Mismo" if model_pred else "Diferente",
                        'Manual': "Mismo" if manual_dec else "Diferente"
                    })
            
            if discrepancy_cases:
                st.write("**Casos con Mayor Discrepancia:**")
                df_discrepancy = pd.DataFrame(discrepancy_cases)
                st.dataframe(df_discrepancy, use_container_width=True, height=200)
    
    if difficult_cases:
        st.subheader("Progreso de Revisión")
        progress_bar = st.progress(0)
        progress_value = len(reviewed_cases) / len(difficult_cases)
        progress_bar.progress(progress_value)
        
        st.write(f"**Progreso:** {len(reviewed_cases)} de {len(difficult_cases)} casos revisados ({progress_value*100:.1f}%)")

def show_graph_statistics(graph):
    """Muestra estadísticas del grafo"""
    if not graph:
        return
    
    stats = graph.get_statistics()
    
    st.subheader("Estadísticas del Grafo")


    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Autores", stats['total_authors'])
    
    with col2:
        st.metric("Total de Colaboraciones", stats['total_collaborations'])
    
    with col3:
        st.metric("Promedio de Colaboradores", f"{stats['average_collaborators']:.2f}")
    
    with col4:
        G = graph.graph
        density = nx.density(G) if G.number_of_nodes() > 1 else 0
        st.metric("Densidad del Grafo", f"{density:.4f}")

    st.subheader("Métricas Académicas")
    
    col1, col2, col3, col4 = st.columns(4)
 
    total_papers = stats.get('total_unique_papers', 0)
    avg_papers_per_author = total_papers / G.number_of_nodes() if G.number_of_nodes() > 0 else 0
    
    collaborator_counts = [G.degree(node) for node in G.nodes()]
    max_collaborators = max(collaborator_counts) if collaborator_counts else 0

    avg_clustering = nx.average_clustering(G, weight='weight') if G.number_of_nodes() > 0 else 0
    
    with col1:
        st.metric("Total de Papers", total_papers)
    
    with col2:
        st.metric("Papers por Autor", f"{avg_papers_per_author:.1f}")
    
    with col3:
        st.metric("Máx. Colaboradores", max_collaborators)
    
    with col4:
        st.metric("Coef. Clustering", f"{avg_clustering:.3f}")

    st.subheader("Distribución de Productividad")
    
    col1, col2 = st.columns(2)
    
    with col1:
        paper_counts = [data.get('paper_count', 0) for _, data in G.nodes(data=True)]
        fig_hist = px.histogram(
            x=paper_counts,
            nbins=20,
            title="Distribución de Papers por Autor",
            labels={'x': 'Número de Papers', 'y': 'Cantidad de Autores'}
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        fig_collab_hist = px.histogram(
            x=collaborator_counts,
            nbins=20,
            title="Distribución de Colaboradores por Autor",
            labels={'x': 'Número de Colaboradores', 'y': 'Cantidad de Autores'}
        )
        st.plotly_chart(fig_collab_hist, use_container_width=True)

    st.subheader("Análisis de Colaboraciones")
    
    col1, col2 = st.columns(2)
    
    with col1:
        strongest_collaborations = []
        for u, v, data in G.edges(data=True):
            weight = data.get('weight', 1)
            name_u = G.nodes[u].get('name', 'Desconocido')
            name_v = G.nodes[v].get('name', 'Desconocido')
            strongest_collaborations.append((name_u, name_v, weight))
        
        strongest_collaborations = sorted(strongest_collaborations, key=lambda x: x[2], reverse=True)[:10]
        
        if strongest_collaborations:
            df_strong = pd.DataFrame(strongest_collaborations, columns=['Autor 1', 'Autor 2', 'Colaboraciones'])
            
            fig_strong = px.bar(
                df_strong,
                x='Colaboraciones',
                y=[f"{row['Autor 1'][:15]}... - {row['Autor 2'][:15]}..." for _, row in df_strong.iterrows()],
                orientation='h',
                title="Top 10 Colaboraciones Más Fuertes"
            )
            st.plotly_chart(fig_strong, use_container_width=True)
    
    with col2:

        edge_weights = [data.get('weight', 1) for _, _, data in G.edges(data=True)]
        fig_weights = px.histogram(
            x=edge_weights,
            nbins=15,
            title="Distribución de Intensidad de Colaboraciones",
            labels={'x': 'Peso de Colaboración', 'y': 'Número de Colaboraciones'}
        )
        st.plotly_chart(fig_weights, use_container_width=True)

    st.subheader("Autores Más Prolíficos")
    
    prolific_authors = stats['most_prolific_authors'][:10]
    if prolific_authors:
        df_prolific = pd.DataFrame(prolific_authors, columns=['Autor', 'Número de Papers'])
        
        fig_bar = px.bar(
            df_prolific,
            x='Número de Papers',
            y='Autor',
            orientation='h',
            title="Top 10 Autores Más Prolíficos",
            color='Número de Papers',
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Análisis de Estructura de Red")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        num_components = nx.number_connected_components(G)
        largest_component_size = len(max(nx.connected_components(G), key=len)) if G.number_of_nodes() > 0 else 0
        st.metric("Componentes Conexas", num_components)
        st.metric("Componente Más Grande", largest_component_size)
    
    with col2:
        try:
            largest_component = G.subgraph(max(nx.connected_components(G), key=len))
            diameter = nx.diameter(largest_component)
            avg_path_length = nx.average_shortest_path_length(largest_component)
            st.metric("Diámetro de la Red", diameter)
            st.metric("Longitud Promedio Camino", f"{avg_path_length:.2f}")
        except:
            st.metric("Diámetro de la Red", "N/A")
            st.metric("Longitud Promedio Camino", "N/A")
    
    with col3:
        degrees = dict(G.degree())
        most_connected = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:5]
        
        st.write("**Top 5 Autores Más Conectados:**")
        for node, degree in most_connected:
            name = G.nodes[node].get('name', 'Desconocido')
            st.write(f"• {name[:30]}... ({degree} conexiones)")

    st.subheader("Métricas de Investigación")
    
    col1, col2 = st.columns(2)
    
    with col1:
        def gini_coefficient(values):
            if len(values) == 0:
                return 0
            sorted_values = sorted(values)
            n = len(sorted_values)
            cumsum = np.cumsum(sorted_values)
            return (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n if cumsum[-1] > 0 else 0
        
        paper_gini = gini_coefficient(paper_counts)
        collab_gini = gini_coefficient(collaborator_counts)
        
        st.metric("Índice Gini - Papers", f"{paper_gini:.3f}")
        st.metric("Índice Gini - Colaboradores", f"{collab_gini:.3f}")
        st.caption("0 = distribución perfectamente equitativa, 1 = máxima desigualdad")
    
    with col2:
        try:
            betweenness = nx.betweenness_centrality(G, weight='weight')
            top_influential = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]
            
            st.write("**Top 5 Autores Más Influyentes:**")
            for node, centrality in top_influential:
                name = G.nodes[node].get('name', 'Desconocido')
                st.write(f"• {name[:30]}... ({centrality:.3f})")
        except:
            st.write("**Autores Más Influyentes:** No disponible")
    

def search_authors(graph):
    """Interfaz para buscar autores específicos"""
    st.subheader("Buscar Autor")
    
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
            
            with col2:
                st.write("**Colaboradores:**")
                collaborators = graph.get_collaborators(search_term)
                
                if collaborators:
                    author_ego_graph = create_author_collaboration_graph(graph, search_term, collaborators)
                    if author_ego_graph:
                        st.plotly_chart(author_ego_graph, use_container_width=True)
                    
                else:
                    st.info("No se encontraron colaboradores")
            
            st.subheader("Papers del Autor")
            if author_info['papers']:
            
                papers_data = []
                for i, paper in enumerate(author_info['papers'][:20], 1): 
                    papers_data.append({
                        'N°': i,
                        'Título': paper if len(paper) <= 100 else paper[:100] + "...",
                        'Título Completo': paper
                    })
                
                df_papers = pd.DataFrame(papers_data)

                st.dataframe(
                    df_papers[['N°', 'Título']], 
                    use_container_width=True,
                    hide_index=True
                )
                
                if len(author_info['papers']) > 20:
                    st.info(f"Mostrando solo los primeros 20 de {len(author_info['papers'])} papers")

                selected_paper = st.selectbox(
                    "Selecciona un paper para ver el título completo:",
                    options=range(len(papers_data)),
                    format_func=lambda x: f"{x+1}. {papers_data[x]['Título']}",
                    key="paper_selector"
                )
                
                if selected_paper is not None:
                    st.write("**Título completo:**")
                    st.write(papers_data[selected_paper]['Título Completo'])
            else:
                st.info("No se encontraron papers para este autor")
            
            if collaborators:
                st.subheader("Colaboraciones Detalladas")
                
                selected_collab = st.selectbox(
                    "Selecciona un colaborador para ver papers compartidos:",
                    options=range(len(collaborators[:10])),
                    format_func=lambda x: f"{collaborators[x]['name']} ({collaborators[x]['collaboration_count']} colaboraciones)",
                    key="collab_selector"
                )
                
                if selected_collab is not None:
                    collab_info = collaborators[selected_collab]
                    st.write(f"**Papers compartidos con {collab_info['name']}:**")
                    
                    if collab_info['shared_papers']:
                        for i, paper in enumerate(collab_info['shared_papers'][:10], 1):
                            st.write(f"{i}. {paper}")
                        
                        if len(collab_info['shared_papers']) > 10:
                            st.info(f"Mostrando solo los primeros 10 de {len(collab_info['shared_papers'])} papers compartidos")
                    else:
                        st.info("No hay información de papers compartidos")
        else:
            st.error("Autor no encontrado")
            