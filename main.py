import streamlit as st
import networkx as nx
import plotly.graph_objects as go
from enhanced_overview import show_overview
from app.utils import *
from app.authors import show_author_management
from app.articles import show_article_management
from app.conections import show_connection_management
from app.network import show_network_analysis
from app.export import show_export_page

st.set_page_config(
    page_title="ARC Graph Editor",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded"
)
load_styles()
if 'metrics_cache' not in st.session_state:
    st.session_state.metrics_cache = {}

if 'graph_signatures' not in st.session_state:
    st.session_state.graph_signatures = {}

def create_graph_visualization(graph, selected_nodes=None):
    """Crea una visualización interactiva del grafo usando Plotly"""
    if len(graph.nodes()) == 0:
        return go.Figure()
    
    pos = nx.spring_layout(graph, k=1, iterations=50)
    
    author_nodes = [n for n, d in graph.nodes(data=True) if d.get('type') == 'author']
    article_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'article']
    
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




def main():
    st.markdown('<div class="main-header">🔗 ARC Graph Editor 2025</div>', unsafe_allow_html=True)
    st.markdown("---")

    if 'graph' not in st.session_state:
        st.session_state.graph = load_graph()
    
    if 'author_graph' not in st.session_state:
        st.session_state.author_graph = load_author_graph()

    if 'consolidation_history' not in st.session_state:
        st.session_state.consolidation_history = load_consolidation_history()
    
    if st.session_state.graph is None:
        st.error("No se pudo cargar el grafo principal. Asegúrate de que el archivo existe.")
        return
    
    with st.sidebar:
        st.markdown("### 📊 Panel de Control")
        
        num_nodes = len(st.session_state.graph.nodes())
        num_edges = len(st.session_state.graph.edges())
        num_authors = len([n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'author'])
        num_articles = len([n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'article'])
        
        author_graph_info = ""
        if st.session_state.author_graph is not None:
            author_nodes = len(st.session_state.author_graph.nodes())
            author_edges = len(st.session_state.author_graph.edges())
            author_graph_info = f"Red de Colaboración: {author_nodes} investigadores, {author_edges} colaboraciones"
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Nodos Totales", num_nodes)
            st.metric("Investigadores", num_authors)
        with col2:
            st.metric("Conexiones", num_edges)
            st.metric("Publicaciones", num_articles)
        
        if author_graph_info:
            st.info(f"🤝 {author_graph_info}")
        
    
        st.markdown("### 🧭 Navegación")
        page = st.selectbox(
            "¿Qué te gustaría hacer?",
            ["📈 Explorar mi Red", "👤 Gestionar Investigadores", "📄 Gestionar Publicaciones", "🔗 Conectar Colaboraciones", "🔍 Descubrir Patrones", "💾 Guardar Resultados"]
        )
        
    if page == "📈 Explorar mi Red":
        show_overview()
    elif page == "👤 Gestionar Investigadores":
        show_author_management()
    elif page == "📄 Gestionar Publicaciones":
        show_article_management()
    elif page == "🔗 Conectar Colaboraciones":
        show_connection_management()
    elif page == "🔍 Descubrir Patrones":
        show_network_analysis()
    elif page == "💾 Guardar Resultados":
        show_export_page()


def show_mixed_graph_analysis():
    """Análisis del grafo mixto autor-artículo"""
    st.markdown("### 🌐 Análisis de tu Red Completa")
    
    graph = st.session_state.graph

    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("📊 Ver Red Completa", type="primary", use_container_width=True):
            with st.spinner("Generando visualización de tu red completa..."):
                fig = create_graph_visualization(graph)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("👆 Visualiza cómo se conectan investigadores con sus publicaciones")
    
    with col2:
        st.markdown("#### 📋 Resumen de tu Red")
        num_authors = len([n for n, d in graph.nodes(data=True) if d.get('node_type') == 'author'])
        num_articles = len([n for n, d in graph.nodes(data=True) if d.get('node_type') == 'article'])
        
        st.metric("👥 Investigadores", num_authors)
        st.metric("📄 Publicaciones", num_articles)
        st.metric("🔗 Conexiones", len(graph.edges()))

