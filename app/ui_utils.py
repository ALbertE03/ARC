import streamlit as st
from db.db_connection import Neo4jConnection


def setup_page():
    """Configura el diseño de la página y los estilos CSS"""
    st.set_page_config(
        page_title="Academic Graph Explorer",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
    <style>
        :root {
            --primary-color: #4a6fa5;
            --secondary-color: #166088;
            --accent-color: #4fc3f7;
            --background-color: #f8f9fa;
            --card-color: #ffffff;
        }
        
        .main {
            padding: 0rem 1rem;
        }
        
        .stAlert > div {
            padding: 0.8rem 1.2rem;
            border-radius: 0.75rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        h1, h2, h3 {
            color: var(--secondary-color) !important;
        }
        
        .stButton>button {
            background-color: var(--primary-color);
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            transition: all 0.3s;
        }
        
        .stButton>button:hover {
            background-color: var(--secondary-color);
            transform: translateY(-2px);
        }
        
        .card {
            background-color: var(--card-color);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin-bottom: 1.5rem;
        }
        
        .tabs {
            display: flex;
            margin-bottom: 1rem;
        }
        
        .tab {
            padding: 0.5rem 1rem;
            cursor: pointer;
            border-radius: 8px 8px 0 0;
            margin-right: 4px;
            background-color: #e9ecef;
        }
        
        .tab.active {
            background-color: var(--primary-color);
            color: white;
        }
        
        .dataframe {
            border-radius: 8px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        }
        
        .stTextInput>div>div>input {
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def get_connection():
    """Establece una conexión con Neo4j y la almacena en caché"""
    try:
        conn = Neo4jConnection()
        conn.connect()
        return conn
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None


def show_sidebar():
    """Muestra la barra lateral con opciones de navegación"""
    with st.sidebar:
        st.header("🔍 Navegación")
        option = st.radio(
            "Seleccione una opción:",
            [
                "📊 Estadísticas de la BD",
                "👤 Buscar Autores",
                "📄 Buscar Trabajos",
                "🤝 Ver Colaboradores",
                "📚 Ver Trabajos de Autor",
                "🔬 Autores por Tema",
                "🧠 Explorador de Conceptos",
                "🏢 Instituciones y Países",
                "🌐 Análisis de Red de Colaboración",
            ],
        )
        return option
