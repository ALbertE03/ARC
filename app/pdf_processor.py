import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from improved_academic_extractor import ImprovedAcademicExtractor, process_pdf_improved
from app.utils import save_graph, clear_centralities_cache
import networkx as nx


def get_progress_file_path():
    """Retorna la ruta del archivo de progreso de procesamiento de PDFs"""
    return Path("data/pdf_processing_progress.json")


def save_processing_progress(state):
    """Guarda el progreso del procesamiento de PDFs de manera persistente"""
    try:
        progress_file = get_progress_file_path()
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Preparar datos para guardar (convertir Path objects a strings)
        save_data = {
            'current_batch': state['current_batch'],
            'processed_pdfs': [str(p) for p in state['processed_pdfs']],
            'pending_pdfs': [str(p) for p in state['pending_pdfs']],
            'batch_size': state['batch_size'],
            'user_decisions': state['user_decisions'],
            'last_updated': datetime.now().isoformat(),
            'total_processed': len(state['processed_pdfs'])
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
            
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar progreso: {e}")
        return False


def load_processing_progress():
    """Carga el progreso del procesamiento de PDFs desde archivo"""
    try:
        progress_file = get_progress_file_path()
        
        if not progress_file.exists():
            return None
            
        with open(progress_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convertir strings de vuelta a Path objects
        data['processed_pdfs'] = [Path(p) for p in data['processed_pdfs']]
        data['pending_pdfs'] = [Path(p) for p in data['pending_pdfs']]
        
        # Agregar campos que podrían faltar para compatibilidad
        if 'extracted_data' not in data:
            data['extracted_data'] = {}
        if 'user_decisions' not in data:
            data['user_decisions'] = {}
            
        return data
    except Exception as e:
        st.error(f"❌ Error al cargar progreso: {e}")
        return None


def validate_and_clean_progress(state, current_pdf_files):
    """Valida y limpia el progreso cargado basándose en los archivos actuales"""
    # Convertir a conjuntos de strings para comparación
    current_files_set = set(str(p) for p in current_pdf_files)
    current_mode = st.session_state.get('pdf_processing_mode', "➕ Agregar al grafo existente")
    
    # Limpiar registro de PDFs que ya no existen
    removed_from_registry = clean_processed_pdfs_registry()
    
    # Filtrar archivos que ya no existen
    valid_processed = [p for p in state['processed_pdfs'] if str(p) in current_files_set]
    valid_pending = [p for p in state['pending_pdfs'] if str(p) in current_files_set]
    
    # Verificar con el registro de PDFs procesados
    registry_processed = []
    for pdf_file in current_pdf_files:
        if is_pdf_already_processed(pdf_file, current_mode):
            registry_processed.append(pdf_file)
    
    # Combinar con los procesados del estado actual
    all_processed = set(str(p) for p in valid_processed + registry_processed)
    valid_processed = [Path(p) for p in all_processed if Path(p) in current_pdf_files]
    
    # Encontrar archivos nuevos (no procesados y no pendientes)
    processed_set = set(str(p) for p in valid_processed)
    pending_set = set(str(p) for p in valid_pending)
    existing_set = processed_set.union(pending_set)
    
    new_files = current_files_set - existing_set
    new_pending = [Path(f) for f in new_files]
    
    # Actualizar estado
    state['processed_pdfs'] = valid_processed
    state['pending_pdfs'] = valid_pending + new_pending
    
    # Limpiar batch si es necesario
    if state['current_batch'] * state['batch_size'] >= len(state['pending_pdfs']):
        state['current_batch'] = 0
    
    registry_info = f" (✅ {len(registry_processed)} desde registro)" if registry_processed else ""
    
    return len(new_files), len(valid_processed) + len(valid_pending) - len(current_pdf_files), registry_info


def clear_processing_progress():
    """Limpia el archivo de progreso de procesamiento"""
    try:
        progress_file = get_progress_file_path()
        if progress_file.exists():
            progress_file.unlink()
        return True
    except Exception as e:
        st.error(f"❌ Error al limpiar progreso: {e}")
        return False


def get_processed_pdfs_file_path():
    """Retorna la ruta del archivo que registra los PDFs procesados"""
    return Path("data/processed_pdfs_registry.json")


def save_processed_pdfs_registry(processed_pdfs_info):
    """Guarda el registro de PDFs procesados con información detallada"""
    try:
        registry_file = get_processed_pdfs_file_path()
        registry_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump(processed_pdfs_info, f, indent=2, ensure_ascii=False)
            
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar registro de PDFs: {e}")
        return False


def load_processed_pdfs_registry():
    """Carga el registro de PDFs procesados"""
    try:
        registry_file = get_processed_pdfs_file_path()
        
        if not registry_file.exists():
            return {}
            
        with open(registry_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"❌ Error al cargar registro de PDFs: {e}")
        return {}


def add_pdf_to_registry(pdf_path, title, authors, processing_mode):
    """Agrega un PDF al registro de procesados"""
    registry = load_processed_pdfs_registry()
    
    pdf_key = str(pdf_path)
    registry[pdf_key] = {
        'filename': Path(pdf_path).name,
        'full_path': pdf_key,
        'title': title,
        'authors': authors,
        'processing_mode': processing_mode,
        'processed_date': datetime.now().isoformat(),
        'file_size': Path(pdf_path).stat().st_size if Path(pdf_path).exists() else 0,
        'file_modified': datetime.fromtimestamp(Path(pdf_path).stat().st_mtime).isoformat() if Path(pdf_path).exists() else None
    }
    
    save_processed_pdfs_registry(registry)
    return registry


def is_pdf_already_processed(pdf_path, current_mode):
    """Verifica si un PDF ya ha sido procesado en el modo actual"""
    registry = load_processed_pdfs_registry()
    pdf_key = str(pdf_path)
    
    if pdf_key not in registry:
        return False
    
    pdf_info = registry[pdf_key]
    
    # Verificar si el archivo aún existe y no ha sido modificado
    if Path(pdf_path).exists():
        current_modified = datetime.fromtimestamp(Path(pdf_path).stat().st_mtime).isoformat()
        if pdf_info.get('file_modified') != current_modified:
            # El archivo ha sido modificado, considerarlo como no procesado
            return False
    else:
        # El archivo no existe, removerlo del registro
        del registry[pdf_key]
        save_processed_pdfs_registry(registry)
        return False
    
    # Verificar si fue procesado en el mismo modo
    return pdf_info.get('processing_mode') == current_mode


def clean_processed_pdfs_registry():
    """Limpia el registro de PDFs que ya no existen"""
    registry = load_processed_pdfs_registry()
    cleaned_registry = {}
    
    for pdf_path, info in registry.items():
        if Path(pdf_path).exists():
            cleaned_registry[pdf_path] = info
    
    save_processed_pdfs_registry(cleaned_registry)
    return len(registry) - len(cleaned_registry)  


def get_processed_pdfs_stats():
    """Obtiene estadísticas del registro de PDFs procesados"""
    registry = load_processed_pdfs_registry()
    
    stats = {
        'total_processed': len(registry),
        'by_mode': {},
        'recent_processed': []
    }
    
    # Contar por modo
    for info in registry.values():
        mode = info.get('processing_mode', 'unknown')
        if mode not in stats['by_mode']:
            stats['by_mode'][mode] = 0
        stats['by_mode'][mode] += 1
    
    # Obtener los 5 más recientes
    recent = sorted(registry.values(), 
                   key=lambda x: x.get('processed_date', ''), 
                   reverse=True)[:5]
    stats['recent_processed'] = recent
    
    return stats


def show_pdf_processor():
    """Muestra la página de procesamiento de PDFs"""
    st.markdown("## 📄 Procesador de PDFs Académicos")
    st.markdown("Extrae automáticamente autores y títulos de PDFs para agregar a tu red.")
    
    # Opción para elegir modo de procesamiento
    st.markdown("### 🎯 Modo de Procesamiento")
    mode_option = st.radio(
        "Elige cómo quieres procesar los PDFs:",
        [
            "➕ Agregar al grafo existente",
            "🆕 Crear grafo nuevo (solo PDFs)"
        ],
        help="Puedes agregar los PDFs al grafo actual o crear un grafo completamente nuevo solo con los datos de los PDFs."
    )
    
    # Guardar la opción en el estado de sesión
    if 'pdf_processing_mode' not in st.session_state:
        st.session_state.pdf_processing_mode = mode_option
    elif st.session_state.pdf_processing_mode != mode_option:
        st.session_state.pdf_processing_mode = mode_option
        # Limpiar estado del procesador si cambia el modo
        if 'pdf_processor_state' in st.session_state:
            del st.session_state.pdf_processor_state
        st.info("🔄 Modo cambiado. El progreso se reiniciará.")
        st.rerun()
    
    # Mostrar información del modo seleccionado
    if mode_option == "🆕 Crear grafo nuevo (solo PDFs)":
        st.info("🆕 **Modo: Grafo Nuevo** - Se creará un grafo completamente nuevo con solo los datos extraídos de los PDFs. El grafo actual no se modificará.")
    else:
        st.info("➕ **Modo: Agregar al Existente** - Los datos extraídos se agregarán al grafo actual.")
    
    st.markdown("---")
    
    # Verificar si hay PDFs para procesar
    pdf_directory = Path(r"c:\Users\Anabel\OneDrive\Desktop\ARC\pdfs_papers")
    
    if not pdf_directory.exists():
        st.error(f"❌ El directorio de PDFs no existe: {pdf_directory}")
        if st.button("📁 Crear directorio"):
            pdf_directory.mkdir(parents=True, exist_ok=True)
            st.success("✅ Directorio creado. Por favor, coloca tus PDFs ahí y recarga la página.")
        return
    
    pdf_files = list(pdf_directory.glob("*.pdf"))
    
    if not pdf_files:
        st.warning(f"⚠️ No se encontraron archivos PDF en: {pdf_directory}")
        st.info("💡 **Instrucciones:** Coloca los archivos PDF que quieres procesar en la carpeta `pdfs_papers` y recarga esta página.")
        
        if st.button("🔄 Buscar PDFs nuevamente"):
            st.rerun()
        return
    
    # Inicializar estado de sesión con persistencia
    if 'pdf_processor_state' not in st.session_state:
        # Intentar cargar progreso guardado
        loaded_state = load_processing_progress()
        
        if loaded_state:
            st.session_state.pdf_processor_state = loaded_state
            st.info("📂 Progreso previo cargado desde archivo.")
            
            # Validar y limpiar el progreso cargado
            new_files, removed_files, registry_info = validate_and_clean_progress(
                st.session_state.pdf_processor_state, 
                pdf_files
            )
            
            if new_files > 0:
                st.success(f"✅ {new_files} archivos nuevos detectados y agregados.")
            if removed_files < 0:  # Archivos eliminados
                st.warning(f"⚠️ {abs(removed_files)} archivos ya no están disponibles y fueron removidos del progreso.")
            if registry_info:
                st.info(f"📂 PDFs recuperados desde registro: {registry_info}")
        else:
            # Inicializar estado nuevo
            st.session_state.pdf_processor_state = {
                'current_batch': 0,
                'processed_pdfs': [],
                'pending_pdfs': list(pdf_files),
                'batch_size': 10,
                'extracted_data': {},
                'user_decisions': {}
            }
            st.info("🆕 Iniciando nuevo progreso de procesamiento.")
    
    state = st.session_state.pdf_processor_state
    
    # Verificar si hay PDFs nuevos
    current_pdf_files = set(str(p) for p in pdf_files)
    pending_pdf_files = set(str(p) for p in state['pending_pdfs'])
    processed_pdf_files = set(str(p) for p in state['processed_pdfs'])
    
    new_pdfs = current_pdf_files - pending_pdf_files - processed_pdf_files
    if new_pdfs:
        st.info(f"🆕 Se encontraron {len(new_pdfs)} PDFs nuevos!")
        if st.button("➕ Agregar PDFs nuevos a la cola"):
            state['pending_pdfs'].extend([Path(p) for p in new_pdfs])
            save_processing_progress(state)  # Guardar progreso
            st.success(f"✅ {len(new_pdfs)} PDFs agregados a la cola de procesamiento.")
            st.rerun()
    
    # Información general
    processing_mode = st.session_state.get('pdf_processing_mode', "➕ Agregar al grafo existente")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📁 PDFs Totales", len(pdf_files))
    with col2:
        st.metric("✅ Procesados", len(state['processed_pdfs']))
    with col3:
        st.metric("⏳ Pendientes", len(state['pending_pdfs']))
    with col4:
        if state['pending_pdfs']:
            batch_num = state['current_batch'] + 1
            total_batches = (len(state['pending_pdfs']) + state['batch_size'] - 1) // state['batch_size']
            st.metric("📋 Lote Actual", f"{batch_num}/{total_batches}")
        else:
            st.metric("📋 Estado", "Completo ✅")
    
    # Mostrar información del grafo objetivo
    if processing_mode == "🆕 Crear grafo nuevo (solo PDFs)":
        if 'pdf_only_graph' in st.session_state:
            pdf_graph = st.session_state.pdf_only_graph
            st.info(f"🆕 **Grafo de PDFs:** {pdf_graph.number_of_nodes()} nodos, {pdf_graph.number_of_edges()} conexiones")
        else:
            st.info("🆕 **Grafo de PDFs:** Vacío (se creará al procesar)")
    else:
        main_graph = st.session_state.graph
        st.info(f"➕ **Grafo Principal:** {main_graph.number_of_nodes()} nodos, {main_graph.number_of_edges()} conexiones")
    
    st.markdown("---")
    
    # Opciones de configuración
    with st.expander("⚙️ Configuración", expanded=False):
        new_batch_size = st.slider("PDFs por lote", min_value=5, max_value=20, value=state['batch_size'])
        if new_batch_size != state['batch_size']:
            state['batch_size'] = new_batch_size
            save_processing_progress(state)  # Guardar progreso
            st.success(f"✅ Tamaño de lote actualizado a {new_batch_size}")
        
        st.markdown("---")
        
        # Información y controles del progreso
        col1, col2 = st.columns(2)
        
        with col1:
            # Mostrar información del progreso guardado
            progress_file = get_progress_file_path()
            if progress_file.exists():
                try:
                    with progress_file.open('r', encoding='utf-8') as f:
                        progress_data = json.load(f)
                    st.success(f"💾 **Progreso guardado**")
                    st.write(f"📅 Última actualización: {progress_data.get('last_updated', 'Desconocido')}")
                    st.write(f"📊 Total procesados: {progress_data.get('total_processed', 0)}")
                except Exception as e:
                    st.error(f"❌ Error leyendo progreso: {e}")
            else:
                st.info("💾 No hay progreso guardado")
            
            # Mostrar estadísticas del registro de PDFs
            stats = get_processed_pdfs_stats()
            if stats['total_processed'] > 0:
                st.success(f"📂 **Registro de PDFs**")
                st.write(f"📁 Total registrados: {stats['total_processed']}")
                for mode, count in stats['by_mode'].items():
                    mode_emoji = "🆕" if "nuevo" in mode else "➕"
                    st.write(f"{mode_emoji} {mode}: {count}")
        
        with col2:
            # Botón para guardar progreso manualmente
            if st.button("💾 Guardar Progreso Ahora"):
                if save_processing_progress(state):
                    st.success("✅ Progreso guardado exitosamente")
                else:
                    st.error("❌ Error al guardar progreso")
            
            # Botón para limpiar progreso guardado
            if st.button("🗑️ Limpiar Progreso Guardado"):
                if clear_processing_progress():
                    st.success("✅ Progreso limpiado")
                else:
                    st.error("❌ Error al limpiar progreso")
            
            # Botón para limpiar registro de PDFs
            if st.button("🗑️ Limpiar Registro de PDFs"):
                registry_file = get_processed_pdfs_file_path()
                if registry_file.exists():
                    registry_file.unlink()
                    st.success("✅ Registro de PDFs limpiado")
                else:
                    st.info("💭 No hay registro que limpiar")
            
            # Botón para recrear grafo autor-autor (solo en modo PDFs)
            if processing_mode == "🆕 Crear grafo nuevo (solo PDFs)":
                if st.button("🤝 Recrear Grafo Autor-Autor"):
                    if 'pdf_only_graph' in st.session_state and st.session_state.pdf_only_graph.number_of_nodes() > 0:
                        author_graph = create_author_graph_from_pdf_graph(st.session_state.pdf_only_graph)
                        if save_pdf_author_graph(author_graph):
                            st.success(f"✅ Grafo autor-autor recreado: {author_graph.number_of_nodes()} autores, {author_graph.number_of_edges()} colaboraciones")
                        else:
                            st.error("❌ Error al guardar grafo autor-autor")
                    else:
                        st.warning("⚠️ No hay grafo de PDFs para procesar")
        
        st.markdown("---")
        
        # Botón para reiniciar completamente
        if st.button("🔄 Reiniciar Procesamiento Completo"):
            state['current_batch'] = 0
            state['processed_pdfs'] = []
            state['pending_pdfs'] = list(pdf_files)
            state['extracted_data'] = {}
            state['user_decisions'] = {}
            clear_processing_progress()  # Limpiar progreso guardado
            st.success("✅ Procesamiento reiniciado")
            st.rerun()
    
    # Procesar lote actual
    if state['pending_pdfs']:
        show_current_batch()
    else:
        st.success("🎉 ¡Todos los PDFs han sido procesados!")
        
        # Limpiar progreso guardado al completar todo
        clear_processing_progress()
        
        # Mostrar resumen final
        show_final_summary()
        
        # Botón para reiniciar el proceso
        if st.button("🔄 Procesar PDFs Nuevamente", type="primary"):
            state['current_batch'] = 0
            state['processed_pdfs'] = []
            state['pending_pdfs'] = list(pdf_files)
            state['extracted_data'] = {}
            state['user_decisions'] = {}
            clear_processing_progress()  # Limpiar progreso guardado
            st.rerun()


def show_current_batch():
    """Muestra el lote actual de PDFs para revisión"""
    state = st.session_state.pdf_processor_state
    
    # Calcular el lote actual
    start_idx = state['current_batch'] * state['batch_size']
    end_idx = min(start_idx + state['batch_size'], len(state['pending_pdfs']))
    current_batch = state['pending_pdfs'][start_idx:end_idx]
    
    if not current_batch:
        return
    
    st.markdown(f"### 📋 Lote {state['current_batch'] + 1} ({len(current_batch)} PDFs)")
    
    # Extraer datos si no se ha hecho
    batch_key = f"batch_{state['current_batch']}"
    if batch_key not in state['extracted_data']:
        extract_batch_data(current_batch, batch_key)
    
    # Mostrar resultados del lote
    if batch_key in state['extracted_data']:
        show_batch_results(current_batch, batch_key)


def extract_batch_data(pdf_files, batch_key):
    """Extrae datos del lote actual de PDFs"""
    state = st.session_state.pdf_processor_state
    
    with st.spinner(f"🔄 Procesando {len(pdf_files)} PDFs..."):
        try:
            extractor = ImprovedAcademicExtractor()
        except Exception as e:
            st.error(f"❌ Error al inicializar el extractor: {e}")
            return
        
        batch_results = {}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, pdf_path in enumerate(pdf_files):
            status_text.text(f"Procesando: {pdf_path.name} ({i+1}/{len(pdf_files)})")
            
            try:
                result = process_pdf_improved(str(pdf_path))
                
                # Extraer título del PDF si es posible
                title = extract_title_from_result(result, pdf_path.name)
                
                # Validar que los datos extraídos sean válidos
                persons = result.get('persons_found', [])
                if persons:
                    # Filtrar nombres muy cortos o inválidos
                    persons = [p for p in persons if len(p.strip()) > 2 and ' ' in p.strip()]
                
                batch_results[str(pdf_path)] = {
                    'filename': pdf_path.name,
                    'title': title,
                    'persons': persons,
                    'text_preview': result.get('text_before_abstract', '')[:500] + "..." if result.get('text_before_abstract') else "Sin texto extraído",
                    'error': result.get('error', None),
                    'success': 'error' not in result
                }
                
            except Exception as e:
                batch_results[str(pdf_path)] = {
                    'filename': pdf_path.name,
                    'title': pdf_path.stem,
                    'persons': [],
                    'text_preview': '',
                    'error': f"Error al procesar el archivo: {str(e)}",
                    'success': False
                }
                
                # Log del error para debugging
                st.write(f"⚠️ Error procesando {pdf_path.name}: {e}")
            
            progress_bar.progress((i + 1) / len(pdf_files))
        
        state['extracted_data'][batch_key] = batch_results
        progress_bar.empty()
        status_text.empty()
        
        # Mostrar resumen del lote
        successful = sum(1 for r in batch_results.values() if r['success'])
        failed = len(batch_results) - successful
        
        if failed > 0:
            st.warning(f"⚠️ {failed} de {len(pdf_files)} PDFs tuvieron errores al procesarse.")
        
        st.success(f"✅ Extracción completada: {successful} PDFs procesados exitosamente.")


def extract_title_from_result(result, filename):
    """Intenta extraer el título del resultado del PDF"""
    if 'error' in result:
        return filename.replace('.pdf', '')
    
    text = result.get('text_before_abstract', '')
    lines = text.split('\n')
    
    # Buscar líneas que podrían ser títulos
    for line in lines[:10]:  # Solo las primeras 10 líneas
        line = line.strip()
        if len(line) > 10 and len(line) < 200:  # Longitud razonable para un título
            # Filtrar líneas que obviamente no son títulos
            if not any(word in line.lower() for word in ['abstract', 'resumen', 'universidad', 'department']):
                return line
    
    # Si no se encuentra, usar el nombre del archivo
    return filename.replace('.pdf', '')


def show_batch_results(pdf_files, batch_key):
    """Muestra los resultados del lote para revisión del usuario"""
    state = st.session_state.pdf_processor_state
    batch_data = state['extracted_data'][batch_key]
    
    st.markdown("#### 🔍 Revisa los datos extraídos:")
    
    # Formulario para el lote completo
    with st.form(f"batch_form_{batch_key}"):
        decisions = {}
        
        for pdf_path in pdf_files:
            pdf_data = batch_data[str(pdf_path)]
            
            # Verificar si el PDF ya fue procesado según el registro
            current_mode = st.session_state.get('pdf_processing_mode', "➕ Agregar al grafo existente")
            if is_pdf_already_processed(pdf_path, current_mode):
                st.info(f"📂 **{pdf_data['filename']}** - Este PDF ya fue procesado anteriormente en este modo, se omitirá.")
                decisions[str(pdf_path)] = {'action': 'skip', 'reason': 'already_processed'}
                continue
            
            # Verificar si el artículo ya existe en el grafo
            article_exists = check_article_exists(pdf_data['title'])
            
            if article_exists:
                st.info(f"⏭️ **{pdf_data['filename']}** - El artículo ya existe en el grafo, se omitirá.")
                decisions[str(pdf_path)] = {'action': 'skip', 'reason': 'exists'}
                continue
            
            with st.expander(f"📄 {pdf_data['filename']}", expanded=True):
                if pdf_data['error']:
                    st.error(f"❌ Error al procesar: {pdf_data['error']}")
                    decisions[str(pdf_path)] = {'action': 'skip', 'reason': 'error'}
                    continue
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Título editable
                    edited_title = st.text_input(
                        "Título del artículo:",
                        value=pdf_data['title'],
                        key=f"title_{pdf_path}_{batch_key}"
                    )
                    
                    # Vista previa del texto
                    st.text_area(
                        "Vista previa del texto:",
                        value=pdf_data['text_preview'],
                        height=100,
                        disabled=True,
                        key=f"preview_{pdf_path}_{batch_key}"
                    )
                
                with col2:
                    # Decisión del usuario
                    action = st.radio(
                        "Acción:",
                        ["✅ Procesar", "❌ Omitir"],
                        key=f"action_{pdf_path}_{batch_key}"
                    )
                    
                    # Información adicional
                    st.write(f"**Autores encontrados:** {len(pdf_data['persons'])}")
                
                # Autores encontrados (editables)
                if pdf_data['persons']:
                    st.write("👥 **Autores detectados:**")
                    selected_authors = []
                    
                    for i, person in enumerate(pdf_data['persons']):
                        col_check, col_name = st.columns([1, 4])
                        
                        with col_check:
                            include = st.checkbox(
                                "✓",
                                value=True,
                                key=f"author_check_{pdf_path}_{i}_{batch_key}"
                            )
                        
                        with col_name:
                            edited_name = st.text_input(
                                f"Autor {i+1}:",
                                value=person,
                                key=f"author_name_{pdf_path}_{i}_{batch_key}"
                            )
                        
                        if include and edited_name.strip():
                            selected_authors.append(edited_name.strip())
                    
                    decisions[str(pdf_path)] = {
                        'action': 'process' if action == "✅ Procesar" else 'skip',
                        'title': edited_title,
                        'authors': selected_authors,
                        'filename': pdf_data['filename']
                    }
                
                else:
                    st.warning("⚠️ No se encontraron autores en este PDF")
                    decisions[str(pdf_path)] = {
                        'action': 'skip',
                        'reason': 'no_authors',
                        'title': edited_title,
                        'filename': pdf_data['filename']
                    }
        
        # Botones de acción
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submitted = st.form_submit_button("✅ Confirmar Lote", type="primary", use_container_width=True)
        
        with col2:
            skip_batch = st.form_submit_button("⏭️ Omitir Lote", use_container_width=True)
        
        with col3:
            cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)
        
        if submitted:
            process_batch_decisions(decisions, pdf_files, batch_key)
        elif skip_batch:
            skip_current_batch(pdf_files)
        elif cancel:
            st.info("❌ Procesamiento cancelado")


def check_article_exists(title):
    """Verifica si un artículo ya existe en el grafo"""
    processing_mode = st.session_state.get('pdf_processing_mode', "➕ Agregar al grafo existente")
    
    # Determinar qué grafo verificar según el modo
    if processing_mode == "🆕 Crear grafo nuevo (solo PDFs)":
        if 'pdf_only_graph' not in st.session_state:
            st.session_state.pdf_only_graph = load_pdf_only_graph()
        graph = st.session_state.pdf_only_graph
    else:
        graph = st.session_state.graph
    
    # Normalizar título para comparación
    normalized_title = title.lower().strip()
    
    # Buscar por título exacto o similar
    for node, data in graph.nodes(data=True):
        if data.get('node_type') == 'article':
            existing_title = data.get('title', data.get('display_name', ''))
            normalized_existing = existing_title.lower().strip()
            
            # Comparación exacta
            if normalized_existing == normalized_title:
                return True
            
            # Comparación de similitud (palabras en común)
            title_words = set(normalized_title.split())
            existing_words = set(normalized_existing.split())
            
            # Si tienen más del 80% de palabras en común, considerarlo duplicado
            if len(title_words) > 0 and len(existing_words) > 0:
                common_words = title_words.intersection(existing_words)
                similarity = len(common_words) / max(len(title_words), len(existing_words))
                
                if similarity > 0.8:
                    return True
    
    return False


def process_batch_decisions(decisions, pdf_files, batch_key):
    """Procesa las decisiones del usuario para el lote actual"""
    state = st.session_state.pdf_processor_state
    processing_mode = st.session_state.get('pdf_processing_mode', "➕ Agregar al grafo existente")
    
    # Determinar qué grafo usar según el modo
    if processing_mode == "🆕 Crear grafo nuevo (solo PDFs)":
        # Verificar si ya existe un grafo de solo PDFs en el estado
        if 'pdf_only_graph' not in st.session_state:
            st.session_state.pdf_only_graph = nx.Graph()
        graph = st.session_state.pdf_only_graph
        graph_name = "grafo de PDFs"
    else:
        graph = st.session_state.graph
        graph_name = "grafo principal"
    
    added_articles = 0
    added_authors = 0
    
    with st.spinner(f"🔄 Agregando artículos y autores al {graph_name}..."):
        
        for pdf_path_str, decision in decisions.items():
            if decision['action'] == 'process':
                # Agregar artículo
                article_id = f"article_{decision['title'].replace(' ', '_').lower()}"
                # Verificar si el autor ya existe
                article_exists = False
                for node, data in graph.nodes(data=True):
                    if (data.get('node_type') == 'article' and 
                            data.get('title', '').lower() == decision['title'].lower()):
                            article_id = node
                            article_exists = True
                            break
                if  article_exists:
                    article_data = {
                        'node_type': 'article',
                        'title': decision['title'],
                        'display_name': decision['title'],
                        'source_file': decision['filename'],
                        'added_via_pdf': True,
                        'created_date': datetime.now().isoformat()
                    }
                    
                    graph.add_node(article_id, **article_data)
                    added_articles += 1
                
                # Agregar autores y conexiones
                for author_name in decision['authors']:
                    author_id = f"author_{author_name.replace(' ', '_').lower()}"
                    
                    # Verificar si el autor ya existe
                    author_exists = False
                    for node, data in graph.nodes(data=True):
                        if (data.get('node_type') == 'author' and 
                            data.get('display_name', '').lower() == author_name.lower()):
                            author_id = node
                            author_exists = True
                            break
                    
                    # Agregar autor si no existe
                    if not author_exists:
                        author_data = {
                            'node_type': 'author',
                            'display_name': author_name,
                            'first_name': author_name.split()[0] if author_name.split() else '',
                            'last_name': ' '.join(author_name.split()[1:]) if len(author_name.split()) > 1 else '',
                            'added_via_pdf': True,
                            'created_date': datetime.now().isoformat()
                        }
                        
                        graph.add_node(author_id, **author_data)
                        added_authors += 1
                    
                    # Agregar conexión autor-artículo
                    if not graph.has_edge(author_id, article_id):
                        graph.add_edge(author_id, article_id, relationship='authored')
    
    # Guardar el grafo actualizado
    if processing_mode == "🆕 Crear grafo nuevo (solo PDFs)":
        # Guardar el grafo de PDFs por separado
        save_pdf_only_graph(graph)
        st.info(f"💾 Grafo de PDFs guardado con {graph.number_of_nodes()} nodos y {graph.number_of_edges()} conexiones.")
    else:
        # Guardar el grafo principal
        save_graph(graph)
        clear_centralities_cache()
    
    # Actualizar estado y registrar PDFs procesados
    processed_in_batch = []
    for pdf_path_str, decision in decisions.items():
        if decision['action'] == 'process':
            # Registrar el PDF como procesado
            add_pdf_to_registry(
                pdf_path_str, 
                decision['title'], 
                decision['authors'], 
                processing_mode
            )
            processed_in_batch.append(pdf_path_str)
    
    state['processed_pdfs'].extend(pdf_files)
    for pdf_path in pdf_files:
        if pdf_path in state['pending_pdfs']:
            state['pending_pdfs'].remove(pdf_path)
    
    # Guardar progreso después de procesar el lote
    save_processing_progress(state)
    
    state['current_batch'] += 1
    
    # Guardar progreso con el nuevo batch
    save_processing_progress(state)
    
    # Mostrar resumen
    st.success(f"✅ Lote procesado exitosamente en el {graph_name}!")
    st.info(f"📊 **Resumen:** {added_articles} artículos y {added_authors} autores agregados.")
    
    if processed_in_batch:
        st.info(f"📂 **Registro:** {len(processed_in_batch)} PDFs registrados como procesados.")
    
    # Limpiar datos del lote para liberar memoria
    if batch_key in state['extracted_data']:
        del state['extracted_data'][batch_key]
    
    # Registrar los PDFs procesados en el registro
    for pdf_path in pdf_files:
        pdf_key = str(pdf_path)
        if not is_pdf_already_processed(pdf_path, processing_mode):
            # Agregar al registro solo si no está ya procesado
            add_pdf_to_registry(pdf_path, "", [], processing_mode)
    
    st.rerun()


def skip_current_batch(pdf_files):
    """Omite el lote actual"""
    state = st.session_state.pdf_processor_state
    
    state['processed_pdfs'].extend(pdf_files)
    for pdf_path in pdf_files:
        if pdf_path in state['pending_pdfs']:
            state['pending_pdfs'].remove(pdf_path)
    
    state['current_batch'] += 1
    
    # Guardar progreso después de omitir el lote
    save_processing_progress(state)
    
    st.info(f"⏭️ Lote omitido. Continuando con el siguiente lote...")
    st.rerun()


def show_final_summary():
    """Muestra un resumen final del procesamiento"""
    st.markdown("### 📊 Resumen Final del Procesamiento")
    
    state = st.session_state.pdf_processor_state
    processing_mode = st.session_state.get('pdf_processing_mode', "➕ Agregar al grafo existente")
    
    # Determinar qué grafo mostrar según el modo
    if processing_mode == "🆕 Crear grafo nuevo (solo PDFs)":
        graph = st.session_state.get('pdf_only_graph', nx.Graph())
        mode_info = "🆕 **Grafo Nuevo de PDFs** - Datos extraídos en un grafo independiente"
    else:
        graph = st.session_state.graph
        mode_info = "➕ **Grafo Existente** - Datos agregados al grafo principal"
    
    st.info(mode_info)
    
    # Contar elementos agregados via PDF
    articles_from_pdf = len([n for n, d in graph.nodes(data=True) 
                           if d.get('node_type') == 'article' and d.get('added_via_pdf', False)])
    
    authors_from_pdf = len([n for n, d in graph.nodes(data=True) 
                          if d.get('node_type') == 'author' and d.get('added_via_pdf', False)])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 Artículos Agregados", articles_from_pdf)
    with col2:
        st.metric("👥 Autores Agregados", authors_from_pdf)
    with col3:
        st.metric("📁 PDFs Procesados", len(state['processed_pdfs']))
    with col4:
        st.metric("🔗 Total Nodos", graph.number_of_nodes())
    
    # Mostrar opciones específicas del modo
    if processing_mode == "🆕 Crear grafo nuevo (solo PDFs)":
        st.markdown("#### 🎯 Opciones del Grafo de PDFs")
        
        # Verificar si existe el grafo autor-autor
        pdf_author_graph = st.session_state.get('pdf_author_graph', load_pdf_author_graph())
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📁 Exportar Grafo de PDFs", type="secondary"):
                graph_path = Path("data/grafo_solo_pdfs.graphml")
                if graph_path.exists():
                    st.success(f"✅ Grafo exportado como: {graph_path}")
                    st.info("📂 El archivo se puede abrir con herramientas como Gephi, Cytoscape, etc.")
                else:
                    st.error("❌ No se encontró el archivo del grafo")
        
        with col2:
            if st.button("🔄 Usar este Grafo como Principal"):
                st.session_state.graph = graph
                # También actualizar el grafo autor-autor principal si existe
                if pdf_author_graph.number_of_nodes() > 0:
                    st.session_state.author_graph = pdf_author_graph
                save_graph(graph)
                st.success("✅ El grafo de PDFs ahora es el grafo principal de la aplicación")
                st.rerun()
        
        with col3:
            if pdf_author_graph.number_of_nodes() > 0:
                if st.button("📊 Ver Red de Colaboración"):
                    st.info(f"🤝 Red autor-autor: {pdf_author_graph.number_of_nodes()} autores, {pdf_author_graph.number_of_edges()} colaboraciones")
                    # Aquí podrías agregar visualización si quieres
            else:
                st.info("🤝 No hay colaboraciones suficientes para mostrar")
    
    # Mostrar estadísticas adicionales para modo PDFs
    if processing_mode == "🆕 Crear grafo nuevo (solo PDFs)" and graph.number_of_nodes() > 0:
        with st.expander("🤝 Estadísticas de Colaboración (PDFs)"):
            pdf_author_graph = st.session_state.get('pdf_author_graph', load_pdf_author_graph())
            if pdf_author_graph.number_of_nodes() > 0:
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Autores que colaboran:** {pdf_author_graph.number_of_nodes()}")
                    st.write(f"**Colaboraciones totales:** {pdf_author_graph.number_of_edges()}")
                with col2:
                    if pdf_author_graph.number_of_nodes() > 1:
                        density = nx.density(pdf_author_graph)
                        st.write(f"**Densidad de colaboración:** {density:.3f}")
                        
                        # Encontrar el autor más colaborativo
                        if pdf_author_graph.number_of_edges() > 0:
                            degrees = dict(pdf_author_graph.degree())
                            most_collaborative = max(degrees, key=degrees.get)
                            st.write(f"**Autor más colaborativo:** {most_collaborative} ({degrees[most_collaborative]} colaboraciones)")
            else:
                st.info("No hay suficientes datos para mostrar estadísticas de colaboración")
    
    # Mostrar lista de artículos agregados
    if articles_from_pdf > 0:
        with st.expander("📋 Ver artículos agregados desde PDFs"):
            for node, data in graph.nodes(data=True):
                if (data.get('node_type') == 'article' and 
                    data.get('added_via_pdf', False)):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{data.get('title', 'Sin título')}**")
                    with col2:
                        st.write(f"📁 {data.get('source_file', 'Desconocido')}")
    
    # Mostrar historial de PDFs procesados
    stats = get_processed_pdfs_stats()
    if stats['total_processed'] > 0:
        with st.expander("📂 Historial de PDFs Procesados"):
            st.write(f"**Total de PDFs registrados:** {stats['total_processed']}")
            
            if stats['recent_processed']:
                st.write("**Procesados recientemente:**")
                for pdf_info in stats['recent_processed']:
                    processed_date = datetime.fromisoformat(pdf_info['processed_date']).strftime("%Y-%m-%d %H:%M")
                    mode_emoji = "🆕" if "nuevo" in pdf_info.get('processing_mode', '') else "➕"
                    st.write(f"{mode_emoji} **{pdf_info['filename']}** - {processed_date}")
                    st.write(f"   📄 *{pdf_info.get('title', 'Sin título')}*")
                    if pdf_info.get('authors'):
                        authors_text = ", ".join(pdf_info['authors'][:3])
                        if len(pdf_info['authors']) > 3:
                            authors_text += f" y {len(pdf_info['authors']) - 3} más"
                        st.write(f"   👥 {authors_text}")
    
    # Mostrar estadísticas del grafo
    if graph.number_of_nodes() > 0:
        with st.expander("📈 Estadísticas del Grafo"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Total de nodos:** {graph.number_of_nodes()}")
                st.write(f"**Total de conexiones:** {graph.number_of_edges()}")
            with col2:
                article_nodes = len([n for n, d in graph.nodes(data=True) if d.get('node_type') == 'article'])
                author_nodes = len([n for n, d in graph.nodes(data=True) if d.get('node_type') == 'author'])
                st.write(f"**Artículos:** {article_nodes}")
                st.write(f"**Autores:** {author_nodes}")


def save_pdf_only_graph(graph):
    """Guarda el grafo que contiene solo datos de PDFs"""
    try:
        # Guardar como archivo GraphML para compatibilidad
        graph_path = Path("data/grafo_solo_pdfs.graphml")
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        
        nx.write_graphml(graph, graph_path)
        
        # También guardarlo en session_state para persistencia
        st.session_state.pdf_only_graph = graph
        
        # Crear y guardar automáticamente el grafo autor-autor
        if graph.number_of_nodes() > 0:
            author_graph = create_author_graph_from_pdf_graph(graph)
            if author_graph.number_of_nodes() > 0:
                save_pdf_author_graph(author_graph)
                st.info(f"🤝 Grafo autor-autor creado automáticamente con {author_graph.number_of_nodes()} autores y {author_graph.number_of_edges()} colaboraciones.")
        
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar grafo de PDFs: {e}")
        return False


def load_pdf_only_graph():
    """Carga el grafo de solo PDFs si existe"""
    try:
        graph_path = Path("data/grafo_solo_pdfs.graphml")
        if graph_path.exists():
            return nx.read_graphml(graph_path)
        else:
            return nx.Graph()
    except Exception as e:
        st.error(f"❌ Error al cargar grafo de PDFs: {e}")
        return nx.Graph()


def create_author_graph_from_pdf_graph(pdf_graph):
    """Crea un grafo autor-autor a partir del grafo de PDFs"""
    try:
        # Crear proyección autor-autor directamente
        author_graph = nx.Graph()
        
        # Obtener todos los autores
        authors = [n for n, d in pdf_graph.nodes(data=True) if d.get('node_type') == 'author']
        
        # Agregar nodos de autores con sus datos
        for author in authors:
            author_data = pdf_graph.nodes[author]
            author_graph.add_node(author, **author_data)

        # Crear conexiones basadas en artículos compartidos
        for article_node in pdf_graph.nodes():
            article_data = pdf_graph.nodes[article_node]
            if article_data.get('node_type') == 'article':
                # Encontrar todos los autores conectados a este artículo
                article_authors = [n for n in pdf_graph.neighbors(article_node) 
                                 if pdf_graph.nodes[n].get('node_type') == 'author']
                
                # Crear conexiones entre cada par de autores
                for i, author1 in enumerate(article_authors):
                    for author2 in article_authors[i+1:]:
                        if not author_graph.has_edge(author1, author2):
                            author_graph.add_edge(author1, author2, weight=1, shared_articles=[article_node])
                        else:
                            # Incrementar peso y agregar artículo compartido
                            author_graph[author1][author2]['weight'] += 1
                            author_graph[author1][author2]['shared_articles'].append(article_node)
        
        return author_graph
    except Exception as e:
        st.error(f"❌ Error al crear grafo autor-autor: {e}")
        return nx.Graph()


def save_pdf_author_graph(author_graph):
    """Guarda el grafo autor-autor creado desde PDFs"""
    try:
        graph_path = Path("data/grafo_autor_autor_pdfs.graphml")
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        
        nx.write_graphml(author_graph, graph_path)
        
        # También guardarlo en session_state
        st.session_state.pdf_author_graph = author_graph
        
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar grafo autor-autor de PDFs: {e}")
        return False


def load_pdf_author_graph():
    """Carga el grafo autor-autor de PDFs si existe"""
    try:
        graph_path = Path("data/grafo_autor_autor_pdfs.graphml")
        if graph_path.exists():
            return nx.read_graphml(graph_path)
        else:
            return nx.Graph()
    except Exception as e:
        st.error(f"❌ Error al cargar grafo autor-autor de PDFs: {e}")
        return nx.Graph()
