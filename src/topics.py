import streamlit as st
# Asumimos que keyword_metrics es un diccionario que contiene los DataFrames
# keyword_metrics = {'top_keywords': df1, 'central_keywords': df2}

def render_topic_page(keyword_metrics):
    """
    Renderiza la página de análisis de temas con múltiples expanders.
    """
    with st.expander("📚 Temas más relevantes (por frecuencia)", expanded=True):
        st.markdown("Las palabras clave que aparecen en el mayor número de artículos, indicando las áreas de investigación más populares en la institución.")
        # st.dataframe(keyword_metrics['top_keywords'], use_container_width=True, hide_index=True)
        # st.bar_chart(keyword_metrics['top_keywords'].head(10).set_index('Tema'), color="#00aaff")
        st.info("Aquí iría la tabla y el gráfico de barras de los temas más frecuentes.", icon="📊")


    with st.expander("🧠 Temas más centrales (por conexiones)"):
        st.markdown("Temas que actúan como **puentes**, conectando una amplia gama de otras áreas de investigación. Son clave para la interdisciplinariedad.")
        # st.dataframe(keyword_metrics['central_keywords'], use_container_width=True, hide_index=True)
        st.info("Aquí iría la tabla de los temas con mayor centralidad en la red.", icon="🕸️")


    with st.expander("🏷️ Clasificación en Áreas de Conocimiento"):
        st.markdown("""
        Clasifica automáticamente los temas de investigación en **dominios y campos de estudio de alto nivel** (ej. 'Computer Science', 'Sociology', 'Medicine') utilizando bases de datos académicas como OpenAlex. 
        
        Esto ayuda a obtener una vista panorámica de las fortalezas de la institución.
        """)
        st.info("Aquí se mostraría una tabla con [Tema, Dominio Principal, Campo de Estudio].", icon="📚")
        

    with st.expander("📈 Tendencias Temporales de Temas (Evolución)"):
        st.markdown("""
        Analiza cómo ha evolucionado el interés en los temas a lo largo del tiempo. Permite identificar:
        - **Temas Emergentes:** Aquellos que han ganado popularidad rápidamente en los últimos años.
        - **Temas Consolidados:** Los que mantienen una presencia constante.
        - **Temas en Declive:** Áreas que han perdido protagonismo.
        """)
        st.info("Aquí se podría mostrar un gráfico de líneas con la frecuencia de temas por año.", icon="📉")


    with st.expander("🤝 Clusters Temáticos y Comunidades de Conocimiento"):
        st.markdown("""
        Identifica grupos de palabras clave que aparecen juntas con frecuencia, formando **"comunidades de conocimiento"**. 
        
        Por ejemplo, podrías descubrir un cluster que agrupa `['inteligencia artificial', 'redes neuronales', 'procesamiento de lenguaje']` y otro sobre `['sostenibilidad', 'energía solar', 'cambio climático']`.
        """)
        st.info("Ideal para una visualización de red donde cada color representa un cluster temático.", icon="🎨")


    with st.expander("🔗 Pares de Temas con Mayor Co-ocurrencia"):
        st.markdown("""
        Muestra los pares de temas que aparecen juntos con más frecuencia en los mismos artículos. Es una forma directa de medir la **colaboración interdisciplinaria** a nivel de temas.
        
        Por ejemplo, `('genética', 'bioinformática')` o `('políticas públicas', 'economía')`.
        """)
        st.info("Aquí se presentaría una tabla de [Tema A, Tema B, Frecuencia Conjunta].", icon="🔗")


    with st.expander("🗺️ Análisis de Brechas y Oportunidades (White-Space Analysis)"):
        st.markdown("""
        Un análisis más avanzado que busca **"espacios en blanco"** en el mapa de investigación. Identifica temas que están relacionados en la literatura global pero que aún no han sido conectados en las publicaciones de la institución.
        
        Esto permite descubrir **oportunidades de investigación innovadoras y colaboraciones potenciales**.
        """)
        st.warning("Este análisis es avanzado y requiere comparar la red interna con una base de datos externa.", icon="💡")

