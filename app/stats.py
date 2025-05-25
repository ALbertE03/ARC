import streamlit as st
import pandas as pd


def mostrar_estadisticas(conn):
    """Muestra estadísticas generales de la base de datos"""
    st.header("📊 Estadísticas del Grafo Académico")

    with st.spinner("Calculando métricas..."):
        # Contenedor principal con pestañas
        tab1, tab2, tab3 = st.tabs(["Resumen General", "Autores", "Trabajos"])

        with tab1:
            st.subheader("📌 Resumen del Grafo")
            col1, col2 = st.columns(2)

            query = """
            CALL () {
                MATCH (a:Author)
                RETURN count(a) AS autores
            }
            CALL () {
                MATCH (w:Work)
                RETURN count(w) AS trabajos
            }
            CALL () {
                MATCH ()-[r:AUTHORED]->()
                RETURN count(r) AS relaciones
            }
            RETURN autores, trabajos, relaciones
            """
            stats = conn.query_to_dataframe(query).iloc[0]

            # Mostramos métricas básicas
            with col1:
                st.metric("Total de Autores", stats["autores"])
                st.metric("Total de Trabajos", stats["trabajos"])

            with col2:
                st.metric("Relaciones AUTHORED", stats["relaciones"])
                # Cálculo de densidad con los datos ya obtenidos
                densidad = (
                    stats["relaciones"] / (stats["autores"] * stats["trabajos"])
                    if stats["autores"] * stats["trabajos"] > 0
                    else 0
                )
                st.metric("Densidad de Colaboración", f"{densidad:.4f}")

            # Distribución de trabajos por año - Optimizada con LIMIT
            st.subheader("📅 Distribución de Trabajos por Año")
            query = """
            MATCH (w:Work)
            WHERE w.publication_year IS NOT NULL 
            WITH w.publication_year AS año
            RETURN año, count(*) AS cantidad
            ORDER BY año
            """
            # Ejecutamos pero mostramos un indicador de carga
            with st.spinner("Cargando gráfico de distribución por año..."):
                años_df = conn.query_to_dataframe(query)
                if not años_df.empty:
                    st.line_chart(años_df.set_index("año"))
                else:
                    st.warning("No hay datos de años disponibles")

        with tab2:
            st.subheader("👥 Estadísticas de Autores")

            # Consulta optimizada: Top autores más productivos y con más colaboradores en paralelo
            col1, col2 = st.columns(2)

            # Ejecutamos las consultas en paralelo mostrando indicadores de carga independientes
            with col1:
                st.markdown("**Top 10 Autores más Productivos**")
                with st.spinner("Cargando autores..."):
                    # Consulta optimizada: usamos LIMIT más temprano en la consulta
                    query = """
                    MATCH (a:Author)-[:AUTHORED]->(w:Work)
                    WITH a, count(w) AS trabajos
                    ORDER BY trabajos DESC
                    LIMIT 10
                    RETURN a.display_name AS autor, trabajos
                    """
                    autores_df = conn.query_to_dataframe(query)
                    st.dataframe(autores_df, use_container_width=True)

            with col2:
                st.markdown("**Autores con más Colaboradores**")
                with st.spinner("Cargando colaboradores..."):
                    # Consulta optimizada: limitamos los resultados más temprano
                    query = """
                    MATCH (a1:Author)-[:AUTHORED]->(w:Work)<-[:AUTHORED]-(a2:Author)
                    WHERE a1 <> a2
                    WITH a1, count(DISTINCT a2) AS colaboradores
                    ORDER BY colaboradores DESC
                    LIMIT 10
                    RETURN a1.display_name AS autor, colaboradores
                    """
                    colab_df = conn.query_to_dataframe(query)
                    st.dataframe(colab_df, use_container_width=True)

        with tab3:
            st.subheader("📚 Estadísticas de Trabajos")

            # Trabajos recientes - Consulta optimizada
            st.markdown("**Trabajos más Recientes**")
            with st.spinner("Cargando trabajos recientes..."):
                query = """
                MATCH (w:Work)
                WHERE w.publication_year IS NOT NULL
                RETURN w.title AS título, w.publication_year AS año
                ORDER BY año DESC
                LIMIT 10
                """
                trabajos_df = conn.query_to_dataframe(query)
                st.dataframe(trabajos_df, use_container_width=True)

            # Palabras clave - Consulta optimizada con límites tempranos
            st.markdown("**Términos más Comunes en Títulos**")
            with st.spinner("Analizando términos..."):
                query = """
                MATCH (w:Work)
                WHERE w.title IS NOT NULL
                WITH w.title AS title
                LIMIT 1000
                WITH split(toLower(title), ' ') AS words
                UNWIND words AS word
                WITH word
                WHERE size(word) > 3 
                AND NOT word IN ['with','from','this','that','using','based','which','study','analysis']
                WITH word, count(*) AS frecuencia
                ORDER BY frecuencia DESC
                LIMIT 15
                RETURN word AS término, frecuencia
                """
                palabras_df = conn.query_to_dataframe(query)
                if not palabras_df.empty:
                    st.bar_chart(palabras_df.set_index("término"))
                else:
                    st.warning("No se pudieron extraer términos de los títulos")
