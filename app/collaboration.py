import streamlit as st
import pandas as pd


def analisis_red_colaboracion(conn):
    """Analizar redes de colaboración entre autores"""
    st.header("🌐 Análisis de Red de Colaboración")

    # Opciones para filtrar el análisis
    with st.expander("Opciones de Análisis", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            min_colaboraciones = st.number_input(
                "Mínimo de colaboraciones", min_value=1, value=2
            )
        with col2:
            año_inicio = st.number_input(
                "Año inicial", min_value=2000, max_value=2025, value=2015
            )
        with col3:
            limite_resultados = st.number_input(
                "Límite de resultados", min_value=10, max_value=500, value=100
            )

    tab1, tab2 = st.tabs(["Colaboraciones Directas", "Comunidades de Investigación"])

    with tab1:
        st.subheader("🔗 Colaboraciones Directas")
        st.markdown(
            "Este análisis muestra cómo los autores están conectados entre sí a través de colaboraciones en trabajos académicos."
        )

        with st.spinner("Analizando red de colaboración..."):
            query = """
            MATCH (a1:Author)-[:AUTHORED]->(w:Work)<-[:AUTHORED]-(a2:Author)
            WHERE a1 <> a2
            AND w.publication_year >= $año_inicio
            WITH a1, a2, count(w) AS trabajos_juntos
            WHERE trabajos_juntos >= $min_colaboraciones
            RETURN a1.display_name AS autor1, a2.display_name AS autor2, trabajos_juntos
            ORDER BY trabajos_juntos DESC
            LIMIT $limite
            """
            params = {
                "min_colaboraciones": min_colaboraciones,
                "año_inicio": año_inicio,
                "limite": limite_resultados,
            }
            red_df = conn.query_to_dataframe(query, params)

            if not red_df.empty:
                st.success(f"Se encontraron {len(red_df)} conexiones de colaboración.")
                st.dataframe(red_df, use_container_width=True)

                st.subheader("Distribución de Intensidad de Colaboraciones")
                distribucion = red_df["trabajos_juntos"].value_counts().sort_index()
                st.bar_chart(distribucion)
            else:
                st.warning("No se encontraron datos de colaboración con estos filtros.")

    with tab2:
        st.subheader("👥 Comunidades de Investigación")
        st.markdown(
            "Identificación de grupos de investigación basados en patrones de colaboración frecuente."
        )

        with st.spinner("Identificando comunidades de investigación..."):
            # Consulta para encontrar comunidades (autores que colaboran frecuentemente)
            query = """
            MATCH (a1:Author)-[:AUTHORED]->(w:Work)<-[:AUTHORED]-(a2:Author)
            WHERE a1 <> a2 AND w.publication_year >= $año_inicio
            WITH a1, collect(DISTINCT a2.display_name) AS colaboradores,
                 count(DISTINCT a2) AS num_colaboradores
            WHERE num_colaboradores >= 2
            RETURN 
                a1.display_name AS autor_central,
                num_colaboradores AS tamaño_red,
                colaboradores[0..10] AS miembros_principales
            ORDER BY tamaño_red DESC
            LIMIT $limite
            """

            comunidades_df = conn.query_to_dataframe(query, params)

            if not comunidades_df.empty:
                st.success(
                    f"Se identificaron {len(comunidades_df)} posibles comunidades de investigación."
                )

                # Simplificamos la visualización para Streamlit
                comunidades_viz = comunidades_df[["autor_central", "tamaño_red"]].copy()
                st.dataframe(comunidades_viz, use_container_width=True)

                # Mostramos detalles de algunas comunidades
                st.subheader("Detalles de Comunidades Principales")
                for i, row in comunidades_df.head(5).iterrows():
                    with st.expander(
                        f"Comunidad de {row['autor_central']} ({row['tamaño_red']} colaboradores)"
                    ):
                        st.markdown(f"**Investigador central:** {row['autor_central']}")
                        st.markdown(
                            f"**Tamaño de red:** {row['tamaño_red']} colaboradores"
                        )
                        st.markdown("**Miembros principales:**")
                        st.write(row["miembros_principales"])
            else:
                st.warning(
                    "No se identificaron comunidades de investigación con estos criterios."
                )

            # Análisis de temas comunes en comunidades
            if not comunidades_df.empty and len(comunidades_df) > 0:
                st.subheader("Temas de Investigación por Comunidad")

                # Permitimos seleccionar una comunidad para analizar sus temas
                comunidad_seleccionada = st.selectbox(
                    "Seleccione una comunidad para ver sus temas principales:",
                    options=comunidades_df["autor_central"].tolist(),
                )

                if comunidad_seleccionada:
                    with st.spinner("Analizando temas de investigación..."):
                        query_temas = """
                        MATCH (central:Author {display_name: $autor_central})-[:AUTHORED]->(w:Work)<-[:AUTHORED]-(colab:Author)
                        WHERE central <> colab
                        WITH w.title AS titulo
                        WHERE titulo IS NOT NULL
                        WITH split(toLower(titulo), ' ') AS words
                        UNWIND words AS word
                        WITH word
                        WHERE size(word) > 3 
                        AND NOT word IN ['with','from','this','that','using','based','which','study','analysis','sobre','para']
                        RETURN word AS palabra, count(*) AS frecuencia
                        ORDER BY frecuencia DESC
                        LIMIT 15
                        """
                        temas_df = conn.query_to_dataframe(
                            query_temas, {"autor_central": comunidad_seleccionada}
                        )

                        if not temas_df.empty:
                            st.success(
                                f"Temas principales de la comunidad de {comunidad_seleccionada}:"
                            )
                            st.bar_chart(temas_df.set_index("palabra"))
