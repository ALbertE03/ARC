import streamlit as st
import pandas as pd


def buscar_autores(conn):
    """Buscar autores por nombre"""
    st.header("👤 Buscar Autores")

    with st.container():
        nombre = st.text_input(
            "Ingrese parte del nombre del autor:", placeholder="Ej: Smith"
        )

        if st.button("Buscar Autores") or nombre:
            if nombre:
                with st.spinner("Buscando autores..."):
                    # Búsqueda por nombre principal o nombres alternativos
                    # Contamos las relaciones AUTHORED salientes en lugar de usar la propiedad works_count
                    query = """
                    MATCH (a:Author)
                    WHERE toLower(a.display_name) CONTAINS toLower($nombre)
                       OR any(alt_name IN a.display_name_alternatives 
                              WHERE toLower(alt_name) CONTAINS toLower($nombre))
                    OPTIONAL MATCH (a)-[r:AUTHORED]->()
                    WITH a, count(r) AS trabajos_rel
                    RETURN a.id AS id, 
                           a.display_name AS nombre, 
                           trabajos_rel AS trabajos,
                           a.cited_by_count AS citaciones
                    ORDER BY trabajos DESC
                    LIMIT 50
                    """

                    results = conn.query_to_dataframe(query, {"nombre": nombre})

                    if not results.empty:
                        st.success(f"Se encontraron {len(results)} autores.")
                        st.dataframe(results, use_container_width=True)

                        # Mostrar algunos detalles adicionales
                        with st.expander("Mostrar detalles de autores"):
                            for i, row in results.head(5).iterrows():
                                st.subheader(f"{row['nombre']}")
                                st.markdown(f"**ID:** {row['id']}")
                                st.markdown(
                                    f"**Trabajos publicados (por relaciones):** {row['trabajos']}"
                                )
                                st.markdown(f"**Citaciones:** {row['citaciones']}")
                    else:
                        st.warning(
                            f"No se encontraron autores con el nombre '{nombre}'."
                        )
            else:
                st.info("Por favor, ingrese un nombre para buscar.")


def ver_trabajos_autor(conn):
    """Ver trabajos de un autor"""
    st.header("📚 Ver Trabajos de un Autor")

    with st.container():
        nombre = st.text_input(
            "Ingrese parte del nombre del autor:",
            placeholder="Ej: Anderson",
            key="works_search",
        )

        if st.button("Buscar Autor", key="works_button") or nombre:
            if nombre:
                with st.spinner("Buscando autor..."):
                    # Primero buscamos al autor usando relaciones para mostrar conteo de trabajos
                    query_autor = """
                    MATCH (a:Author)
                    WHERE toLower(a.display_name) CONTAINS toLower($nombre)
                       OR any(alt_name IN a.display_name_alternatives 
                              WHERE toLower(alt_name) CONTAINS toLower($nombre))
                    OPTIONAL MATCH (a)-[r:AUTHORED]->()
                    WITH a, count(r) AS num_trabajos
                    RETURN a.id AS id, a.display_name AS nombre, num_trabajos
                    ORDER BY num_trabajos DESC
                    LIMIT 10
                    """

                    autores = conn.query_to_dataframe(query_autor, {"nombre": nombre})

                    if not autores.empty:
                        if len(autores) > 1:
                            st.info("Se encontraron varios autores. Seleccione uno:")
                            autor_seleccionado = st.selectbox(
                                "Seleccione un autor:",
                                options=autores["nombre"].tolist(),
                                format_func=lambda x: x,
                                key="works_autor_select",
                            )
                            autor_id = autores[autores["nombre"] == autor_seleccionado][
                                "id"
                            ].iloc[0]
                            # Mostrar número de trabajos basado en relaciones
                            trabajos_count = autores[
                                autores["nombre"] == autor_seleccionado
                            ]["num_trabajos"].iloc[0]
                            st.info(
                                f"Autor seleccionado: {autor_seleccionado} ({trabajos_count} trabajos)"
                            )
                        else:
                            autor_id = autores.iloc[0]["id"]
                            trabajos_count = autores.iloc[0]["num_trabajos"]
                            st.info(
                                f"Autor seleccionado: {autores.iloc[0]['nombre']} ({trabajos_count} trabajos)"
                            )

                        # Ahora buscamos los trabajos
                        with st.spinner("Buscando trabajos..."):
                            query_trabajos = """
                            MATCH (a:Author {id: $autor_id})-[:AUTHORED]->(w:Work)
                            RETURN w.id AS id, w.title AS título, w.publication_year AS año,
                                   w.cited_by_count AS citaciones
                            ORDER BY w.publication_year DESC
                            """

                            trabajos = conn.query_to_dataframe(
                                query_trabajos, {"autor_id": autor_id}
                            )

                            if not trabajos.empty:
                                st.success(f"Se encontraron {len(trabajos)} trabajos.")

                                col1, col2 = st.columns(2)

                                with col1:
                                    st.dataframe(trabajos, use_container_width=True)

                                with col2:
                                    st.subheader("Distribución por año")
                                    if not trabajos.empty and "año" in trabajos.columns:
                                        años_conteo = (
                                            trabajos["año"].value_counts().sort_index()
                                        )
                                        st.bar_chart(años_conteo)
                            else:
                                st.warning(
                                    "No se encontraron trabajos para este autor."
                                )
                    else:
                        st.warning(
                            f"No se encontró ningún autor con el nombre '{nombre}'."
                        )
            else:
                st.info("Por favor, ingrese un nombre para buscar.")


