import streamlit as st
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import os
from src.utils import load_author_graph, load_keyword_graph, save_graph_state, calculate_author_metrics, calculate_keyword_metrics,calculate_advanced_author_metrics
from src.authors import render_authors_page
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
    
    
    keyword_metrics = calculate_keyword_metrics(keyword_graph)
    if 'author_analytics' not in st.session_state:
        st.session_state.author_analytics = calculate_advanced_author_metrics(author_graph)
    
    st.title("Análisis de la red científica de la UH", anchor=False)

    with st.container(border=True):
        tab1, tab3= st.tabs(["Autores",'Articulos'])
        with tab1:
            st.header("Análisis de Autores", anchor=False, divider='gray')
            render_authors_page(author_analytics=st.session_state.author_analytics,keyword_graph=keyword_graph)

        with tab3:
            render_papers_page(author_graph,keyword_graph)
           

if __name__ == "__main__":
    main()