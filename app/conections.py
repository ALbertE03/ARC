
import streamlit as st
from app.utils import clear_centralities_cache
from datetime import datetime


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
