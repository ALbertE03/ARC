import streamlit as st 
import json
import networkx as nx
from datetime import datetime
@st.cache_data
def load_graph():
    """Carga el grafo con artículos desde el archivo GraphML"""
    try:
        graph = nx.read_graphml("data/subgrafo_con_articulos.graphml")
        return graph
    except FileNotFoundError:
        st.error("No se encontró el archivo 'data/subgrafo_con_articulos.graphml'. Ejecuta primero add_articles.py")
        return None

@st.cache_data
def load_author_graph():
    """Carga el grafo autor-autor para análisis de colaboración"""
    try:
        graph = nx.read_graphml("data/grafo_autor_autor.graphml")
        return graph
    except FileNotFoundError:
        st.warning("No se encontró el archivo 'data/grafo_autor_autor.graphml'. Usando análisis básico.")
        return None

@st.cache_data
def load_article_graph():
    """Carga el grafo artículo-artículo para análisis de conexiones entre artículos"""
    try:
        graph = nx.read_graphml("data/grafo_articulo_articulo.graphml")
        return graph
    except FileNotFoundError:
        st.warning("No se encontró el archivo 'data/grafo_articulo_articulo.graphml'. El análisis de artículos no estará disponible.")
        return None


def save_graph(graph, filename="subgrafo_con_articulos.graphml"):
    """Guarda el grafo en formato GraphML"""
    try:
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

def load_consolidation_history():
    """
    Carga el historial de consolidaciones desde el archivo JSON
    """
    try:
        import os 
        if not os.path.exists("data/consolidation_history.json"):
            return []
        with open("data/consolidation_history.json", "r", encoding="utf-8") as f:
            history_data = json.load(f)
            return history_data.get('consolidations', [])
    except FileNotFoundError:
        return []
    except Exception as e:
        st.error(f"Error al cargar historial de consolidaciones: {str(e)}")
        return []

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


def clear_centralities_cache():
    """
    Limpia el cache de centralidades cuando el grafo se modifica
    """
    if 'centralities_cache' in st.session_state:
        st.session_state.centralities_cache = {}


def load_styles():
        
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