def show_author_collaboration_analysis():
    """Análisis de la red de colaboración entre autores"""
    st.markdown("### 🤝 Red de Colaboración entre Investigadores")

    if 'author_graph' not in st.session_state or st.session_state.author_graph is None:
        if st.button("🔄 Generar Red de Colaboración", type="primary", use_container_width=True):
            with st.spinner("Creando red de colaboración entre investigadores..."):
                try:
                    author_graph = load_author_graph()
                    if author_graph is None:
                        author_graph = create_author_projection(st.session_state.graph)
                    
                    st.session_state.author_graph = author_graph
                    st.success("✅ Red de colaboración generada exitosamente")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al generar la red: {str(e)}")
        else:
            st.info("👆 Genera la red de colaboración para ver cómo trabajan juntos los investigadores")
        return
    
    author_graph = st.session_state.author_graph
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("📊 Ver Red de Colaboración", use_container_width=True):
            with st.spinner("Generando visualización de colaboraciones..."):
                fig = create_author_graph_visualization(author_graph)
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📊 Métricas de Colaboración")
        st.metric("👥 Investigadores", len(author_graph.nodes()))
        st.metric("🤝 Colaboraciones", len(author_graph.edges()))
        
        if len(author_graph.nodes()) > 0:
            density = nx.density(author_graph)
            st.metric("🌐 Densidad de Red", f"{density:.3f}")

def show_comparative_analysis():
    """Análisis comparativo entre ambas redes"""
    st.markdown("### 📊 Análisis Comparativo de Redes")
    
    graph = st.session_state.graph

    if 'author_graph' not in st.session_state or st.session_state.author_graph is None:
        st.warning("⚠️ Primero necesitas generar la red de colaboración")
        if st.button("🔄 Generar Red de Colaboración", type="primary"):
            with st.spinner("Generando red de colaboración..."):
                try:
                    author_graph = load_author_graph()
                    if author_graph is None:
                        author_graph = create_author_projection(graph)
                    st.session_state.author_graph = author_graph
                    st.success("✅ Red de colaboración generada")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        return
    
    author_graph = st.session_state.author_graph
    
    if st.button("📊 Ejecutar Análisis Comparativo", type="primary", use_container_width=True):
        with st.spinner("Realizando análisis comparativo..."):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🌐 Red Completa")
                st.metric("Nodos Totales", len(graph.nodes()))
                st.metric("Aristas Totales", len(graph.edges()))
                
                num_authors = len([n for n, d in graph.nodes(data=True) if d.get('node_type') == 'author'])
                num_articles = len([n for n, d in graph.nodes(data=True) if d.get('node_type') == 'article'])
                st.metric("Investigadores", num_authors)
                st.metric("Publicaciones", num_articles)
            
            with col2:
                st.markdown("#### 🤝 Red de Colaboración")
                st.metric("Investigadores", len(author_graph.nodes()))
                st.metric("Colaboraciones", len(author_graph.edges()))
                
                if len(author_graph.nodes()) > 0:
                    density = nx.density(author_graph)
                    st.metric("Densidad", f"{density:.3f}")

def create_author_projection(main_graph):
    """Crea una proyección de la red de colaboración entre autores"""
    author_graph = nx.Graph()
    
    authors = [n for n, d in main_graph.nodes(data=True) if d.get('node_type') == 'author']
    
    for author in authors:
        author_data = main_graph.nodes[author]
        author_graph.add_node(author, **author_data)

    for article_node in main_graph.nodes():
        article_data = main_graph.nodes[article_node]
        if article_data.get('node_type') == 'article':
            article_authors = [n for n in main_graph.neighbors(article_node) 
                             if main_graph.nodes[n].get('node_type') == 'author']
            
            for i, author1 in enumerate(article_authors):
                for author2 in article_authors[i+1:]:
                    if not author_graph.has_edge(author1, author2):
                        author_graph.add_edge(author1, author2, weight=1)
                    else:
                        author_graph[author1][author2]['weight'] += 1
    
    return author_graph

def create_author_graph_visualization(author_graph):
    """Crea una visualización específica para la red de autores"""
    if len(author_graph.nodes()) == 0:
        return go.Figure()
    
    pos = nx.spring_layout(author_graph, k=2, iterations=50)

    edge_x = []
    edge_y = []
    edge_weights = []
    
    for edge in author_graph.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        weight = edge[2].get('weight', 1)
        edge_weights.append(weight)
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    node_x = []
    node_y = []
    node_text = []
    node_sizes = []
    
    for node in author_graph.nodes():
        if node in pos:
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            node_data = author_graph.nodes[node]
            display_name = node_data.get('display_name', str(node))
            degree = author_graph.degree(node)
            node_text.append(f"{display_name}<br>Colaboraciones: {degree}")

            node_sizes.append(max(10, degree * 3))
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=[name.split('<br>')[0] for name in node_text],
        textposition="middle center",
        hoverinfo='text',
        hovertext=node_text,
        marker=dict(
            size=node_sizes,
            color='lightcoral',
            line=dict(width=2, color='darkred')
        ),
        name='Investigadores'
    )
    
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                        title='Red de Colaboración entre Investigadores',
                        titlefont_size=16,
                        showlegend=True,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        height=600
                    ))
    
    return fig
        

if __name__ == "__main__":
    main()
