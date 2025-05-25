import streamlit as st
import pandas as pd


def explorador_conceptos(conn):
    """Exploración de conceptos científicos en la base de datos"""
    st.header("🧠 Explorador de Conceptos Científicos")
    st.markdown(
        "Explore los conceptos científicos, sus relaciones con autores y trabajos."
    )

    # Pestañas para diferentes formas de explorar conceptos
    tab1, tab2, tab3 = st.tabs(
        ["Buscar Conceptos", "Conceptos por Autor", "Red de Conceptos"]
    )

    with tab1:
        st.subheader("🔍 Buscar Conceptos")

        # Campo de búsqueda para conceptos
        concepto = st.text_input(
            "Buscar concepto por nombre:", placeholder="Ej: Artificial Intelligence"
        )

        if st.button("Buscar", key="search_concept") or concepto:
            if concepto:
                with st.spinner("Buscando conceptos..."):
                    # Consulta para encontrar conceptos que coincidan con el término de búsqueda
                    query = """
                    MATCH (c:Concept)
                    WHERE toLower(c.display_name) CONTAINS toLower($concepto)
                    RETURN 
                        c.id AS id_concepto,
                        c.display_name AS nombre,
                        c.level AS nivel,
                        c.score AS relevancia
                    ORDER BY c.level, c.score DESC
                    LIMIT 50
                    """

                    resultados = conn.query_to_dataframe(query, {"concepto": concepto})

                    if not resultados.empty:
                        st.success(
                            f"Se encontraron {len(resultados)} conceptos relacionados con '{concepto}'"
                        )

                        # Mostrar los resultados
                        st.dataframe(resultados, use_container_width=True)

                        # Permitir seleccionar un concepto para ver más detalles
                        if len(resultados) > 0:
                            concepto_seleccionado = st.selectbox(
                                "Seleccione un concepto para ver detalles:",
                                options=resultados["nombre"].tolist(),
                            )

                            if concepto_seleccionado:
                                concepto_id = resultados[
                                    resultados["nombre"] == concepto_seleccionado
                                ]["id_concepto"].iloc[0]

                                # Datos de autores que trabajan con este concepto
                                with st.spinner("Cargando autores relacionados..."):
                                    query_autores = """
                                    MATCH (a:Author)-[r:HAS_CONCEPT]->(c:Concept {id: $concepto_id})
                                    RETURN 
                                        a.display_name AS autor,
                                        r.score AS afinidad
                                    ORDER BY r.score DESC
                                    LIMIT 20
                                    """

                                    autores = conn.query_to_dataframe(
                                        query_autores, {"concepto_id": concepto_id}
                                    )

                                    if not autores.empty:
                                        st.subheader(
                                            f"Autores que trabajan en {concepto_seleccionado}"
                                        )
                                        autores["afinidad"] = autores["afinidad"].apply(
                                            lambda x: f"{x:.2f}"
                                        )
                                        st.dataframe(autores, use_container_width=True)
                                    else:
                                        st.info(
                                            "No se encontraron autores relacionados con este concepto."
                                        )

                                # Datos de trabajos que tratan este concepto
                                with st.spinner("Cargando trabajos relacionados..."):
                                    query_trabajos = """
                                    MATCH (w:Work)-[r:HAS_CONCEPT]->(c:Concept {id: $concepto_id})
                                    RETURN 
                                        w.title AS titulo,
                                        w.publication_year AS año,
                                        r.score AS relevancia
                                    ORDER BY r.score DESC
                                    LIMIT 20
                                    """

                                    trabajos = conn.query_to_dataframe(
                                        query_trabajos, {"concepto_id": concepto_id}
                                    )

                                    if not trabajos.empty:
                                        st.subheader(
                                            f"Trabajos sobre {concepto_seleccionado}"
                                        )
                                        trabajos["relevancia"] = trabajos[
                                            "relevancia"
                                        ].apply(lambda x: f"{x:.2f}")
                                        st.dataframe(trabajos, use_container_width=True)
                                    else:
                                        st.info(
                                            "No se encontraron trabajos relacionados con este concepto."
                                        )
                    else:
                        st.warning(
                            f"No se encontraron conceptos relacionados con '{concepto}'"
                        )
            else:
                st.info("Por favor, ingrese un término para buscar conceptos.")

    with tab2:
        st.subheader("👤 Conceptos por Autor")

        # Campo para buscar autor
        nombre_autor = st.text_input(
            "Ingrese el nombre del autor:",
            key="author_concept_search",
            placeholder="Ej: Johnson",
        )

        if st.button("Buscar", key="search_author_concepts") or nombre_autor:
            if nombre_autor:
                with st.spinner("Buscando autor..."):
                    # Buscar autor
                    query_autor = """
                    MATCH (a:Author)
                    WHERE toLower(a.display_name) CONTAINS toLower($nombre)
                       OR any(alt_name IN a.display_name_alternatives 
                              WHERE toLower(alt_name) CONTAINS toLower($nombre))
                    RETURN a.id AS id, a.display_name AS nombre
                    LIMIT 10
                    """

                    autores = conn.query_to_dataframe(
                        query_autor, {"nombre": nombre_autor}
                    )

                    if not autores.empty:
                        if len(autores) > 1:
                            autor_seleccionado = st.selectbox(
                                "Seleccione un autor:",
                                options=autores["nombre"].tolist(),
                                key="author_concept_select",
                            )
                            autor_id = autores[autores["nombre"] == autor_seleccionado][
                                "id"
                            ].iloc[0]
                            st.info(f"Autor seleccionado: {autor_seleccionado}")
                        else:
                            autor_id = autores.iloc[0]["id"]
                            st.info(f"Autor encontrado: {autores.iloc[0]['nombre']}")

                        # Obtener conceptos del autor
                        with st.spinner("Analizando perfil conceptual del autor..."):
                            query_conceptos = """
                            MATCH (a:Author {id: $autor_id})-[r:HAS_CONCEPT]->(c:Concept)
                            RETURN 
                                c.display_name AS concepto,
                                c.level AS nivel,
                                r.score AS afinidad
                            ORDER BY r.score DESC
                            LIMIT 30
                            """

                            conceptos = conn.query_to_dataframe(
                                query_conceptos, {"autor_id": autor_id}
                            )

                            if not conceptos.empty:
                                st.subheader("Perfil Conceptual del Autor")

                                col1, col2 = st.columns([2, 1])

                                with col1:
                                    st.dataframe(conceptos, use_container_width=True)

                                with col2:
                                    st.subheader("Principales Áreas")
                                    chart_data = conceptos.head(10).sort_values(
                                        "afinidad"
                                    )
                                    st.bar_chart(
                                        chart_data.set_index("concepto")["afinidad"]
                                    )

                                # Conceptos relacionados (conceptos similares a los del autor)
                                with st.expander(
                                    "Ver conceptos relacionados", expanded=False
                                ):
                                    with st.spinner("Buscando conceptos similares..."):
                                        # Tomamos los primeros 5 conceptos del autor para buscar similares
                                        top_conceptos = conceptos.head(5)[
                                            "concepto"
                                        ].tolist()

                                        if top_conceptos:
                                            query_relacionados = """
                                            MATCH (c1:Concept)<-[:HAS_CONCEPT]-(w:Work)-[:HAS_CONCEPT]->(c2:Concept)
                                            WHERE c1.display_name IN $top_conceptos
                                              AND NOT c2.display_name IN $top_conceptos
                                            WITH c2, count(DISTINCT w) AS comun
                                            RETURN 
                                                c2.display_name AS concepto_relacionado,
                                                comun AS frecuencia_relacion
                                            ORDER BY comun DESC
                                            LIMIT 15
                                            """

                                            relacionados = conn.query_to_dataframe(
                                                query_relacionados,
                                                {"top_conceptos": top_conceptos},
                                            )

                                            if not relacionados.empty:
                                                st.subheader("Conceptos Relacionados")
                                                st.dataframe(
                                                    relacionados,
                                                    use_container_width=True,
                                                )
                                            else:
                                                st.info(
                                                    "No se encontraron conceptos relacionados."
                                                )
                            else:
                                st.warning(
                                    "No se encontraron conceptos asociados a este autor."
                                )
                    else:
                        st.warning(
                            f"No se encontró ningún autor con el nombre '{nombre_autor}'"
                        )
            else:
                st.info("Por favor, ingrese un nombre de autor para buscar.")

    with tab3:
        st.subheader("🕸️ Red de Conceptos")
        st.markdown(
            """
        Esta visualización muestra cómo los conceptos científicos se relacionan entre sí.
        Los conceptos se consideran relacionados cuando aparecen juntos en trabajos.
        """
        )

        # Controles para filtrar la red de conceptos
        min_relacion = st.slider(
            "Fuerza mínima de relación",
            min_value=1,
            max_value=20,
            value=3,
            help="Número mínimo de trabajos que comparten ambos conceptos",
        )

        nivel_max = st.slider(
            "Nivel máximo de profundidad conceptual", min_value=1, max_value=5, value=3
        )

        if st.button("Generar Red de Conceptos"):
            with st.spinner(
                "Analizando relaciones entre conceptos (esto puede tardar unos momentos)..."
            ):
                # Consulta para encontrar conceptos relacionados
                query_red = """
                MATCH (c1:Concept)<-[:HAS_CONCEPT]-(w:Work)-[:HAS_CONCEPT]->(c2:Concept)
                WHERE c1 <> c2
                  AND c1.level <= $nivel_max AND c2.level <= $nivel_max
                WITH c1, c2, count(DISTINCT w) AS trabajos_comunes
                WHERE trabajos_comunes >= $min_relacion
                RETURN 
                    c1.display_name AS concepto1,
                    c2.display_name AS concepto2,
                    trabajos_comunes AS fuerza_relacion
                ORDER BY fuerza_relacion DESC
                LIMIT 200
                """

                red = conn.query_to_dataframe(
                    query_red, {"min_relacion": min_relacion, "nivel_max": nivel_max}
                )

                if not red.empty:
                    st.success(f"Se encontraron {len(red)} conexiones entre conceptos.")

                    # Extraer conceptos únicos para ver distribución
                    conceptos_unicos = set()
                    for i, row in red.iterrows():
                        conceptos_unicos.add(row["concepto1"])
                        conceptos_unicos.add(row["concepto2"])

                    st.markdown(f"Total conceptos: {len(conceptos_unicos)}")
                    st.dataframe(red, use_container_width=True)

                    # Análisis de agrupamiento
                    st.subheader("Agrupaciones Temáticas")

                    # Agrupar por concepto1 y ver con cuántos otros conceptos se relaciona
                    agrupaciones = (
                        red.groupby("concepto1")
                        .agg(
                            conexiones=("concepto2", "nunique"),
                            fuerza_media=("fuerza_relacion", "mean"),
                        )
                        .reset_index()
                        .sort_values("conexiones", ascending=False)
                    )

                    st.markdown("**Conceptos con más conexiones:**")
                    st.dataframe(agrupaciones.head(15), use_container_width=True)

                    # Para algunos conceptos principales, mostrar sus conexiones
                    if len(agrupaciones) > 0:
                        concepto_principal = st.selectbox(
                            "Seleccione un concepto para ver sus conexiones:",
                            options=agrupaciones.head(15)["concepto1"].tolist(),
                        )

                        if concepto_principal:
                            conexiones = red[
                                red["concepto1"] == concepto_principal
                            ].sort_values("fuerza_relacion", ascending=False)

                            st.subheader(
                                f"Conceptos relacionados con '{concepto_principal}'"
                            )
                            st.dataframe(
                                conexiones[["concepto2", "fuerza_relacion"]],
                                use_container_width=True,
                            )
                else:
                    st.warning(
                        "No se encontraron relaciones entre conceptos con los filtros actuales. "
                        "Intente reducir la fuerza mínima de relación o incrementar el nivel máximo."
                    )
