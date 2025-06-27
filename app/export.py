
import streamlit as st
import pandas as pd
from app.utils import save_graph

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
    
    
    st.markdown("### 💾 Guardar Grafo")
        
    filename = st.text_input("Nombre del archivo:", value="subgrafo_con_articulos_editado.graphml")
        
    if st.button("💾 Guardar GraphML", type="primary", use_container_width=True):
            if save_graph(st.session_state.graph, filename):
                st.success(f"✅ Grafo guardado como '{filename}'")
            else:
                st.error("❌ Error al guardar el grafo")
