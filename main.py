#!/usr/bin/env python3

import streamlit as st
from dotenv import load_dotenv
from app.ui_utils import setup_page, get_connection, show_sidebar
from app.stats import mostrar_estadisticas
from app.authors import (
    buscar_autores,
    ver_trabajos_autor,
    ver_colaboradores,
    autores_temas_similares,
)
from app.works import buscar_trabajos
from app.concepts import explorador_conceptos
from app.institutions import explorador_instituciones
from app.collaboration import analisis_red_colaboracion

load_dotenv()


def main():
    """Función principal de la aplicación Streamlit"""
    setup_page()

    st.title("📊 Academic Graph Explorer")
    st.markdown(
        "Explore relaciones académicas entre autores, trabajos y colaboraciones."
    )

    conn = get_connection()

    if not conn:
        st.error("No se pudo establecer conexión con la base de datos Neo4j.")
        st.info("Verifique que las credenciales en el archivo .env sean correctas.")
        return

    # Mostrar barra lateral con opciones de navegación
    option = show_sidebar()

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
    elif "🧠 Explorador de Conceptos" in option:
        explorador_conceptos(conn)
    elif "🏢 Instituciones y Países" in option:
        explorador_instituciones(conn)
    elif "🌐 Análisis de Red de Colaboración" in option:
        analisis_red_colaboracion(conn)


if __name__ == "__main__":
    main()
