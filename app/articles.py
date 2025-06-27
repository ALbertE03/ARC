import streamlit as st
from datetime import datetime
from app.utils import clear_centralities_cache



def show_article_management():
    """Muestra la página de gestión de artículos"""
    st.markdown("## 📄 Gestión de Artículos")
    
    tab1, tab2, tab3 = st.tabs(["➕ Agregar Artículo", "✏️ Editar Artículo"])
    
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
                    if title in st.session_state.graph.nodes():
                        st.error("❌ Ya existe un artículo con este título")
                    else:
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
                        
                        clear_centralities_cache()
                        
                        st.success("✅ Artículo agregado exitosamente")
                        st.rerun()
                else:
                    st.error("❌ El título es obligatorio")
    
    with tab2:
        st.markdown("### Editar Artículo Existente")
        
        articles = [n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'article']
        
        if articles:
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

                        clear_centralities_cache()
                        
                        st.success("✅ Artículo actualizado exitosamente")
                        st.rerun()
        else:
            st.info("No hay artículos en el grafo")
    
   