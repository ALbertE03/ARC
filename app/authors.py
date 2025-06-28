import streamlit as st
from datetime import datetime
from app.utils import *
import os

def show_author_management():
    """Muestra la página de gestión de autores"""
    st.markdown("## 👤 Gestiona tus Investigadores")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Agregar Investigador", "✏️ Editar Investigador", "🗑️ Eliminar Investigador", "🔄 Unificar Perfiles", "↩️ Historial de Cambios"])
    
    with tab1:
        st.markdown("### Agregar Nuevo Investigador")
        
        with st.form("add_author_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                author_id = st.text_input("ID del Investigador*", placeholder="A1234567890")
                display_name = st.text_input("Nombre Completo*", placeholder="Dr. Juan Pérez")
                first_name = st.text_input("Nombre", placeholder="Juan")
                last_name = st.text_input("Apellido", placeholder="Pérez")
            
            with col2:
                orcid = st.text_input("ORCID", placeholder="0000-0000-0000-0000")
                affiliation = st.text_input("Institución", placeholder="Universidad XYZ")
                h_index = st.number_input("Índice H", min_value=0, value=0)
            
            submitted = st.form_submit_button("🔄 Agregar Investigador", use_container_width=True)
            
            if submitted:
                if author_id and display_name:
                    if author_id in st.session_state.graph.nodes():
                        st.error("❌ Este investigador ya existe en tu red")
                    else:
                        author_data = {
                            'node_type': 'author',
                            'id': author_id,
                            'display_name': display_name,
                            'first_name': first_name,
                            'last_name': last_name,
                            'orcid': orcid,
                            'affiliation': affiliation,
                            "summary_stats":{'h_index': h_index},
                            'created_date': datetime.now().isoformat()
                        }
                        
                        st.session_state.graph.add_node(author_id, **author_data)
                        save_graph(st.session_state.graph,filename='subgrafo_con_articulos.graphml')
                        clear_centralities_cache()
                        
                        st.success("✅ Investigador agregado exitosamente a tu red")
                        st.rerun()
                else:
                    st.error("❌ Los campos marcados con * son obligatorios")
    
    with tab2:
        st.markdown("### Editar Investigador Existente")
        
        authors = [n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'author']
        
        if authors:
            author_options = {}
            for author_id in authors:
                author_data = st.session_state.graph.nodes[author_id]
                display_name = author_data.get('display_name', author_id)
                author_options[display_name] = author_id
            
            selected_author_name = st.selectbox("Selecciona un investigador:", list(author_options.keys()))
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
                        new_affiliation = st.text_input("Institución", value=author_data.get('affiliation', ''))
                    
                    submitted = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)
                    
                    if submitted:
                        st.session_state.graph.nodes[selected_author].update({
                            'display_name': new_display_name,
                            'first_name': new_first_name,
                            'last_name': new_last_name,
                            'orcid': new_orcid,
                            'affiliation': new_affiliation,
                            'modified_date': datetime.now().isoformat()
                        })
                        save_graph(st.session_state.graph,filename='subgrafo_con_articulos.graphml')
                        clear_centralities_cache()
                        
                        st.success("✅ Investigador actualizado exitosamente")
                        st.rerun()
        else:
            st.info("No hay investigadores en tu red")
    
    with tab3:
        st.markdown("### Eliminar Autor")
        
        authors = [n for n, d in st.session_state.graph.nodes(data=True) if d.get('node_type') == 'author']
        
        if authors:
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
                    save_graph(st.session_state.graph,filename='subgrafo_con_articulos.graphml')
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
                selected_author_ids = [author_options[name] for name in selected_authors]
                
                st.markdown("#### Paso 2: Información de autores seleccionados")
                
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
                            st.write(f"**Afiliación:** {author_data.get('affiliation', 'N/A')}")
                            st.write(f"**Conexiones:** {connections}")
                
                st.markdown("#### Paso 3: Configurar autor consolidado")
                
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
                        all_orcids = [st.session_state.graph.nodes[aid].get('orcid', '') 
                                    for aid in selected_author_ids]
                        unique_orcids = [o for o in all_orcids if o and o != 'N/A']
                        
                        consolidated_orcid = st.selectbox(
                            "ORCID:", 
                            [''] + unique_orcids,
                            index=0 if not unique_orcids else 1
                        )
                        
                        consolidated_affiliation = st.text_input(
                            "Afiliación:", 
                            value=primary_data.get('affiliation', '')
                        )
                    
                    
                    submitted = st.form_submit_button("🔄 Consolidar Autores", type="primary")
                    
                    if submitted and consolidated_name:
            
                            consolidate_authors(
                                selected_author_ids, 
                                primary_author_id,
                                {
                                    'node_type': 'author',
                                    'display_name': consolidated_name,
                                    'first_name': consolidated_first,
                                    'last_name': consolidated_last,
                                    'orcid': consolidated_orcid,
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
    
    if 'consolidation_history' not in st.session_state:
        st.session_state.consolidation_history = load_consolidation_history()
    
    history = st.session_state.consolidation_history
    
    if not history:
        st.info("No se han realizado consolidaciones aún.")
        st.markdown("---")
        st.markdown("### 🔄 Rehacer Consolidación desde Archivo")
        
        if st.button("📂 Cargar Historial desde Archivo"):
            loaded_history = load_consolidation_history()
            if loaded_history:
                st.session_state.consolidation_history = loaded_history
                st.success(f"✅ Historial cargado: {len(loaded_history)} consolidaciones encontradas")
                st.rerun()
            else:
                st.warning("No se encontró historial guardado")
        return
    
    try:       
        with open(os.path.join('data','consolidation_history.json'), "r", encoding="utf-8") as f:
            file_data = json.load(f)
            st.info(f"📁 **Archivo:** consolidation_history.json | **Última actualización:** {file_data.get('last_updated', 'N/A')}")
    except Exception as e:
        print(e)
        st.warning("⚠️ No se pudo acceder al archivo de historial")
    
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

        author_names = [author['display_name'] for author in consolidation['original_authors']]
        if len(author_names) <= 2:
            authors_text = " y ".join(author_names)
        else:
            authors_text = ", ".join(author_names[:-1]) + f" y {author_names[-1]}"
        
        expander_title = f"🔄 {authors_text} se consolidaron en {consolidation['consolidated_name']}"
        
        with st.expander(expander_title, expanded=(i == 0)):
            st.markdown(f"### 📋 Resumen de Consolidación #{consolidation_id + 1}")
            st.markdown(f"**📅 Fecha:** {consolidation['date']}")
 
            st.markdown("### ✨ Resultado")
            st.success(f"**Autor Final:** {consolidation['consolidated_name']} (ID: {consolidation['consolidated_id']})")

            st.markdown("### 👥 Autores que se Consolidaron")
            st.markdown(f"**Total:** {len(consolidation['original_authors'])} autores")

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

                if j < len(consolidation['original_authors']) - 1:
                    st.markdown("---")

            st.markdown("### ⚙️ Acciones Disponibles")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🔄 Gestión de Consolidación")
 
                can_revert = consolidation['consolidated_id'] in st.session_state.graph.nodes()
                
                if can_revert:
                    if st.button(f"↩️ Revertir Consolidación", key=f"revert_{consolidation_id}", type="secondary", use_container_width=True):
                        if revert_consolidation(consolidation):
                            save_graph(st.session_state.graph, "subgrafo_con_articulos.graphml")  
                            save_consolidation_history()  
                            st.success("✅ Consolidación revertida exitosamente")
                            st.rerun()
                        else:
                            st.error("❌ Error al revertir la consolidación")
                    st.success("✅ Se puede revertir")
                else:
                    st.button(f"↩️ Revertir Consolidación", key=f"revert_{consolidation_id}_disabled", disabled=True, use_container_width=True)
                    st.warning("⚠️ No se puede revertir: el autor consolidado ya no existe")
                
                can_redo = check_can_redo_consolidation(consolidation)
                if can_redo['can_redo']:
                    if st.button(f"🔄 Rehacer Consolidación", key=f"redo_{consolidation_id}", type="primary", use_container_width=True):
                        if redo_consolidation(consolidation):
                            save_graph(st.session_state.graph, "subgrafo_con_articulos.graphml") 
                            save_consolidation_history()  
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

                if can_revert:
                    st.success("✅ **Estado:** Activa")
                    st.caption("Esta consolidación está activa y se puede revertir")
                else:
                    st.error("❌ **Estado:** Inactiva")
                    st.caption("El autor consolidado ya no existe en el grafo")

                total_original = len(consolidation['original_authors'])
                existing_authors = sum(1 for author in consolidation['original_authors'] 
                                     if author['id'] in st.session_state.graph.nodes())
                
                st.metric("Autores Originales", f"{existing_authors}/{total_original}", 
                         delta="Disponibles" if existing_authors > 0 else "No disponibles")

                if 'original_consolidation_date' in consolidation.get('consolidation_data', {}):
                    st.info(f"🔄 **Rehecha desde:** {consolidation['consolidation_data']['original_consolidation_date']}")

                if st.button(f"📋 Ver Detalles Técnicos", key=f"details_{consolidation_id}", help="Ver información técnica completa", use_container_width=True):
                    with st.expander("🔍 Datos Técnicos de la Consolidación", expanded=True):
                        st.json(consolidation)

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


def consolidate_authors(author_ids, consolidated_id, consolidated_data):
    """
    Consolida múltiples autores en uno solo y guarda el registro para poder revertir
    
    Args:
        author_ids: Lista de IDs de autores a consolidar
        consolidated_id: ID del autor consolidado
        consolidated_data: Datos del autor consolidado
    """
    graph = st.session_state.graph

    if 'consolidation_history' not in st.session_state:
        st.session_state.consolidation_history = []
    
    original_authors_info = []
    all_connections = set()
    
    for author_id in author_ids:
        author_data = dict(graph.nodes[author_id])
        author_data['id'] = author_id
        
        connections = []
        for neighbor in list(graph.neighbors(author_id)):
            if neighbor not in author_ids:  
                edge_data = graph.get_edge_data(author_id, neighbor)
                connections.append((neighbor, edge_data))
                all_connections.add((neighbor, json.dumps(edge_data) if edge_data else "{}"))
        
        author_data['connections'] = connections
        original_authors_info.append(author_data)
 
    consolidation_record = {
        'consolidated_id': consolidated_id,
        'consolidated_name': consolidated_data.get('display_name', 'N/A'),
        'original_authors': original_authors_info,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'consolidation_data': consolidated_data.copy()
    }

    for author_id in author_ids:
        graph.remove_node(author_id)

    graph.add_node(consolidated_id, **consolidated_data)

    for neighbor, edge_data_json in all_connections:
        edge_data = json.loads(edge_data_json) if edge_data_json != "{}" else {}
        graph.add_edge(consolidated_id, neighbor, **edge_data)

    st.session_state.consolidation_history.append(consolidation_record)

    clear_centralities_cache()

    save_graph(graph, "subgrafo_con_articulos.graphml")
    
    save_consolidation_history()

def check_can_redo_consolidation(consolidation_data):
    """
    Verifica si una consolidación se puede rehacer
    
    Args:
        consolidation_data: Datos de la consolidación a verificar
    
    Returns:
        dict: {'can_redo': bool, 'reason': str}
    """
    graph = st.session_state.graph

    if consolidation_data['consolidated_id'] in graph.nodes():
        return {'can_redo': False, 'reason': 'El autor consolidado ya existe'}

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

        can_redo_result = check_can_redo_consolidation(consolidation_data)
        if not can_redo_result['can_redo']:
            return False

        existing_author_ids = []
        for author_info in consolidation_data['original_authors']:
            if author_info['id'] in graph.nodes():
                existing_author_ids.append(author_info['id'])
        
        if not existing_author_ids:
            return False

        consolidation_data_copy = consolidation_data['consolidation_data'].copy()
        consolidation_data_copy['re_consolidated_date'] = datetime.now().isoformat()
        consolidation_data_copy['original_consolidation_date'] = consolidation_data['date']

        consolidate_authors(
            existing_author_ids,
            consolidation_data['consolidated_id'],
            consolidation_data_copy
        )
        
        return True
        
    except Exception as e:
        st.error(f"Error al rehacer consolidación: {str(e)}")
        return False
    



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

        if consolidated_id not in graph.nodes():
            return False

        current_connections = []
        for neighbor in list(graph.neighbors(consolidated_id)):
            edge_data = graph.get_edge_data(consolidated_id, neighbor)
            current_connections.append((neighbor, edge_data))

        graph.remove_node(consolidated_id)

        for author_info in consolidation_data['original_authors']:
            author_id = author_info['id']
            author_data = {k: v for k, v in author_info.items() if k not in ['id', 'connections']}
            graph.add_node(author_id, **author_data)

            for neighbor, edge_data in author_info['connections']:
                if neighbor in graph.nodes():  
                    graph.add_edge(author_id, neighbor, **(edge_data or {}))
  
        if consolidation_data['original_authors'] and current_connections:
            primary_author_id = consolidation_data['original_authors'][0]['id']
            if primary_author_id in graph.nodes():
                for neighbor, edge_data in current_connections:
                    original_neighbors = [conn[0] for conn in consolidation_data['original_authors'][0]['connections']]
                    if neighbor not in original_neighbors and neighbor in graph.nodes():
                        graph.add_edge(primary_author_id, neighbor, **(edge_data or {}))
        
        st.session_state.consolidation_history.remove(consolidation_data)
        
        clear_centralities_cache()
        
        return True
        
    except Exception as e:
        st.error(f"Error al revertir consolidación: {str(e)}")
        return False
