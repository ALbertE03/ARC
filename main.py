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


def mostrar_estadisticas(conn):
    """Muestra estadísticas generales de la base de datos"""
    st.header("📊 Estadísticas del Grafo Académico")

    with st.spinner("Calculando métricas..."):
        # Contenedor principal con pestañas
        tab1, tab2, tab3 = st.tabs(["Resumen General", "Autores", "Trabajos"])

        with tab1:
            st.subheader("📌 Resumen del Grafo")
            col1, col2 = st.columns(2)

            # Métricas básicas
            with col1:
                query = """
                MATCH (n)
                RETURN 
                    sum(CASE WHEN 'Author' IN labels(n) THEN 1 ELSE 0 END) AS autores,
                    sum(CASE WHEN 'Work' IN labels(n) THEN 1 ELSE 0 END) AS trabajos
                """
                stats = conn.query_to_dataframe(query).iloc[0]
                st.metric("Total de Autores", stats["autores"])
                st.metric("Total de Trabajos", stats["trabajos"])

            with col2:
                query = "MATCH ()-[r]->() RETURN count(r) AS relaciones"
                relaciones = conn.query_to_dataframe(query).iloc[0]["relaciones"]
                st.metric("Relaciones AUTHORED", relaciones)
                densidad = (
                    relaciones / (stats["autores"] * stats["trabajos"])
                    if stats["autores"] * stats["trabajos"] > 0
                    else 0
                )
                st.metric("Densidad de Colaboración", f"{densidad:.4f}")

            # Distribución de trabajos por año
            st.subheader("📅 Distribución de Trabajos por Año")
            query = """
            MATCH (w:Work)
            WHERE w.year IS NOT NULL AND w.year <> 'unknown'
            RETURN w.year AS año, count(*) AS cantidad
            ORDER BY año
            """
            años_df = conn.query_to_dataframe(query)
            if not años_df.empty:
                st.line_chart(años_df.set_index("año"))
            else:
                st.warning("No hay datos de años disponibles")

        with tab2:
            st.subheader("👥 Estadísticas de Autores")
            col1, col2 = st.columns(2)

            with col1:
                # Top autores más productivos
                st.markdown("**Top 10 Autores más Productivos**")
                query = """
                MATCH (a:Author)-[:AUTHORED]->(w:Work)
                RETURN a.label AS autor, count(w) AS trabajos
                ORDER BY trabajos DESC
                LIMIT 10
                """
                autores_df = conn.query_to_dataframe(query)
                st.dataframe(autores_df, use_container_width=True)

            with col2:
                # Autores con más colaboraciones
                st.markdown("**Autores con más Colaboradores**")
                query = """
                MATCH (a1:Author)-[:AUTHORED]->()<-[:AUTHORED]-(a2:Author)
                WHERE a1 <> a2
                RETURN a1.label AS autor, count(DISTINCT a2) AS colaboradores
                ORDER BY colaboradores DESC
                LIMIT 10
                """
                colab_df = conn.query_to_dataframe(query)
                st.dataframe(colab_df, use_container_width=True)

        with tab3:
            st.subheader("📚 Estadísticas de Trabajos")

            # Trabajos recientes
            st.markdown("**Trabajos más Recientes**")
            query = """
            MATCH (w:Work)
            WHERE w.year IS NOT NULL AND w.year <> 'unknown'
            RETURN w.label AS título, w.year AS año
            ORDER BY año DESC
            LIMIT 10
            """
            trabajos_df = conn.query_to_dataframe(query)
            st.dataframe(trabajos_df, use_container_width=True)

            # Palabras clave en títulos
            st.markdown("**Términos más Comunes en Títulos**")
            query = """
            MATCH (w:Work)
            WITH w.label AS title, split(toLower(w.label), ' ') AS words
            UNWIND words AS word
            WITH word
            WHERE size(word) > 3 
            AND NOT word IN ['with','from','this','that','using','based','which','study','analysis']
            RETURN word AS término, count(*) AS frecuencia
            ORDER BY frecuencia DESC
            LIMIT 15
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
                    query = """
                    MATCH (a:Author)
                    WHERE toLower(a.label) CONTAINS toLower($nombre)
                    RETURN a.id AS id, a.label AS nombre, a.orcid AS orcid
                    LIMIT 50
                    """

                    results = conn.query_to_dataframe(query, {"nombre": nombre})

                    if not results.empty:
                        st.success(f"Se encontraron {len(results)} autores.")
                        st.dataframe(results, use_container_width=True)
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
                    WHERE toLower(w.label) CONTAINS toLower($titulo)
                    RETURN w.id AS id, w.label AS título, w.year AS año
                    ORDER BY w.year DESC
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
                    WHERE toLower(a.label) CONTAINS toLower($nombre)
                    RETURN a.id AS id, a.label AS nombre
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
                            RETURN colab.label AS colaborador, count(distinct w) AS trabajos_juntos
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
                    # Primero buscamos al autor
                    query_autor = """
                    MATCH (a:Author)
                    WHERE toLower(a.label) CONTAINS toLower($nombre)
                    RETURN a.id AS id, a.label AS nombre
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
                        else:
                            autor_id = autores.iloc[0]["id"]
                            st.info(f"Autor seleccionado: {autores.iloc[0]['nombre']}")

                        # Ahora buscamos los trabajos
                        with st.spinner("Buscando trabajos..."):
                            query_trabajos = """
                            MATCH (a:Author {id: $autor_id})-[:AUTHORED]->(w:Work)
                            RETURN w.label AS título, w.year AS año
                            ORDER BY w.year DESC
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
                    query = """
                    MATCH (w:Work)
                    WHERE toLower(w.label) CONTAINS toLower($tema)
                    MATCH (a:Author)-[:AUTHORED]->(w)
                    WITH a, count(w) AS num_works
                    RETURN a.label AS autor, num_works AS trabajos_relacionados
                    ORDER BY num_works DESC
                    LIMIT 50
                    """

                    results = conn.query_to_dataframe(query, {"tema": tema})

                    if not results.empty:
                        st.success(
                            f"Se encontraron {len(results)} autores que trabajan en temas relacionados con '{tema}'."
                        )

                        col1, col2 = st.columns(2)

                        with col1:
                            st.dataframe(results, use_container_width=True)

                        with col2:
                            st.subheader("Top 10 Autores")
                            chart_data = results.head(10).sort_values(
                                "trabajos_relacionados"
                            )
                            st.bar_chart(chart_data.set_index("autor"))
                    else:
                        st.warning(
                            f"No se encontraron autores que trabajen en temas relacionados con '{tema}'."
                        )
            else:
                st.info("Por favor, ingrese un tema para buscar.")


if __name__ == "__main__":
    main()
