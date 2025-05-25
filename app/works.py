import streamlit as st
import pandas as pd


def buscar_trabajos(conn):
    """Buscar trabajos por título"""
    st.header("📄 Buscar Trabajos")

    with st.container():
        titulo = st.text_input(
            "Ingrese parte del título del trabajo:", placeholder="Ej: Machine Learning"
        )

        if st.button("Buscar Trabajos") or titulo:
            if titulo:
                with st.spinner("Buscando trabajos..."):
                    query = """
                    MATCH (w:Work)
                    WHERE toLower(w.title) CONTAINS toLower($titulo)
                    RETURN w.id AS id, w.title AS título, w.publication_year AS año,
                           w.cited_by_count AS citaciones
                    ORDER BY w.publication_year DESC
                    LIMIT 50
                    """

                    results = conn.query_to_dataframe(query, {"titulo": titulo})

                    if not results.empty:
                        st.success(f"Se encontraron {len(results)} trabajos.")
                        st.dataframe(results, use_container_width=True)
                    else:
                        st.warning(
                            f"No se encontraron trabajos con el título '{titulo}'."
                        )
            else:
                st.info("Por favor, ingrese un título para buscar.")