def ver_colaboradores(conn):
    """Ver colaboradores de un autor"""
    st.header("🤝 Ver Colaboradores de un Autor")

    with st.container():
        nombre = st.text_input(
            "Ingrese parte del nombre del autor:",
            placeholder="Ej: Johnson",
            key="colab_search",
        )

        if st.button("Buscar Autor", key="colab_button") or nombre:
            if nombre:
                with st.spinner("Buscando autor..."):
                    # Primero buscamos al autor
                    query_autor = """
                    MATCH (a:Author)
                    WHERE toLower(a.display_name) CONTAINS toLower($nombre)
                       OR any(alt_name IN a.display_name_alternatives 
                              WHERE toLower(alt_name) CONTAINS toLower($nombre))
                    RETURN a.id AS id, a.display_name AS nombre
                    LIMIT 10
                    """

                    autores = conn.query_to_dataframe(query_autor, {"nombre": nombre})

                    if not autores.empty:
                        if len(autores) > 1:
                            st.info("Se encontraron varios autores. Seleccione uno:")
                            autor_seleccionado = st.selectbox(
                                "Seleccione un autor:",
                                options=autores["nombre"].tolist(),
                                format_func=lambda x: x,
                                key="autor_select",
                            )
                            autor_id = autores[autores["nombre"] == autor_seleccionado][
                                "id"
                            ].iloc[0]
                        else:
                            autor_id = autores.iloc[0]["id"]
                            st.info(f"Autor seleccionado: {autores.iloc[0]['nombre']}")

                        # Ahora buscamos los colaboradores
                        with st.spinner("Buscando colaboradores..."):
                            query_colaboradores = """
                            MATCH (a:Author {id: $autor_id})-[:AUTHORED]->(w:Work)<-[:AUTHORED]-(colab:Author)
                            WHERE a.id <> colab.id
                            RETURN colab.display_name AS colaborador, count(distinct w) AS trabajos_juntos
                            ORDER BY trabajos_juntos DESC
                            LIMIT 50
                            """

                            colaboradores = conn.query_to_dataframe(
                                query_colaboradores, {"autor_id": autor_id}
                            )

                            if not colaboradores.empty:
                                st.success(
                                    f"Se encontraron {len(colaboradores)} colaboradores."
                                )

                                col1, col2 = st.columns([2, 1])

                                with col1:
                                    st.dataframe(
                                        colaboradores, use_container_width=True
                                    )

                                with col2:
                                    st.subheader("Top Colaboradores")
                                    if len(colaboradores) > 0:
                                        chart_data = colaboradores.head(10).sort_values(
                                            "trabajos_juntos"
                                        )
                                        st.bar_chart(
                                            chart_data.set_index("colaborador")
                                        )
                            else:
                                st.warning(
                                    "No se encontraron colaboradores para este autor."
                                )
                    else:
                        st.warning(
                            f"No se encontró ningún autor con el nombre '{nombre}'."
                        )
            else:
                st.info("Por favor, ingrese un nombre para buscar.")


