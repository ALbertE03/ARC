import streamlit as st
import pandas as pd


def explorador_instituciones(conn):
    """Explorar instituciones y países en la base de datos"""
    st.header("🏢 Explorador de Instituciones y Países")
    st.markdown("Analice la distribución de investigadores por instituciones y países.")

    # Pestañas para diferentes análisis
    tab1, tab2, tab3 = st.tabs(
        ["Buscar Instituciones", "Análisis por País", "Trayectorias Institucionales"]
    )

    with tab1:
        st.subheader("🔍 Buscar Instituciones")

        # Campo de búsqueda para instituciones
        institucion = st.text_input(
            "Ingrese parte del nombre de la institución:",
            placeholder="Ej: Universidad de La Habana",
        )

        if st.button("Buscar", key="search_institution") or institucion:
            if institucion:
                with st.spinner("Buscando instituciones..."):
                    # Consulta para encontrar instituciones que coincidan con el término de búsqueda
                    query = """
                    MATCH (i:Institution)
                    WHERE toLower(i.name) CONTAINS toLower($institucion)
                    RETURN 
                        i.id AS id_institucion,
                        i.name AS nombre,
                        i.country_code AS pais
                    ORDER BY i.name
                    LIMIT 50
                    """

                    resultados = conn.query_to_dataframe(
                        query, {"institucion": institucion}
                    )

                    if not resultados.empty:
                        st.success(
                            f"Se encontraron {len(resultados)} instituciones relacionadas con '{institucion}'"
                        )
                        st.dataframe(resultados, use_container_width=True)

                        # Permitir seleccionar una institución para ver detalles
                        if len(resultados) > 0:
                            institucion_seleccionada = st.selectbox(
                                "Seleccione una institución para ver detalles:",
                                options=resultados["nombre"].tolist(),
                            )

                            if institucion_seleccionada:
                                inst_id = resultados[
                                    resultados["nombre"] == institucion_seleccionada
                                ]["id_institucion"].iloc[0]

                                # Obtener investigadores afiliados a esta institución
                                with st.spinner("Buscando investigadores afiliados..."):
                                    query_afiliados = """
                                    MATCH (a:Author)-[r:AFFILIATED_WITH]->(i:Institution {id: $inst_id})
                                    OPTIONAL MATCH (a)-[:AUTHORED]->(w)
                                    WITH a, i, count(DISTINCT w) AS num_trabajos, r.years AS años
                                    RETURN 
                                        a.display_name AS investigador,
                                        num_trabajos AS trabajos,
                                        CASE WHEN años IS NOT NULL THEN size(años) ELSE 0 END AS años_afiliacion
                                    ORDER BY num_trabajos DESC
                                    LIMIT 50
                                    """

                                    afiliados = conn.query_to_dataframe(
                                        query_afiliados, {"inst_id": inst_id}
                                    )

                                    if not afiliados.empty:
                                        st.subheader(
                                            f"Investigadores afiliados a {institucion_seleccionada}"
                                        )
                                        st.dataframe(
                                            afiliados, use_container_width=True
                                        )

                                        col1, col2 = st.columns(2)

                                        with col1:
                                            st.subheader("Top Investigadores")
                                            chart_data = afiliados.head(10).sort_values(
                                                "trabajos"
                                            )
                                            st.bar_chart(
                                                chart_data.set_index("investigador")[
                                                    "trabajos"
                                                ]
                                            )
                                    else:
                                        st.info(
                                            "No se encontraron investigadores afiliados a esta institución."
                                        )

                                # Conceptos principales en esta institución
                                with st.spinner(
                                    "Analizando perfil temático de la institución..."
                                ):
                                    query_conceptos = """
                                    MATCH (a:Author)-[:AFFILIATED_WITH]->(i:Institution {id: $inst_id})
                                    MATCH (a)-[:AUTHORED]->(w:Work)-[r:HAS_CONCEPT]->(c:Concept)
                                    RETURN 
                                        c.display_name AS concepto,
                                        count(DISTINCT w) AS frecuencia,
                                        avg(r.score) AS relevancia_media
                                    ORDER BY frecuencia DESC, relevancia_media DESC
                                    LIMIT 20
                                    """

                                    conceptos = conn.query_to_dataframe(
                                        query_conceptos, {"inst_id": inst_id}
                                    )

                                    if not conceptos.empty:
                                        st.subheader(
                                            f"Perfil Temático de {institucion_seleccionada}"
                                        )
                                        st.dataframe(
                                            conceptos, use_container_width=True
                                        )

                                        st.subheader(
                                            "Principales Áreas de Investigación"
                                        )
                                        chart_data = conceptos.head(10)
                                        st.bar_chart(
                                            chart_data.set_index("concepto")[
                                                "frecuencia"
                                            ]
                                        )
                                    else:
                                        st.info(
                                            "No se encontraron conceptos asociados a esta institución."
                                        )
                    else:
                        st.warning(
                            f"No se encontraron instituciones relacionadas con '{institucion}'"
                        )
            else:
                st.info("Por favor, ingrese un nombre de institución para buscar.")

    with tab2:
        st.subheader("🌎 Análisis por País")

        with st.spinner("Analizando distribución de investigadores por país..."):
            # Consulta para obtener la distribución de investigadores por país
            query_paises = """
            MATCH (a:Author)-[:AFFILIATED_WITH]->(i:Institution)
            WHERE i.country_code IS NOT NULL
            RETURN 
                i.country_code AS pais,
                count(DISTINCT a) AS investigadores
            ORDER BY investigadores DESC
            LIMIT 50
            """

            paises = conn.query_to_dataframe(query_paises)

            if not paises.empty:
                st.success(f"Se encontraron datos de {len(paises)} países.")

                # Mostrar resultados
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.dataframe(paises, use_container_width=True)

                with col2:
                    st.subheader("Top 10 Países")
                    chart_data = paises.head(10).sort_values("investigadores")
                    st.bar_chart(chart_data.set_index("pais"))

                # Permitir seleccionar un país para análisis detallado
                pais_seleccionado = st.selectbox(
                    "Seleccione un país para análisis detallado:",
                    options=paises["pais"].tolist(),
                )

                if pais_seleccionado:
                    with st.spinner(
                        f"Analizando instituciones en {pais_seleccionado}..."
                    ):
                        # Consulta para obtener las principales instituciones del país
                        query_instituciones = """
                        MATCH (a:Author)-[:AFFILIATED_WITH]->(i:Institution)
                        WHERE i.country_code = $pais
                        RETURN 
                            i.name AS institucion,
                            count(DISTINCT a) AS investigadores
                        ORDER BY investigadores DESC
                        LIMIT 20
                        """

                        instituciones_pais = conn.query_to_dataframe(
                            query_instituciones, {"pais": pais_seleccionado}
                        )

                        if not instituciones_pais.empty:
                            st.subheader(
                                f"Principales Instituciones en {pais_seleccionado}"
                            )
                            st.dataframe(instituciones_pais, use_container_width=True)

                            st.subheader("Top Instituciones")
                            chart_data = instituciones_pais.head(10).sort_values(
                                "investigadores"
                            )
                            st.bar_chart(chart_data.set_index("institucion"))

                            # Análisis de colaboraciones internacionales para este país
                            with st.spinner(
                                "Analizando colaboraciones internacionales..."
                            ):
                                query_colaboraciones = """
                                MATCH (a1:Author)-[:AFFILIATED_WITH]->(i1:Institution)
                                WHERE i1.country_code = $pais
                                MATCH (a1)-[:AUTHORED]->(w:Work)<-[:AUTHORED]-(a2:Author)
                                WHERE a1 <> a2
                                MATCH (a2)-[:AFFILIATED_WITH]->(i2:Institution)
                                WHERE i2.country_code <> $pais AND i2.country_code IS NOT NULL
                                RETURN 
                                    i2.country_code AS pais_colaborador,
                                    count(DISTINCT w) AS num_colaboraciones
                                ORDER BY num_colaboraciones DESC
                                LIMIT 15
                                """

                                colaboraciones = conn.query_to_dataframe(
                                    query_colaboraciones, {"pais": pais_seleccionado}
                                )

                                if not colaboraciones.empty:
                                    st.subheader(
                                        f"Principales Colaboraciones Internacionales de {pais_seleccionado}"
                                    )
                                    st.dataframe(
                                        colaboraciones, use_container_width=True
                                    )

                                    st.bar_chart(
                                        colaboraciones.set_index("pais_colaborador")
                                    )
                                else:
                                    st.info(
                                        f"No se encontraron colaboraciones internacionales para {pais_seleccionado}."
                                    )
                        else:
                            st.warning(
                                f"No se encontraron instituciones en {pais_seleccionado}."
                            )
            else:
                st.warning("No se encontraron datos de países en la base de datos.")

    with tab3:
        st.subheader("🛤️ Trayectorias Institucionales")
        st.markdown(
            """
        Esta sección permite analizar cómo los investigadores cambian de institución a lo largo de su carrera.
        Identifique patrones de movilidad académica entre instituciones y países.
        """
        )

        # Buscar un investigador para ver su trayectoria
        nombre_autor = st.text_input(
            "Ingrese el nombre de un investigador:",
            key="author_institution_search",
            placeholder="Ej: García López",
        )

        if st.button("Buscar", key="search_author_trajectory") or nombre_autor:
            if nombre_autor:
                with st.spinner("Buscando investigador..."):
                    # Búsqueda mejorada que detecta nombres con/sin guiones
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
                        autor_seleccionado = autores.iloc[0]["nombre"]
                        autor_id = autores.iloc[0]["id"]

                        if len(autores) > 1:
                            autor_seleccionado = st.selectbox(
                                "Seleccione un investigador:",
                                options=autores["nombre"].tolist(),
                                key="trajectory_author_select",
                            )
                            autor_id = autores[autores["nombre"] == autor_seleccionado][
                                "id"
                            ].iloc[0]

                        st.info(f"Investigador seleccionado: {autor_seleccionado}")

                        # Obtener afiliaciones del investigador
                        with st.spinner("Analizando trayectoria institucional..."):
                            query_trayectoria = """
                            MATCH (a:Author {id: $autor_id})-[r:AFFILIATED_WITH]->(i:Institution)
                            RETURN 
                                i.name AS institucion,
                                i.country_code AS pais,
                                r.years AS años
                            ORDER BY i.name
                            """

                            trayectoria = conn.query_to_dataframe(
                                query_trayectoria, {"autor_id": autor_id}
                            )

                            if not trayectoria.empty:
                                st.subheader("Afiliaciones Institucionales")
                                trayectoria_procesada = []

                                for i, row in trayectoria.iterrows():
                                    años = row["años"]
                                    años_str = (
                                        ", ".join([str(a) for a in años])
                                        if isinstance(años, list)
                                        else "N/A"
                                    )

                                    trayectoria_procesada.append(
                                        {
                                            "Institución": row["institucion"],
                                            "País": (
                                                row["pais"]
                                                if pd.notna(row["pais"])
                                                else "Desconocido"
                                            ),
                                            "Años": años_str,
                                        }
                                    )

                                st.dataframe(
                                    pd.DataFrame(trayectoria_procesada),
                                    use_container_width=True,
                                )
                            else:
                                st.warning(
                                    "No se encontraron datos de afiliaciones para este investigador."
                                )
                    else:
                        st.warning(
                            f"No se encontró ningún investigador con el nombre '{nombre_autor}'"
                        )
            else:
                st.info(
                    "Por favor, ingrese el nombre de un investigador para analizar su trayectoria."
                )
