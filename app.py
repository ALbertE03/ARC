import streamlit as st
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import os
from src.utils import load_author_graph, load_keyword_graph, save_graph_state, calculate_author_metrics, calculate_keyword_metrics,calculate_advanced_author_metrics
from src.authors import render_authors_page
from src.topics import render_topic_page
from src.papers import render_papers_page
def main():
   
    PATH_TO_AUTHOR_GRAPH = './graph/author_collaboration_graph.graphml'
    PATH_TO_KEYWORD_GRAPH = './graph/keywords_graph.graphml'

    if 'graphs_loaded' not in st.session_state:
        author_graph = load_author_graph(PATH_TO_AUTHOR_GRAPH)
        keyword_graph = load_keyword_graph(PATH_TO_KEYWORD_GRAPH)
        if author_graph is None or keyword_graph is None:
            st.error("Error crítico: No se pudieron cargar los archivos de grafos. Asegúrate de que las rutas son correctas y los archivos no están corruptos.")
            st.stop()
        save_graph_state(author_graph, keyword_graph)
        st.session_state['graphs_loaded'] = True
    
    author_graph = st.session_state['author_graph']
    keyword_graph = st.session_state['keyword_graph']
    
    author_metrics = calculate_author_metrics(author_graph)
    keyword_metrics = calculate_keyword_metrics(keyword_graph)
    if 'author_analytics' not in st.session_state:
        st.session_state.author_analytics = calculate_advanced_author_metrics(author_graph)
    
    st.title("🔬 Dashboard de Inteligencia en Investigación", anchor=False)
    st.markdown("Análisis de la red de colaboración y producción científica de la institución.")

    with st.container(border=True):
        tab1, tab2, tab3,tab4= st.tabs(["Autores", "Temas",'Articulos', "Co-ocurrencia"])
        with tab1:
            st.header("Análisis de Autores", anchor=False, divider='gray')
            render_authors_page(author_analytics=st.session_state.author_analytics,keyword_graph=keyword_graph)
        with tab2:
            st.header("Análisis de Temas de Investigación", anchor=False, divider='gray')
            render_topic_page(keyword_metrics)
        with tab3:
            render_papers_page()
           
        with tab4:
            st.header("Análisis Individual y de Co-ocurrencia", anchor=False, divider='gray')

            with st.expander("**🧑‍🔬 Perfil de Investigador**"):
                author_names = sorted([data['name'] for _, data in author_graph.nodes(data=True)])
                selected_author = st.selectbox("Selecciona un autor para ver su perfil detallado:", options=author_names, index=None, placeholder="Escribe o selecciona un nombre...")
                if selected_author:
                    author_id = [node for node, data in author_graph.nodes(data=True) if data['name'] == selected_author][0]
                    author_data = author_graph.nodes[author_id]
                    
                    st.subheader(f"Perfil de {selected_author}", divider='gray')
                    st.markdown(f"**Nº de Artículos:** {author_data.get('paper_count', 0)}")
                    collaborators = list(author_graph.neighbors(author_id))
                    st.markdown(f"**Nº de Colaboradores:** {len(collaborators)}")
                    
                    collaborator_names = [author_graph.nodes[nid]['name'] for nid in collaborators]
                    st.write("**Colaboradores:**")
                    st.text(', '.join(collaborator_names))

            with st.expander("**🔄 Co-ocurrencia de Temas**"):
                all_keywords = sorted([node for node, data in keyword_graph.nodes(data=True) if data.get('type') == 'keyword'])
                selected_keyword = st.selectbox("Selecciona un tema para ver sus temas relacionados:", options=all_keywords, index=None, placeholder="Escribe o selecciona un tema...")
                if selected_keyword:
                    related_keywords = []
                    for neighbor in keyword_graph.neighbors(selected_keyword):
                        if keyword_graph.nodes[neighbor].get('type') == 'keyword':
                            weight = keyword_graph.get_edge_data(selected_keyword, neighbor).get('weight', 0)
                            related_keywords.append({'Tema Relacionado': neighbor, 'Fuerza de Co-ocurrencia': weight})
                    
                    if related_keywords:
                        df_related = pd.DataFrame(related_keywords).sort_values(by='Fuerza de Co-ocurrencia', ascending=False)
                        st.dataframe(df_related, use_container_width=True, hide_index=True)
                    else:
                        st.info("Este tema no tiene co-ocurrencias registradas.")


if __name__ == "__main__":
    main()