def autores_temas_similares(conn):
    """Ver autores que han trabajado en temas similares"""
    st.header("🔬 Autores por Tema")

    with st.container():
        tema = st.text_input(
            "Ingrese un tema o palabra clave:",
            placeholder="Ej: Inteligencia Artificial",
        )

        if st.button("Buscar Autores", key="theme_button") or tema:
            if tema:
                with st.spinner("Buscando autores relacionados al tema..."):
                    query = """
                    MATCH (a:Author)
                    OPTIONAL MATCH (a)-[:AUTHORED]->(w_all:Work)
                    WITH a, count(w_all) AS trabajos_totales
                    
                    OPTIONAL MATCH (a)-[:AUTHORED]->(w:Work)
                    WHERE toLower(w.title) CONTAINS toLower($tema)
                    WITH a, trabajos_totales, count(w) AS trabajos_relacionados
                    WHERE trabajos_relacionados > 0
                    
                    RETURN 
                        a.display_name AS autor, 
                        trabajos_relacionados,
                        trabajos_totales,
                        CASE 
                          WHEN trabajos_totales > 0 
                          THEN round(100.0 * trabajos_relacionados / trabajos_totales, 1) 
                          ELSE 0.0 
                        END AS porcentaje_especialización
                    ORDER BY trabajos_relacionados DESC, porcentaje_especialización DESC
                    LIMIT 50
                    """

                    results = conn.query_to_dataframe(query, {"tema": tema})

                    if not results.empty:
                        st.success(
                            f"Se encontraron {len(results)} autores que trabajan en temas relacionados con '{tema}'."
                        )

                        col1, col2 = st.columns(2)

                        with col1:
                            display_df = results[
                                [
                                    "autor",
                                    "trabajos_relacionados",
                                    "trabajos_totales",
                                    "porcentaje_especialización",
                                ]
                            ]
                            display_df.columns = [
                                "Autor",
                                "Trabajos en este tema",
                                "Trabajos totales",
                                "% Especialización",
                            ]
                            st.dataframe(display_df, use_container_width=True)

                        with col2:
                            st.subheader("Top 10 Autores")
                            chart_data = results.head(10).sort_values(
                                "trabajos_relacionados"
                            )
                            st.bar_chart(chart_data.set_index("autor"))

                        # Añadimos información sobre colaboradores en este tema
                        st.subheader("👥 Colaboraciones en este tema")
                        with st.spinner("Analizando colaboraciones en este tema..."):
                            query_colab_tema = """
                            MATCH (a1:Author)-[:AUTHORED]->(w:Work)<-[:AUTHORED]-(a2:Author)
                            WHERE a1 <> a2
                              AND toLower(w.title) CONTAINS toLower($tema)
                            WITH a1, a2, count(w) AS trabajos_juntos
                            ORDER BY trabajos_juntos DESC
                            LIMIT 20
                            RETURN a1.display_name AS autor1, 
                                   a2.display_name AS autor2, 
                                   trabajos_juntos AS colaboraciones_en_tema
                            """

                            colab_tema_df = conn.query_to_dataframe(
                                query_colab_tema, {"tema": tema}
                            )

                            if not colab_tema_df.empty:
                                st.dataframe(colab_tema_df, use_container_width=True)
                            else:
                                st.info(
                                    "No se encontraron colaboraciones frecuentes en este tema."
                                )
                    else:
                        st.warning(
                            f"No se encontraron autores que trabajen en temas relacionados con '{tema}'."
                        )
            else:
                st.info("Por favor, ingrese un tema para buscar.")
