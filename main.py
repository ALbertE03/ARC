import streamlit as st
import networkx as nx
import pandas as pd
import json
import os
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    from collections import Counter, defaultdict
    import community as community_louvain
    from networkx.algorithms import bipartite
    import warnings
    warnings.filterwarnings('ignore')
    HAS_ADVANCED_LIBS = True
except ImportError:
    HAS_ADVANCED_LIBS = False

# Configuración de la página
st.set_page_config(
    page_title="ARC Graph Editor",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem;
    }
    
    .stSelectbox > div > div {
        background-color: black;
        border: 2px solid #e9ecef;
        border-radius: 8px;
    }
    
    .sidebar-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    .success-message {
        padding: 1rem;
        border-radius: 8px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    
    .warning-message {
        padding: 1rem;
        border-radius: 8px;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Función para cargar el grafo
@st.cache_data
def load_graph():
    """Carga el grafo con artículos desde el archivo GraphML"""
    try:
        graph = nx.read_graphml("data/subgrafo_con_articulos.graphml")
        return graph
    except FileNotFoundError:
        st.error("No se encontró el archivo 'data/subgrafo_con_articulos.graphml'. Ejecuta primero add_articles.py")
        return None

# Función para guardar el grafo
def save_graph(graph, filename="subgrafo_con_articulos.graphml"):
    """Guarda el grafo en formato GraphML"""
    try:
        # Convertir tipos no compatibles
        for n, d in graph.nodes(data=True):
            for k, v in list(d.items()):
                if v is None:
                    d[k] = ""
                elif isinstance(v, dict):
                    d[k] = json.dumps(v)
                elif isinstance(v, list):
                    d[k] = json.dumps(v)
        
        for u, v, d in graph.edges(data=True):
            for k, v2 in list(d.items()):
                if v2 is None:
                    d[k] = ""
                elif isinstance(v2, dict):
                    d[k] = json.dumps(v2)
                elif isinstance(v2, list):
                    d[k] = json.dumps(v2)
        
        nx.write_graphml(graph, f"data/{filename}")
        return True
    except Exception as e:
        st.error(f"Error al guardar el grafo: {str(e)}")
        return False

# Función para visualizar el grafo
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
        line=dict(width=1, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Crear trazas para nodos de autores
    author_x = [pos[node][0] for node in author_nodes]
    author_y = [pos[node][1] for node in author_nodes]
    author_text = [f"Autor: {node}" for node in author_nodes]
    
    author_trace = go.Scatter(
        x=author_x, y=author_y,
        mode='markers+text',
        hoverinfo='text',
        hovertext=author_text,
        text=[str(node)[:20] + "..." if len(str(node)) > 20 else str(node) for node in author_nodes],
        textposition="middle center",
        marker=dict(
            size=15,
            color='#667eea',
            line=dict(width=2, color='white')
        ),
        name='Autores'
    )
    
    # Crear trazas para nodos de artículos
    article_x = [pos[node][0] for node in article_nodes]
    article_y = [pos[node][1] for node in article_nodes]
    article_text = [f"Artículo: {node}" for node in article_nodes]
    
    article_trace = go.Scatter(
        x=article_x, y=article_y,
        mode='markers+text',
        hoverinfo='text',
        hovertext=article_text,
        text=[str(node)[:20] + "..." if len(str(node)) > 20 else str(node) for node in article_nodes],
        textposition="middle center",
        marker=dict(
            size=12,
            color='#764ba2',
            symbol='square',
            line=dict(width=2, color='white')
        ),
        name='Artículos'
    )
    
    # Crear figura
    fig = go.Figure(data=[edge_trace, author_trace, article_trace],
                   layout=go.Layout(
                       title='Grafo de Colaboración Académica',
                       titlefont_size=16,
                       showlegend=True,
                       hovermode='closest',
                       margin=dict(b=20,l=5,r=5,t=40),
                       annotations=[ dict(
                           text="Visualización interactiva del grafo de colaboración",
                           showarrow=False,
                           xref="paper", yref="paper",
                           x=0.005, y=-0.002,
                           xanchor='left', yanchor='bottom',
                           font=dict(color="#888", size=12)
                       )],
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       plot_bgcolor='white',
                       height=600
                   ))
    
    return fig

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
    
    # Calcular todas las centralidades sin mostrar mensajes intermedios
    centralities = {}
    
    try:
        # Crear placeholder para mostrar progreso
        progress_placeholder = st.empty()
        
        # Grado (rápido)
        progress_placeholder.info("🔄 Calculando centralidad de grado...")
        centralities['Grado'] = nx.degree_centrality(graph)
        
        # Intermediación (puede ser lento para grafos grandes)
        progress_placeholder.info("🔄 Calculando centralidad de intermediación...")
        if len(graph.nodes()) < 1000:  # Solo para grafos pequeños/medianos
            centralities['Intermediación'] = nx.betweenness_centrality(graph)
        else:
            # Para grafos grandes, usar muestreo
            centralities['Intermediación'] = nx.betweenness_centrality(graph, k=100)
        
        # Cercanía
        progress_placeholder.info("🔄 Calculando centralidad de cercanía...")
        if nx.is_connected(graph):
            centralities['Cercanía'] = nx.closeness_centrality(graph)
        else:
            # Para grafos no conectados, calcular por componente
            centralities['Cercanía'] = {}
            for component in nx.connected_components(graph):
                subgraph = graph.subgraph(component)
                closeness = nx.closeness_centrality(subgraph)
                centralities['Cercanía'].update(closeness)
        
        # Vector propio
        progress_placeholder.info("🔄 Calculando centralidad de vector propio...")
        try:
            centralities['Vector Propio'] = nx.eigenvector_centrality(graph, max_iter=1000)
        except:
            # Si falla, usar centralidad de grado como respaldo
            centralities['Vector Propio'] = centralities['Grado']
        
        # Limpiar placeholder de progreso
        progress_placeholder.empty()
            
    except Exception as e:
        st.error(f"Error calculando centralidades: {str(e)}")
        # Centralidades básicas como respaldo
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

# Función para limpiar cache de centralidades
def clear_centralities_cache():
    """
    Limpia el cache de centralidades cuando el grafo se modifica
    """
    if 'centralities_cache' in st.session_state:
        st.session_state.centralities_cache = {}

# Función principal
def main():
    # Header principal
    st.markdown('<div class="main-header">🔗 ARC Graph Editor 2025</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Cargar grafo
    if 'graph' not in st.session_state:
        st.session_state.graph = load_graph()
    
    # Cargar historial de consolidaciones
    if 'consolidation_history' not in st.session_state:
        st.session_state.consolidation_history = load_consolidation_history()
    
    if st.session_state.graph is None:
        st.error("No se pudo cargar el grafo. Asegúrate de que el archivo existe.")
        return
    
    # Sidebar para navegación
    with st.sidebar:
        st.markdown("### 📊 Panel de Control")
        
        # Métricas del grafo
        num_nodes = len(st.session_state.graph.nodes())
        num_edges = len(st.session_state.graph.edges())
        num_authors = len([n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'author'])
        num_articles = len([n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'article'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Nodos", num_nodes)
            st.metric("Autores", num_authors)
        with col2:
            st.metric("Aristas", num_edges)
            st.metric("Artículos", num_articles)
        
    
        st.markdown("### 🧭 Navegación")
        page = st.selectbox(
            "Selecciona una página:",
            ["📈 Vista General", "👤 Gestión de Autores", "📄 Gestión de Artículos", "🔗 Gestión de Conexiones", "� Análisis de Redes", "�💾 Exportar Datos"]
        )
        
    
    # Contenido principal según la página seleccionada
    if page == "📈 Vista General":
        show_overview()
    elif page == "👤 Gestión de Autores":
        show_author_management()
    elif page == "📄 Gestión de Artículos":
        show_article_management()
    elif page == "🔗 Gestión de Conexiones":
        show_connection_management()
    elif page == "� Análisis de Redes":
        show_network_analysis()
    elif page == "�💾 Exportar Datos":
        show_export_page()

def show_overview():
    """Muestra la página de vista general"""
    st.markdown("## 📈 Vista General del Grafo")
    
    # Visualización del grafo
    st.markdown("### Visualización Interactiva")
    
    # Botón para cargar la visualización
    if st.button("📊 Cargar Visualización del Grafo", type="primary", use_container_width=True):
        with st.spinner("Generando visualización del grafo..."):
            fig = create_graph_visualization(st.session_state.graph)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("👆 Haz clic en el botón para cargar la visualización interactiva del grafo")
    
    # Estadísticas detalladas
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Estadísticas de Autores")
        authors_df = pd.DataFrame([
            (node, data.get('display_name', 'N/A'), len(list(st.session_state.graph.neighbors(node))))
            for node, data in st.session_state.graph.nodes(data=True) 
            if data.get('node_type') == 'author'
        ], columns=['ID', 'Nombre', 'Conexiones'])
        
        if not authors_df.empty:
            st.dataframe(authors_df.head(10), use_container_width=True)
    
    with col2:
        st.markdown("### 📄 Estadísticas de Artículos")
        articles_df = pd.DataFrame([
            (node, data.get('display_name', 'N/A'), len(list(st.session_state.graph.neighbors(node))))
            for node, data in st.session_state.graph.nodes(data=True) 
            if data.get('node_type') == 'article'
        ], columns=['ID', 'Título', 'Autores'])
        
        if not articles_df.empty:
            st.dataframe(articles_df.head(10), use_container_width=True)

def show_author_management():
    """Muestra la página de gestión de autores"""
    st.markdown("## 👤 Gestión de Autores")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Agregar Autor", "✏️ Editar Autor", "🗑️ Eliminar Autor", "🔄 Consolidar Autores", "↩️ Historial de Consolidaciones"])
    
    with tab1:
        st.markdown("### Agregar Nuevo Autor")
        
        with st.form("add_author_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                author_id = st.text_input("ID del Autor*", placeholder="A1234567890")
                display_name = st.text_input("Nombre Completo*", placeholder="Dr. Juan Pérez")
                first_name = st.text_input("Nombre", placeholder="Juan")
                last_name = st.text_input("Apellido", placeholder="Pérez")
            
            with col2:
                orcid = st.text_input("ORCID", placeholder="0000-0000-0000-0000")
                scopus_id = st.text_input("Scopus ID", placeholder="12345678900")
                affiliation = st.text_input("Afiliación", placeholder="Universidad XYZ")
                h_index = st.number_input("H-Index", min_value=0, value=0)
            
            submitted = st.form_submit_button("🔄 Agregar Autor", use_container_width=True)
            
            if submitted:
                if author_id and display_name:
                    # Verificar si el autor ya existe
                    if author_id in st.session_state.graph.nodes():
                        st.error("❌ El ID del autor ya existe en el grafo")
                    else:
                        # Crear datos del autor
                        author_data = {
                            'node_type': 'author',
                            'id': author_id,
                            'display_name': display_name,
                            'first_name': first_name,
                            'last_name': last_name,
                            'orcid': orcid,
                            'scopus_id': scopus_id,
                            'affiliation': affiliation,
                            'h_index': h_index,
                            'created_date': datetime.now().isoformat()
                        }
                        
                        # Agregar al grafo
                        st.session_state.graph.add_node(author_id, **author_data)
                        
                        # Limpiar cache de centralidades
                        clear_centralities_cache()
                        
                        st.success("✅ Autor agregado exitosamente")
                        st.rerun()
                else:
                    st.error("❌ Los campos marcados con * son obligatorios")
    
    with tab2:
        st.markdown("### Editar Autor Existente")
        
        # Seleccionar autor
        authors = [n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'author']
        
        if authors:
            # Crear mapeo de nombres a IDs
            author_options = {}
            for author_id in authors:
                author_data = st.session_state.graph.nodes[author_id]
                display_name = author_data.get('display_name', author_id)
                author_options[display_name] = author_id
            
            selected_author_name = st.selectbox("Selecciona un autor:", list(author_options.keys()))
            selected_author = author_options[selected_author_name] if selected_author_name else None
            
            if selected_author:
                author_data = st.session_state.graph.nodes[selected_author]
                
                with st.form("edit_author_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_display_name = st.text_input("Nombre Completo", value=author_data.get('display_name', ''))
                        new_first_name = st.text_input("Nombre", value=author_data.get('first_name', ''))
                        new_last_name = st.text_input("Apellido", value=author_data.get('last_name', ''))
                    
                    with col2:
                        new_orcid = st.text_input("ORCID", value=author_data.get('orcid', ''))
                        new_scopus_id = st.text_input("Scopus ID", value=author_data.get('scopus_id', ''))
                        new_affiliation = st.text_input("Afiliación", value=author_data.get('affiliation', ''))
                    
                    submitted = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)
                    
                    if submitted:
                        # Actualizar datos
                        st.session_state.graph.nodes[selected_author].update({
                            'display_name': new_display_name,
                            'first_name': new_first_name,
                            'last_name': new_last_name,
                            'orcid': new_orcid,
                            'scopus_id': new_scopus_id,
                            'affiliation': new_affiliation,
                            'modified_date': datetime.now().isoformat()
                        })
                        
                        # Limpiar cache de centralidades
                        clear_centralities_cache()
                        
                        st.success("✅ Autor actualizado exitosamente")
                        st.rerun()
        else:
            st.info("No hay autores en el grafo")
    
    with tab3:
        st.markdown("### Eliminar Autor")
        
        authors = [n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'author']
        
        if authors:
            # Crear mapeo de nombres a IDs
            author_options = {}
            for author_id in authors:
                author_data = st.session_state.graph.nodes[author_id]
                display_name = author_data.get('display_name', author_id)
                author_options[display_name] = author_id
            
            selected_author_name = st.selectbox("Selecciona un autor para eliminar:", list(author_options.keys()))
            selected_author = author_options[selected_author_name] if selected_author_name else None
            
            if selected_author:
                author_data = st.session_state.graph.nodes[selected_author]
                connections = len(list(st.session_state.graph.neighbors(selected_author)))
                
                st.markdown(f"**Autor:** {author_data.get('display_name', 'N/A')}")
                st.markdown(f"**Conexiones:** {connections}")
                
                if connections > 0:
                    st.warning(f"⚠️ Este autor tiene {connections} conexiones que también serán eliminadas")
                
                if st.button("🗑️ Confirmar Eliminación", type="secondary"):
                    st.session_state.graph.remove_node(selected_author)
                    
                    # Limpiar cache de centralidades
                    clear_centralities_cache()
                    
                    st.success("✅ Autor eliminado exitosamente")
                    st.rerun()
        else:
            st.info("No hay autores en el grafo")
    
    with tab4:
        st.markdown("### 🔄 Consolidar Autores Duplicados")
        st.markdown("Esta función te permite fusionar múltiples entradas de autores que representan a la misma persona.")
        
        authors = [n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'author']
        
        if len(authors) < 2:
            st.info("Necesitas al menos 2 autores para poder consolidar")
        else:
            # Crear mapeo de nombres a IDs para autores
            author_options = {}
            for author_id in authors:
                author_data = st.session_state.graph.nodes[author_id]
                display_name = author_data.get('display_name', author_id)
                affiliation = author_data.get('affiliation', 'N/A')
                author_options[f"{display_name} ({affiliation}) - ID: {author_id}"] = author_id
            
            st.markdown("#### Paso 1: Selecciona autores a consolidar")
            st.info("💡 Selecciona múltiples autores que representan a la misma persona")
            
            selected_authors = st.multiselect(
                "Autores a consolidar:",
                list(author_options.keys()),
                help="Selecciona 2 o más autores que representan a la misma persona"
            )
            
            if len(selected_authors) >= 2:
                # Convertir nombres a IDs
                selected_author_ids = [author_options[name] for name in selected_authors]
                
                st.markdown("#### Paso 2: Información de autores seleccionados")
                
                # Mostrar información de cada autor seleccionado
                for i, author_name in enumerate(selected_authors):
                    author_id = author_options[author_name]
                    author_data = st.session_state.graph.nodes[author_id]
                    connections = len(list(st.session_state.graph.neighbors(author_id)))
                    
                    with st.expander(f"📄 {author_name}", expanded=(i == 0)):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**ID:** {author_id}")
                            st.write(f"**Nombre:** {author_data.get('display_name', 'N/A')}")
                            st.write(f"**Primer Nombre:** {author_data.get('first_name', 'N/A')}")
                            st.write(f"**Apellido:** {author_data.get('last_name', 'N/A')}")
                        
                        with col2:
                            st.write(f"**ORCID:** {author_data.get('orcid', 'N/A')}")
                            st.write(f"**Scopus ID:** {author_data.get('scopus_id', 'N/A')}")
                            st.write(f"**Afiliación:** {author_data.get('affiliation', 'N/A')}")
                            st.write(f"**Conexiones:** {connections}")
                
                st.markdown("#### Paso 3: Configurar autor consolidado")
                
                # Obtener datos del primer autor como base
                primary_author_id = selected_author_ids[0]
                primary_data = st.session_state.graph.nodes[primary_author_id]
                
                with st.form("consolidate_authors_form"):
                    st.markdown("**Datos del autor consolidado:**")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        consolidated_name = st.text_input(
                            "Nombre completo:", 
                            value=primary_data.get('display_name', ''),
                            help="Nombre que tendrá el autor consolidado"
                        )
                        consolidated_first = st.text_input(
                            "Primer nombre:", 
                            value=primary_data.get('first_name', '')
                        )
                        consolidated_last = st.text_input(
                            "Apellido:", 
                            value=primary_data.get('last_name', '')
                        )
                    
                    with col2:
                        # Recopilar todos los ORCIDs únicos
                        all_orcids = [st.session_state.graph.nodes[aid].get('orcid', '') 
                                    for aid in selected_author_ids]
                        unique_orcids = [o for o in all_orcids if o and o != 'N/A']
                        
                        consolidated_orcid = st.selectbox(
                            "ORCID:", 
                            [''] + unique_orcids,
                            index=0 if not unique_orcids else 1
                        )
                        
                        # Recopilar todos los Scopus IDs únicos
                        all_scopus = [st.session_state.graph.nodes[aid].get('scopus_id', '') 
                                    for aid in selected_author_ids]
                        unique_scopus = [s for s in all_scopus if s and s != 'N/A']
                        
                        consolidated_scopus = st.selectbox(
                            "Scopus ID:", 
                            [''] + unique_scopus,
                            index=0 if not unique_scopus else 1
                        )
                        
                        consolidated_affiliation = st.text_input(
                            "Afiliación:", 
                            value=primary_data.get('affiliation', '')
                        )
                    
                    # Opciones de consolidación
                    new_author_id = st.text_input(
                        "ID para el autor consolidado:",
                        value=primary_author_id,
                        help="ID que tendrá el nuevo autor consolidado(se recomienda no cambiar)"
                    )
                    
                    submitted = st.form_submit_button("🔄 Consolidar Autores", type="primary")
                    
                    if submitted and consolidated_name and new_author_id:
            
                        
                            # Realizar consolidación
                            consolidate_authors(
                                selected_author_ids, 
                                new_author_id,
                                {
                                    'node_type': 'author',
                                    'display_name': consolidated_name,
                                    'first_name': consolidated_first,
                                    'last_name': consolidated_last,
                                    'orcid': consolidated_orcid,
                                    'scopus_id': consolidated_scopus,
                                    'affiliation': consolidated_affiliation,
                                    'consolidated_from': selected_author_ids,
                                    'consolidation_date': datetime.now().isoformat()
                                }
                            )
                            st.success("✅ Autores consolidados exitosamente")
                            st.rerun()
                    elif submitted:
                        st.error("❌ El nombre y el ID son obligatorios")
            else:
                st.info("👆 Selecciona al menos 2 autores para consolidar")
    
    with tab5:
        show_consolidation_history()

def show_consolidation_history():
    """Muestra el historial de consolidaciones y permite revertirlas o rehacerlas"""
    st.markdown("### ↩️ Historial de Consolidaciones")
    st.markdown("Aquí puedes ver todas las consolidaciones realizadas, revertirlas o rehacerlas.")
    
    # Inicializar historial si no existe
    if 'consolidation_history' not in st.session_state:
        st.session_state.consolidation_history = load_consolidation_history()
    
    history = st.session_state.consolidation_history
    
    if not history:
        st.info("No se han realizado consolidaciones aún.")
        st.markdown("---")
        st.markdown("### 🔄 Rehacer Consolidación desde Archivo")
        
        # Opción para cargar historial desde archivo
        if st.button("📂 Cargar Historial desde Archivo"):
            loaded_history = load_consolidation_history()
            if loaded_history:
                st.session_state.consolidation_history = loaded_history
                st.success(f"✅ Historial cargado: {len(loaded_history)} consolidaciones encontradas")
                st.rerun()
            else:
                st.warning("No se encontró historial guardado")
        return
    
    # Mostrar información del archivo
    try:       
        with open(os.path.join('data','consolidation_history.json'), "r", encoding="utf-8") as f:
            file_data = json.load(f)
            st.info(f"📁 **Archivo:** consolidation_history.json | **Última actualización:** {file_data.get('last_updated', 'N/A')}")
    except Exception as e:
        print(e)
        st.warning("⚠️ No se pudo acceder al archivo de historial")
    
    # Mostrar historial en orden cronológico inverso
    st.markdown(f"**Total de consolidaciones:** {len(history)}")
    
    if len(history) > 0:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col3:
            if st.button("🔄 Recargar desde Archivo", help="Recargar historial desde archivo guardado"):
                st.session_state.consolidation_history = load_consolidation_history()
                st.success("✅ Historial recargado")
                st.rerun()
    
    for i, consolidation in enumerate(reversed(history)):
        consolidation_id = len(history) - i - 1
        
        # Crear título más descriptivo
        author_names = [author['display_name'] for author in consolidation['original_authors']]
        if len(author_names) <= 2:
            authors_text = " y ".join(author_names)
        else:
            authors_text = ", ".join(author_names[:-1]) + f" y {author_names[-1]}"
        
        expander_title = f"🔄 {authors_text} se consolidaron en {consolidation['consolidated_name']}"
        
        with st.expander(expander_title, expanded=(i == 0)):
            # Información principal de la consolidación
            st.markdown(f"### 📋 Resumen de Consolidación #{consolidation_id + 1}")
            st.markdown(f"**📅 Fecha:** {consolidation['date']}")
            
            # Mostrar el resultado de la consolidación
            st.markdown("### ✨ Resultado")
            st.success(f"**Autor Final:** {consolidation['consolidated_name']} (ID: {consolidation['consolidated_id']})")
            
            # Mostrar autores que se consolidaron
            st.markdown("### 👥 Autores que se Consolidaron")
            st.markdown(f"**Total:** {len(consolidation['original_authors'])} autores")
            
            # Crear columnas para mostrar los autores de manera más organizada
            for j, author_info in enumerate(consolidation['original_authors']):
                with st.container():
                    author_col1, author_col2 = st.columns([3, 1])
                    
                    with author_col1:
                        st.markdown(f"""
                        **{j+1}. {author_info['display_name']}**
                        - **ID:** `{author_info['id']}`
                        - **Afiliación:** {author_info.get('affiliation', 'N/A')}
                        - **ORCID:** {author_info.get('orcid', 'N/A')}
                        """)
                    
                    with author_col2:
                        st.metric("Conexiones", len(author_info['connections']))
                
                # Línea separadora entre autores (excepto el último)
                if j < len(consolidation['original_authors']) - 1:
                    st.markdown("---")
            
            # Sección de acciones
            st.markdown("### ⚙️ Acciones Disponibles")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🔄 Gestión de Consolidación")
                
                # Verificar si se puede revertir
                can_revert = consolidation['consolidated_id'] in st.session_state.graph.nodes()
                
                if can_revert:
                    if st.button(f"↩️ Revertir Consolidación", key=f"revert_{consolidation_id}", type="secondary", use_container_width=True):
                        if revert_consolidation(consolidation):
                            save_graph(st.session_state.graph, "subgrafo_con_articulos.graphml")  # Guardar cambios
                            save_consolidation_history()  # Actualizar historial
                            st.success("✅ Consolidación revertida exitosamente")
                            st.rerun()
                        else:
                            st.error("❌ Error al revertir la consolidación")
                    st.success("✅ Se puede revertir")
                else:
                    st.button(f"↩️ Revertir Consolidación", key=f"revert_{consolidation_id}_disabled", disabled=True, use_container_width=True)
                    st.warning("⚠️ No se puede revertir: el autor consolidado ya no existe")
                
                # Botón para rehacer consolidación
                can_redo = check_can_redo_consolidation(consolidation)
                if can_redo['can_redo']:
                    if st.button(f"🔄 Rehacer Consolidación", key=f"redo_{consolidation_id}", type="primary", use_container_width=True):
                        if redo_consolidation(consolidation):
                            save_graph(st.session_state.graph, "subgrafo_con_articulos.graphml")  # Guardar cambios
                            save_consolidation_history()  # Actualizar historial
                            st.success("✅ Consolidación rehecha exitosamente")
                            st.rerun()
                        else:
                            st.error("❌ Error al rehacer la consolidación")
                    st.info(f"🔄 {can_redo['reason']}")
                else:
                    st.button(f"🔄 Rehacer Consolidación", key=f"redo_{consolidation_id}_disabled", disabled=True, use_container_width=True)
                    st.warning(f"⚠️ No se puede rehacer: {can_redo['reason']}")
            
            with col2:
                st.markdown("#### 📊 Información de Estado")
                
                # Estado de la consolidación
                if can_revert:
                    st.success("✅ **Estado:** Activa")
                    st.caption("Esta consolidación está activa y se puede revertir")
                else:
                    st.error("❌ **Estado:** Inactiva")
                    st.caption("El autor consolidado ya no existe en el grafo")
                
                # Información de autores
                total_original = len(consolidation['original_authors'])
                existing_authors = sum(1 for author in consolidation['original_authors'] 
                                     if author['id'] in st.session_state.graph.nodes())
                
                st.metric("Autores Originales", f"{existing_authors}/{total_original}", 
                         delta="Disponibles" if existing_authors > 0 else "No disponibles")
                
                # Información adicional
                if 'original_consolidation_date' in consolidation.get('consolidation_data', {}):
                    st.info(f"🔄 **Rehecha desde:** {consolidation['consolidation_data']['original_consolidation_date']}")
                
                # Botón para ver detalles JSON
                if st.button(f"📋 Ver Detalles Técnicos", key=f"details_{consolidation_id}", help="Ver información técnica completa", use_container_width=True):
                    with st.expander("🔍 Datos Técnicos de la Consolidación", expanded=True):
                        st.json(consolidation)
    
    # Botón para exportar historial
    if history:
        st.markdown("---")
        st.markdown("### 📄 Exportar Datos")
        if st.button("📄 Exportar Historial Completo", help="Descargar historial como archivo JSON"):
            history_json = json.dumps(history, indent=2, ensure_ascii=False)
            st.download_button(
                label="💾 Descargar Historial JSON",
                data=history_json,
                file_name=f"historial_consolidaciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

def revert_consolidation(consolidation_data):
    """
    Revierte una consolidación específica
    
    Args:
        consolidation_data: Datos de la consolidación a revertir
    
    Returns:
        bool: True si se revirtió exitosamente, False en caso contrario
    """
    try:
        graph = st.session_state.graph
        consolidated_id = consolidation_data['consolidated_id']
        
        # Verificar que el nodo consolidado existe
        if consolidated_id not in graph.nodes():
            return False
        
        # Paso 1: Recopilar conexiones actuales del autor consolidado
        current_connections = []
        for neighbor in list(graph.neighbors(consolidated_id)):
            edge_data = graph.get_edge_data(consolidated_id, neighbor)
            current_connections.append((neighbor, edge_data))
        
        # Paso 2: Eliminar el autor consolidado
        graph.remove_node(consolidated_id)
        
        # Paso 3: Recrear los autores originales
        for author_info in consolidation_data['original_authors']:
            # Recrear el nodo del autor
            author_id = author_info['id']
            author_data = {k: v for k, v in author_info.items() if k not in ['id', 'connections']}
            graph.add_node(author_id, **author_data)
            
            # Recrear sus conexiones originales
            for neighbor, edge_data in author_info['connections']:
                if neighbor in graph.nodes():  # Solo si el nodo vecino aún existe
                    graph.add_edge(author_id, neighbor, **(edge_data or {}))
        
        # Paso 4: Distribuir conexiones nuevas que el autor consolidado pudiera haber adquirido
        # Las repartimos entre los autores originales (al primero por simplicidad)
        if consolidation_data['original_authors'] and current_connections:
            primary_author_id = consolidation_data['original_authors'][0]['id']
            if primary_author_id in graph.nodes():
                for neighbor, edge_data in current_connections:
                    # Solo agregar si no existía originalmente
                    original_neighbors = [conn[0] for conn in consolidation_data['original_authors'][0]['connections']]
                    if neighbor not in original_neighbors and neighbor in graph.nodes():
                        graph.add_edge(primary_author_id, neighbor, **(edge_data or {}))
        
        # Paso 5: Remover la consolidación del historial
        st.session_state.consolidation_history.remove(consolidation_data)
        
        # Paso 6: Limpiar cache de centralidades
        clear_centralities_cache()
        
        return True
        
    except Exception as e:
        st.error(f"Error al revertir consolidación: {str(e)}")
        return False

def check_can_redo_consolidation(consolidation_data):
    """
    Verifica si una consolidación se puede rehacer
    
    Args:
        consolidation_data: Datos de la consolidación a verificar
    
    Returns:
        dict: {'can_redo': bool, 'reason': str}
    """
    graph = st.session_state.graph
    
    # Verificar que el autor consolidado NO exista
    if consolidation_data['consolidated_id'] in graph.nodes():
        return {'can_redo': False, 'reason': 'El autor consolidado ya existe'}
    
    # Verificar que al menos uno de los autores originales exista
    existing_authors = []
    for author_info in consolidation_data['original_authors']:
        if author_info['id'] in graph.nodes():
            existing_authors.append(author_info['id'])
    
    if not existing_authors:
        return {'can_redo': False, 'reason': 'Ninguno de los autores originales existe'}
    
    return {'can_redo': True, 'reason': f'Se pueden consolidar {len(existing_authors)} autores'}

def redo_consolidation(consolidation_data):
    """
    Rehace una consolidación específica
    
    Args:
        consolidation_data: Datos de la consolidación a rehacer
    
    Returns:
        bool: True si se rehizo exitosamente, False en caso contrario
    """
    try:
        graph = st.session_state.graph
        
        # Verificar que se puede rehacer
        can_redo_result = check_can_redo_consolidation(consolidation_data)
        if not can_redo_result['can_redo']:
            return False
        
        # Identificar autores que aún existen
        existing_author_ids = []
        for author_info in consolidation_data['original_authors']:
            if author_info['id'] in graph.nodes():
                existing_author_ids.append(author_info['id'])
        
        if not existing_author_ids:
            return False
        
        # Rehacer la consolidación con los autores que existen
        consolidation_data_copy = consolidation_data['consolidation_data'].copy()
        consolidation_data_copy['re_consolidated_date'] = datetime.now().isoformat()
        consolidation_data_copy['original_consolidation_date'] = consolidation_data['date']
        
        # Usar la función de consolidación existente
        consolidate_authors(
            existing_author_ids,
            consolidation_data['consolidated_id'],
            consolidation_data_copy
        )
        
        return True
        
    except Exception as e:
        st.error(f"Error al rehacer consolidación: {str(e)}")
        return False

def consolidate_authors(author_ids, consolidated_id, consolidated_data):
    """
    Consolida múltiples autores en uno solo y guarda el registro para poder revertir
    
    Args:
        author_ids: Lista de IDs de autores a consolidar
        consolidated_id: ID del autor consolidado
        consolidated_data: Datos del autor consolidado
    """
    graph = st.session_state.graph
    
    # Inicializar historial si no existe
    if 'consolidation_history' not in st.session_state:
        st.session_state.consolidation_history = []
    
    # Paso 1: Guardar información completa de los autores originales
    original_authors_info = []
    all_connections = set()
    
    for author_id in author_ids:
        # Guardar datos del autor
        author_data = dict(graph.nodes[author_id])
        author_data['id'] = author_id
        
        # Guardar todas sus conexiones
        connections = []
        for neighbor in list(graph.neighbors(author_id)):
            if neighbor not in author_ids:  # No incluir conexiones entre autores a consolidar
                edge_data = graph.get_edge_data(author_id, neighbor)
                connections.append((neighbor, edge_data))
                all_connections.add((neighbor, json.dumps(edge_data) if edge_data else "{}"))
        
        author_data['connections'] = connections
        original_authors_info.append(author_data)
    
    # Paso 2: Crear registro de consolidación
    consolidation_record = {
        'consolidated_id': consolidated_id,
        'consolidated_name': consolidated_data.get('display_name', 'N/A'),
        'original_authors': original_authors_info,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'consolidation_data': consolidated_data.copy()
    }
    
    # Paso 3: Eliminar todos los autores originales
    for author_id in author_ids:
        graph.remove_node(author_id)
    
    # Paso 4: Crear el nuevo autor consolidado
    graph.add_node(consolidated_id, **consolidated_data)
    
    # Paso 5: Conectar el autor consolidado a todos los nodos que estaban conectados
    for neighbor, edge_data_json in all_connections:
        edge_data = json.loads(edge_data_json) if edge_data_json != "{}" else {}
        graph.add_edge(consolidated_id, neighbor, **edge_data)
    
    # Paso 6: Guardar el registro en el historial
    st.session_state.consolidation_history.append(consolidation_record)
    
    # Paso 7: Limpiar cache de centralidades
    clear_centralities_cache()
    
    # Paso 8: Guardar automáticamente el grafo modificado
    save_graph(graph, "subgrafo_con_articulos.graphml")
    
    # Paso 9: Guardar el historial de consolidaciones en archivo separado
    save_consolidation_history()

def save_consolidation_history():
    """
    Guarda el historial de consolidaciones en un archivo JSON separado
    """
    try:
        if 'consolidation_history' in st.session_state and st.session_state.consolidation_history:
            history_data = {
                'last_updated': datetime.now().isoformat(),
                'total_consolidations': len(st.session_state.consolidation_history),
                'consolidations': st.session_state.consolidation_history
            }
            
            with open("data/consolidation_history.json", "w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            return True
    except Exception as e:
        st.error(f"Error al guardar historial de consolidaciones: {str(e)}")
        return False

def load_consolidation_history():
    """
    Carga el historial de consolidaciones desde el archivo JSON
    """
    try:
        with open("data/consolidation_history.json", "r", encoding="utf-8") as f:
            history_data = json.load(f)
            return history_data.get('consolidations', [])
    except FileNotFoundError:
        return []
    except Exception as e:
        st.error(f"Error al cargar historial de consolidaciones: {str(e)}")
        return []

def show_article_management():
    """Muestra la página de gestión de artículos"""
    st.markdown("## 📄 Gestión de Artículos")
    
    tab1, tab2, tab3 = st.tabs(["➕ Agregar Artículo", "✏️ Editar Artículo", "🗑️ Eliminar Artículo"])
    
    with tab1:
        st.markdown("### Agregar Nuevo Artículo")
        
        with st.form("add_article_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Título del Artículo*", placeholder="Título del paper")
                doi = st.text_input("DOI", placeholder="10.1000/182")
                publication_year = st.number_input("Año de Publicación", min_value=1900, max_value=2025, value=2024)
                journal = st.text_input("Revista/Journal", placeholder="Nature")
            
            with col2:
                abstract = st.text_area("Resumen", placeholder="Resumen del artículo...")
                keywords = st.text_input("Palabras Clave", placeholder="keyword1, keyword2, keyword3")
                citation_count = st.number_input("Número de Citas", min_value=0, value=0)
                open_access = st.checkbox("Acceso Abierto")
            
            submitted = st.form_submit_button("🔄 Agregar Artículo", use_container_width=True)
            
            if submitted:
                if title:
                    # Verificar si el artículo ya existe
                    if title in st.session_state.graph.nodes():
                        st.error("❌ Ya existe un artículo con este título")
                    else:
                        # Crear datos del artículo
                        article_data = {
                            'node_type': 'article',
                            'display_name': title,
                            'title': title,
                            'doi': doi,
                            'publication_year': publication_year,
                            'journal': journal,
                            'abstract': abstract,
                            'keywords': keywords,
                            'citation_count': citation_count,
                            'open_access': open_access,
                            'created_date': datetime.now().isoformat()
                        }

                        st.session_state.graph.add_node(title, **article_data)
                        
                        # Limpiar cache de centralidades
                        clear_centralities_cache()
                        
                        st.success("✅ Artículo agregado exitosamente")
                        st.rerun()
                else:
                    st.error("❌ El título es obligatorio")
    
    with tab2:
        st.markdown("### Editar Artículo Existente")
        
        articles = [n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'article']
        
        if articles:
            # Crear mapeo de títulos a IDs
            article_options = {}
            for article_id in articles:
                article_data = st.session_state.graph.nodes[article_id]
                display_title = article_data.get('title', article_data.get('display_name', article_id))
                article_options[display_title] = article_id
            
            selected_article_name = st.selectbox("Selecciona un artículo:", list(article_options.keys()))
            selected_article = article_options[selected_article_name] if selected_article_name else None
            
            if selected_article:
                article_data = st.session_state.graph.nodes[selected_article]
                
                with st.form("edit_article_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_title = st.text_input("Título", value=article_data.get('title', ''))
                        new_doi = st.text_input("DOI", value=article_data.get('doi', ''))
                        new_year = st.number_input("Año", min_value=1900, max_value=2025, 
                                                 value=int(article_data.get('publication_year', 2024)))
                        new_journal = st.text_input("Revista", value=article_data.get('journal', ''))
                    
                    with col2:
                        new_abstract = st.text_area("Resumen", value=article_data.get('abstract', ''))
                        new_keywords = st.text_input("Palabras Clave", value=article_data.get('keywords', ''))
                        new_citations = st.number_input("Citas", min_value=0, 
                                                      value=int(article_data.get('citation_count', 0)))
                        new_open_access = st.checkbox("Acceso Abierto", 
                                                    value=bool(article_data.get('open_access', False)))
                    
                    submitted = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)
                    
                    if submitted:
                        # Actualizar datos
                        st.session_state.graph.nodes[selected_article].update({
                            'title': new_title,
                            'display_name': new_title,
                            'doi': new_doi,
                            'publication_year': new_year,
                            'journal': new_journal,
                            'abstract': new_abstract,
                            'keywords': new_keywords,
                            'citation_count': new_citations,
                            'open_access': new_open_access,
                            'modified_date': datetime.now().isoformat()
                        })
                        
                        # Limpiar cache de centralidades
                        clear_centralities_cache()
                        
                        st.success("✅ Artículo actualizado exitosamente")
                        st.rerun()
        else:
            st.info("No hay artículos en el grafo")
    
    with tab3:
        st.markdown("### Eliminar Artículo")
        
        articles = [n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'article']
        
        if articles:
            # Crear mapeo de títulos a IDs
            article_options = {}
            for article_id in articles:
                article_data = st.session_state.graph.nodes[article_id]
                display_title = article_data.get('title', article_data.get('display_name', article_id))
                article_options[display_title] = article_id
            
            selected_article_name = st.selectbox("Selecciona un artículo para eliminar:", list(article_options.keys()))
            selected_article = article_options[selected_article_name] if selected_article_name else None
            
            if selected_article:
                article_data = st.session_state.graph.nodes[selected_article]
                connections = len(list(st.session_state.graph.neighbors(selected_article)))
                
                st.markdown(f"**Título:** {article_data.get('title', 'N/A')}")
                st.markdown(f"**Autores:** {connections}")
                
                if connections > 0:
                    st.warning(f"⚠️ Este artículo tiene {connections} autores conectados")
                
                if st.button("🗑️ Confirmar Eliminación", type="secondary"):
                    st.session_state.graph.remove_node(selected_article)
                    
                    # Limpiar cache de centralidades
                    clear_centralities_cache()
                    
                    st.success("✅ Artículo eliminado exitosamente")
                    st.rerun()
        else:
            st.info("No hay artículos en el grafo")

def show_connection_management():
    """Muestra la página de gestión de conexiones"""
    st.markdown("## 🔗 Gestión de Conexiones")
    
    tab1, tab2 = st.tabs(["➕ Crear Conexión", "🗑️ Eliminar Conexión"])
    
    with tab1:
        st.markdown("### Crear Nueva Conexión")
        
        authors = [n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'author']
        articles = [n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'article']
        
        if authors and articles:
            col1, col2 = st.columns(2)
            
            with col1:
                # Crear mapeo de nombres a IDs para autores
                author_options = {}
                for author_id in authors:
                    author_data = st.session_state.graph.nodes[author_id]
                    display_name = author_data.get('display_name', author_id)
                    author_options[display_name] = author_id
                
                selected_author_name = st.selectbox("Selecciona un Autor:", list(author_options.keys()))
                selected_author = author_options[selected_author_name] if selected_author_name else None
                
                if selected_author:
                    author_data = st.session_state.graph.nodes[selected_author]
                    st.info(f"👤 {author_data.get('display_name', 'N/A')}")
            
            with col2:
                # Crear mapeo de títulos a IDs para artículos
                article_options = {}
                for article_id in articles:
                    article_data = st.session_state.graph.nodes[article_id]
                    display_title = article_data.get('title', article_data.get('display_name', article_id))
                    article_options[display_title] = article_id
                
                selected_article_name = st.selectbox("Selecciona un Artículo:", list(article_options.keys()))
                selected_article = article_options[selected_article_name] if selected_article_name else None
                
                if selected_article:
                    article_data = st.session_state.graph.nodes[selected_article]
                    st.info(f"📄 {article_data.get('title', 'N/A')}")
            
            connection_type = st.selectbox("Tipo de Conexión:", 
                                         ["corresponds_to", "authored", "co-authored", "reviewed"])
            
            if st.button("🔗 Crear Conexión", type="primary", use_container_width=True):
                if selected_author and selected_article:
                    if st.session_state.graph.has_edge(selected_author, selected_article):
                        st.warning("⚠️ Ya existe una conexión entre estos nodos")
                    else:
                        st.session_state.graph.add_edge(selected_author, selected_article, 
                                                      type=connection_type,
                                                      created_date=datetime.now().isoformat())
                        
                        # Limpiar cache de centralidades
                        clear_centralities_cache()
                        
                        st.success("✅ Conexión creada exitosamente")
                        st.rerun()
        else:
            st.warning("⚠️ Necesitas al menos un autor y un artículo para crear conexiones")
    
    with tab2:
        st.markdown("### Eliminar Conexión Existente")
        
        edges = list(st.session_state.graph.edges(data=True))
        
        if edges:
            edge_options = []
            for u, v, data in edges:
                u_data = st.session_state.graph.nodes[u]
                v_data = st.session_state.graph.nodes[v]
                u_name = u_data.get('display_name', u)
                v_name = v_data.get('display_name', v_data.get('title', v))
                edge_options.append(f"{u_name} ↔ {v_name}")
            
            selected_edge_idx = st.selectbox("Selecciona una conexión:", range(len(edge_options)),
                                           format_func=lambda x: edge_options[x])
            
            if st.button("🗑️ Eliminar Conexión", type="secondary", use_container_width=True):
                u, v, data = edges[selected_edge_idx]
                st.session_state.graph.remove_edge(u, v)
                
                # Limpiar cache de centralidades
                clear_centralities_cache()
                
                st.success("✅ Conexión eliminada exitosamente")
                st.rerun()
        else:
            st.info("No hay conexiones en el grafo")

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

def show_export_page():
    """Muestra la página de exportación"""
    st.markdown("## 💾 Exportar Datos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Exportar como CSV")
        
        if st.button("📥 Descargar Nodos", use_container_width=True):
            nodes_data = []
            for node, data in st.session_state.graph.nodes(data=True):
                node_info = {'id': node}
                node_info.update(data)
                nodes_data.append(node_info)
            
            nodes_df = pd.DataFrame(nodes_data)
            csv = nodes_df.to_csv(index=False)
            st.download_button(
                label="💾 Descargar CSV de Nodos",
                data=csv,
                file_name="nodos_grafo.csv",
                mime="text/csv"
            )
        
        if st.button("📥 Descargar Aristas", use_container_width=True):
            edges_data = []
            for u, v, data in st.session_state.graph.edges(data=True):
                edge_info = {'source': u, 'target': v}
                edge_info.update(data)
                edges_data.append(edge_info)
            
            edges_df = pd.DataFrame(edges_data)
            csv = edges_df.to_csv(index=False)
            st.download_button(
                label="💾 Descargar CSV de Aristas",
                data=csv,
                file_name="aristas_grafo.csv",
                mime="text/csv"
            )
    
    with col2:
        st.markdown("### 💾 Guardar Grafo")
        
        filename = st.text_input("Nombre del archivo:", value="subgrafo_con_articulos_editado.graphml")
        
        if st.button("💾 Guardar GraphML", type="primary", use_container_width=True):
            if save_graph(st.session_state.graph, filename):
                st.success(f"✅ Grafo guardado como '{filename}'")
            else:
                st.error("❌ Error al guardar el grafo")
        
        st.markdown("### 📈 Estadísticas del Grafo")
        stats = {
            "Total de Nodos": len(st.session_state.graph.nodes()),
            "Total de Aristas": len(st.session_state.graph.edges()),
            "Autores": len([n for n, d in st.session_state.graph.nodes(data=True) if d.get('type') == 'author']),
            "Artículos": len([n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'article']),
            "Densidad": round(nx.density(st.session_state.graph), 4),
            "Componentes Conectados": nx.number_connected_components(st.session_state.graph)
        }
        
        for key, value in stats.items():
            st.metric(key, value)

if __name__ == "__main__":
    main()
