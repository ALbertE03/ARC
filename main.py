#!/usr/bin/env python3

import streamlit as st
import pandas as pd
from db.db_connection import Neo4jConnection
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Academic Graph Explorer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    :root {
        --primary-color: #4a6fa5;
        --secondary-color: #166088;
        --accent-color: #4fc3f7;
        --background-color: #f8f9fa;
        --card-color: #ffffff;
    }
    
    .main {
        padding: 0rem 1rem;
    }
    
    .stAlert > div {
        padding: 0.8rem 1.2rem;
        border-radius: 0.75rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    h1, h2, h3 {
        color: var(--secondary-color) !important;
    }
    
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        background-color: var(--secondary-color);
        transform: translateY(-2px);
    }
    
    .card {
        background-color: var(--card-color);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
    }
    
    .tabs {
        display: flex;
        margin-bottom: 1rem;
    }
    
    .tab {
        padding: 0.5rem 1rem;
        cursor: pointer;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
        background-color: #e9ecef;
    }
    
    .tab.active {
        background-color: var(--primary-color);
        color: white;
    }
    
    .dataframe {
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    
    .stTextInput>div>div>input {
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_connection():
    """Establece una conexión con Neo4j y la almacena en caché"""
    try:
        conn = Neo4jConnection()
        conn.connect()
        return conn
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None


def main():
    """Función principal de la aplicación Streamlit"""

    st.title("📊 Academic Graph Explorer")
    st.markdown(
        "Explore relaciones académicas entre autores, trabajos y colaboraciones."
    )

    # Conexión a la base de datos
    conn = get_connection()

    if not conn:
        st.error("No se pudo establecer conexión con la base de datos Neo4j.")
        st.info("Verifique que las credenciales en el archivo .env sean correctas.")
        return

    # Barra lateral con opciones
    with st.sidebar:
        st.header("🔍 Navegación")
        option = st.radio(
            "Seleccione una opción:",
            [
                "📊 Estadísticas de la BD",
                "👤 Buscar Autores",
                "📄 Buscar Trabajos",
                "🤝 Ver Colaboradores",
                "📚 Ver Trabajos de Autor",
                "🔬 Autores por Tema",
                "🌐 Análisis de Red de Colaboración",
            ],
        )

    # Contenido principal basado en la opción seleccionada
    if "📊 Estadísticas de la BD" in option:
        mostrar_estadisticas(conn)
    elif "👤 Buscar Autores" in option:
        buscar_autores(conn)
    elif "📄 Buscar Trabajos" in option:
        buscar_trabajos(conn)
    elif "🤝 Ver Colaboradores" in option:
        ver_colaboradores(conn)
    elif "📚 Ver Trabajos de Autor" in option:
        ver_trabajos_autor(conn)
    elif "🔬 Autores por Tema" in option:
        autores_temas_similares(conn)
    elif "🌐 Análisis de Red de Colaboración" in option:
        analisis_red_colaboracion(conn)


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
                    # Consulta basada en relaciones para encontrar autores por tema
                    # Optimización: calculamos trabajos totales y relacionados en una sola consulta
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
                            # Mostramos conteo total de trabajos para comparar
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
            # Consulta basada en relaciones para encontrar colaboraciones directas
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
            WITH a1, a2, count(w) AS colaboraciones
            WHERE colaboraciones >= $min_colaboraciones
            
            WITH a1, collect({autor: a2.display_name, trabajos: colaboraciones}) AS colaboradores
            WHERE size(colaboradores) >= 2
            
            RETURN 
                a1.display_name AS autor_central,
                size(colaboradores) AS tamaño_red,
                [c IN colaboradores | c.autor] AS miembros_principales,
                [c IN colaboradores | c.trabajos] AS intensidad_colaboracion
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
                        # Creamos una tabla con miembros y su intensidad de colaboración
                        miembros_tabla = pd.DataFrame(
                            {
                                "Colaborador": row["miembros_principales"][
                                    :10
                                ],  # Limitamos a 10
                                "Trabajos conjuntos": row["intensidad_colaboracion"][
                                    :10
                                ],
                            }
                        )
                        st.dataframe(miembros_tabla, use_container_width=True)
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


if __name__ == "__main__":
    main()
