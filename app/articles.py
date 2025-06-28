import streamlit as st
from datetime import datetime
from app.utils import clear_centralities_cache, save_article_modification_history, load_article_modification_history



def show_article_management():
    """Muestra la página de gestión de artículos"""
    st.markdown("## 📄 Gestión de Artículos")
    
    tab1, tab2, tab3 = st.tabs(["➕ Agregar Artículo", "✏️ Editar Artículo", "🕒 Historial de Modificaciones"])
    
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
                        user = st.session_state.get('user', 'desconocido')
                        now = datetime.now().isoformat()
                        modification_history = [{
                            'action': 'creación',
                            'user': user,
                            'timestamp': now,
                            'fields': {
                                'title': title,
                                'doi': doi,
                                'publication_year': publication_year,
                                'journal': journal,
                                'abstract': abstract,
                                'keywords': keywords,
                                'citation_count': citation_count,
                                'open_access': open_access
                            }
                        }]
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
                            'created_date': now,
                            'modification_history': modification_history
                        }
                        st.session_state.graph.add_node(title, **article_data)
                        clear_centralities_cache()
                        from app.utils import save_graph, load_article_graph
                        save_graph(st.session_state.graph)
                        # Guardar también el grafo de artículo-artículo
                        article_graph = load_article_graph()
                        if article_graph is not None:
                            # Actualizar nodo en grafo artículo-artículo
                            if title in article_graph.nodes:
                                article_graph.nodes[title].update({
                                    'title': title,
                                    'display_name': title,
                                    'doi': doi,
                                    'publication_year': publication_year,
                                    'journal': journal,
                                    'abstract': abstract,
                                    'keywords': keywords,
                                    'citation_count': citation_count,
                                    'open_access': open_access,
                                    'created_date': now
                                })
                            save_graph(article_graph, filename="grafo_articulo_articulo.graphml")
                            st.session_state.article_graph = article_graph
                        # Al agregar artículo, guardar historial externo
                        if submitted:
                            all_history = load_article_modification_history()
                            all_history[title] = modification_history
                            save_article_modification_history(all_history)
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
                # Cargar historial externo
                all_history = load_article_modification_history()
                article_history = all_history.get(selected_article, article_data.get('modification_history', []))
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
                        user = st.session_state.get('user', 'desconocido')
                        now = datetime.now().isoformat()
                        changes = {}
                        for field, old, new in [
                            ('title', article_data.get('title', ''), new_title),
                            ('doi', article_data.get('doi', ''), new_doi),
                            ('publication_year', article_data.get('publication_year', 2024), new_year),
                            ('journal', article_data.get('journal', ''), new_journal),
                            ('abstract', article_data.get('abstract', ''), new_abstract),
                            ('keywords', article_data.get('keywords', ''), new_keywords),
                            ('citation_count', article_data.get('citation_count', 0), new_citations),
                            ('open_access', article_data.get('open_access', False), new_open_access)
                        ]:
                            if old != new:
                                changes[field] = {'old': old, 'new': new}
                        # Actualizar historial
                        if 'modification_history' not in article_data:
                            article_data['modification_history'] = []
                        article_data['modification_history'].append({
                            'action': 'edición',
                            'user': user,
                            'timestamp': now,
                            'changes': changes
                        })
                        # Guardar historial externo
                        all_history = load_article_modification_history()
                        if new_title != selected_article:
                            all_history[new_title] = article_data['modification_history']
                            if selected_article in all_history:
                                del all_history[selected_article]
                        else:
                            all_history[selected_article] = article_data['modification_history']
                        save_article_modification_history(all_history)
                        # Si el título cambia, crear nuevo nodo y transferir datos y aristas
                        if new_title != selected_article:
                            G = st.session_state.graph
                            # Copiar datos y actualizar
                            new_data = dict(article_data)
                            new_data.update({
                                'title': new_title,
                                'display_name': new_title,
                                'doi': new_doi,
                                'publication_year': new_year,
                                'journal': new_journal,
                                'abstract': new_abstract,
                                'keywords': new_keywords,
                                'citation_count': new_citations,
                                'open_access': new_open_access,
                                'modified_date': now
                            })
                            G.add_node(new_title, **new_data)
                            # Transferir aristas
                            for u, v, d in list(G.edges(selected_article, data=True)):
                                if u == selected_article:
                                    G.add_edge(new_title, v, **d)
                                else:
                                    G.add_edge(u, new_title, **d)
                            for u, v, d in list(G.in_edges(selected_article, data=True)) if hasattr(G, 'in_edges') else []:
                                if v == selected_article:
                                    G.add_edge(u, new_title, **d)
                            # Eliminar nodo viejo
                            G.remove_node(selected_article)
                        else:
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
                                'modified_date': now,
                                'modification_history': article_data['modification_history']
                            })
                        clear_centralities_cache()
                        from app.utils import save_graph, load_article_graph
                        import networkx as nx
                        save_graph(st.session_state.graph)
                        # Guardar también el grafo de artículo-artículo
                        article_graph = load_article_graph()
                        if article_graph is not None:
                            # Si el título cambió, renombrar el nodo
                            if selected_article != new_title and selected_article in article_graph.nodes:
                                nx.relabel_nodes(article_graph, {selected_article: new_title}, copy=False)
                            # Actualizar atributos
                            if new_title in article_graph.nodes:
                                article_graph.nodes[new_title].update({
                                    'title': new_title,
                                    'display_name': new_title,
                                    'doi': new_doi,
                                    'publication_year': new_year,
                                    'journal': new_journal,
                                    'abstract': new_abstract,
                                    'keywords': new_keywords,
                                    'citation_count': new_citations,
                                    'open_access': new_open_access,
                                    'modified_date': now
                                })
                            save_graph(article_graph, filename="grafo_articulo_articulo.graphml")
                            st.session_state.article_graph = article_graph
                        st.success("✅ Artículo actualizado exitosamente")
                        st.rerun()
        else:
            st.info("No hay artículos en el grafo")
    
    with tab3:
        st.markdown("### Historial de Modificaciones de Artículos")
        all_history = load_article_modification_history()
        import pandas as pd
        rows = []
        for art_title, history in all_history.items():
            for entry in history:
                action = entry.get('action', '')
                user = entry.get('user', '')
                timestamp = entry.get('timestamp', '')
                if action == 'creación':
                    fields = entry.get('fields', {})
                    changes = '\n'.join([f"{k}: {v}" for k, v in fields.items()])
                else:
                    changes = '\n'.join([f"{k}: {v['old']} → {v['new']}" for k, v in entry.get('changes', {}).items()])
                rows.append({
                    'Artículo': art_title,
                    'Acción': action,
                    'Usuario': user,
                    'Fecha': timestamp,
                    'Cambios': changes
                })
        if rows:
            df_hist = pd.DataFrame(rows)
            df_hist = df_hist.sort_values(by="Fecha", ascending=False)
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info("No hay historial registrado para ningún artículo.")

