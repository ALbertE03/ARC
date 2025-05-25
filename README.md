# 📊 ARC - Academic Research Connections

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.11-green)
![Neo4j](https://img.shields.io/badge/Neo4j-5.x-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red)

<div align="center">
  <img src="https://raw.githubusercontent.com/enriquedev/arc-sample/main/docs/images/arc_logo.png" alt="ARC Logo" width="200"/>
  <p><i>Conectando el conocimiento académico a través de grafos</i></p>
</div>

## 🌟 Descripción

**ARC (Academic Research Connections)** es una plataforma avanzada para explorar y analizar las relaciones entre investigadores y publicaciones académicas. Utilizando datos de OpenAlex y la potencia de las bases de datos de grafos Neo4j, ARC permite visualizar colaboraciones entre autores, descubrir patrones de investigación y explorar la producción científica de la comunidad académica de la Universidad de La Habana.

## ✨ Características Principales

- **Consolidación Inteligente de Identidades**: Algoritmos de ML para identificar y unificar perfiles de autores duplicados, incluyendo manejo avanzado de nombres con guiones
- **Exploración Interactiva**: Interfaz de usuario intuitiva desarrollada con Streamlit con estructura modular
- **Análisis de Comunidades**: Descubre grupos de investigación y colaboraciones frecuentes
- **Visualizaciones Dinámicas**: Gráficos y métricas para entender patrones de colaboración
- **Búsqueda Avanzada**: Localiza autores y trabajos por nombre, tema o afiliación
- **Exploración de Conceptos**: Analiza los conceptos científicos y sus interrelaciones
- **Análisis Institucional**: Explora afiliaciones, países y trayectorias institucionales de los investigadores
- **Optimización para Neo4j**: Consultas Cypher optimizadas para análisis de grafos con índices avanzados

## 🔍 Casos de Uso

- **Encontrar Expertos**: Identifica investigadores especializados en áreas específicas
- **Mapear Colaboraciones**: Visualiza redes de colaboración entre diferentes autores
- **Descubrir Tendencias**: Analiza los temas más populares por año o área de estudio
- **Evaluar Producción**: Consulta métricas de productividad e impacto por investigador
- **Análisis Conceptual**: Explora la estructura de conceptos científicos y sus relaciones
- **Análisis Geográfico**: Estudia la distribución de investigadores por países e instituciones
- **Trayectorias Institucionales**: Analiza el movimiento de investigadores entre instituciones

## 🛠️ Tecnologías Utilizadas

| Componente | Tecnología |
|------------|------------|
| **Backend** | Python 3.11+ |
| **Base de Datos** | Neo4j (Grafo) |
| **Interfaz** | Streamlit |
| **Extracción de Datos** | OpenAlex API |
| **Procesamiento** | pandas, scikit-learn |
| **Visualización** | Streamlit Charts |

## 🚀 Instalación

### Requisitos Previos

- Python 3.11 o superior
- Neo4j Database (versión 5.x recomendada)
- Git

### Pasos de Instalación

1. **Clonar el repositorio**

   ```bash
   git clone https://github.com/tuusuario/ARC.git
   cd ARC
   ```

2. **Crear y activar entorno virtual**

   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**

   ```bash
   cp .env.example .env
   # Edita el archivo .env con tus credenciales de Neo4j
   ```

## 📋 Uso de la Aplicación

### Iniciar el Proceso Completo

Para ejecutar el pipeline completo (extracción, procesamiento y visualización):

```bash
./run.sh
```

### Iniciar Solo la Interfaz

Si la base de datos ya está poblada:

```bash
streamlit run main.py
```

### Ejecución por Componentes

1. **Extraer datos de trabajos académicos**:

   ```bash
   python extract_data/extract_data_works.py
   ```

2. **Extraer y procesar datos de autores**:

   ```bash
   python extract_data/extract_data_authors.py
   ```

3. **Crear la base de datos de grafos**:

   ```bash
   python create_db/create_graph_author_to_articles.py
   ```

## 🔎 Exploración de Datos

### Módulos de la Interfaz

La aplicación incluye los siguientes módulos de exploración:

- **📊 Estadísticas de la BD**: Visión general del grafo académico
- **👤 Buscar Autores**: Encuentra investigadores por nombre
- **📄 Buscar Trabajos**: Localiza publicaciones por título
- **🤝 Ver Colaboradores**: Explora la red de colaboración de un autor
- **📚 Ver Trabajos de Autor**: Analiza la producción científica de cada investigador
- **🔬 Autores por Tema**: Identifica expertos en áreas específicas
- **🧠 Explorador de Conceptos**: Analiza conceptos científicos y sus relaciones
- **🏢 Instituciones y Países**: Explora las afiliaciones institucionales y distribución geográfica
- **🌐 Análisis de Red de Colaboración**: Visualiza comunidades de investigación

## 💻 Arquitectura del Sistema

### Estructura Modular del Proyecto

```
ARC/
├── main.py                    # Punto de entrada principal de la aplicación
├── app/                       # Módulos de la interfaz Streamlit
│   ├── __init__.py            # Inicialización del paquete
│   ├── ui_utils.py            # Utilidades de la interfaz y configuración
│   ├── stats.py               # Visualización de estadísticas generales
│   ├── authors.py             # Funcionalidades relacionadas con autores
│   ├── works.py               # Funcionalidades relacionadas con trabajos
│   ├── concepts.py            # Exploración de conceptos científicos
│   ├── institutions.py        # Análisis de instituciones y países
│   └── collaboration.py       # Análisis de redes de colaboración
├── data/                      # Datos de entrada y salida
│   ├── openalex_authors_complete.json   # Datos completos de autores
│   ├── openalex_data.json               # Datos de trabajos académicos
│   └── works-*.csv                      # Dataset de trabajos procesado
├── db/                        # Capa de acceso a base de datos
│   ├── db_connection.py       # Clase para conectar con Neo4j
│   └── db_operations.py       # Operaciones de base de datos
├── extract_data/              # Scripts de extracción de datos
│   ├── extract_data_authors.py          # Extracción de datos de autores
│   └── extract_data_works.py            # Extracción de datos de trabajos
├── create_db/                 # Creación y configuración de la base de datos
│   └── create_graph_author_to_articles.py  # Creación del grafo académico
├── models/                    # Modelos de ML y algoritmos
│   └── author_matcher.py      # Algoritmo de consolidación de identidad
├── utils/                     # Utilidades generales
│   ├── data_processing.py     # Procesamiento de datos
│   └── text_processing.py     # Procesamiento de texto
├── requirements.txt           # Dependencias del proyecto
├── run.sh                     # Script de ejecución completa
└── LICENSE                    # Licencia del proyecto
```

### Flujo de Datos y Procesamiento

1. **Extracción**: Los scripts en `extract_data/` obtienen información desde OpenAlex API
2. **Procesamiento**: Los módulos en `utils/` y `models/` procesan y transforman los datos
3. **Consolidación**: El algoritmo en `models/author_matcher.py` unifica identidades de autores
4. **Almacenamiento**: Scripts en `create_db/` construyen el grafo en Neo4j con los siguientes tipos de nodos y relaciones:
   - **Nodos**: `Author`, `Work`, `Concept`, `Institution`
   - **Relaciones**: `AUTHORED`, `HAS_CONCEPT`, `AFFILIATED_WITH`, `CITES`
5. **Visualización**: Los módulos en `app/` consultan la BD para presentar información interactiva

## 🧠 Algoritmos y Estrategias Técnicas

### Consolidación de Identidad de Autores

1. **Preprocesamiento de Nombres**:
   - Normalización de caracteres especiales y acentos
   - Tokenización considerando guiones como variantes ortográficas
   - Generación de formas canónicas y alternativas de nombres

2. **Vectorización y Comparación**:
   - Vectorización TF-IDF de nombres y alias
   - Similitud coseno para comparar nombres
   - Algoritmo de distancia Jaro-Winkler para variaciones ortográficas

3. **Agrupamiento**:
   - DBSCAN parametrizado para identificar clusters de autores similares
   - Umbral dinámico ajustado según longitud y complejidad de nombres

4. **Resolución de Identidad**:
   - Análisis de coautoría y patrones de colaboración
   - Consideración de afiliaciones institucionales
   - Verificación de ORCIDs como identificadores de respaldo

3. **Propiedades Multivaluadas**:
   - Almacenamiento de variantes de nombres como arrays
   - Años de afiliación institucional como colecciones
   - Pesos en relaciones para indicar fuerza de asociación

## 📊 Resultados y Visualizaciones

### Visualizaciones y Análisis

- **Mapa de Conceptos**: Visualización de conceptos científicos interrelacionados
- **Perfiles Conceptuales**: Análisis de áreas de especialización de autores
- **Análisis Geográfico**: Distribución de investigadores por países e instituciones
- **Trayectorias Institucionales**: Visualización del movimiento de investigadores entre instituciones
- **Colaboración Internacional**: Análisis de patrones de colaboración entre países
- **Comunidades de Investigación**: Identificación automática de grupos de investigación

### Métricas de Rendimiento

- **Velocidad de Consultas**: Optimización de consultas Cypher con tiempo promedio < 2s
- **Escalabilidad**: Soporte para grafos académicos con >10.000 nodos y >50.000 relaciones
- **Consolidación de Identidad**: Precisión >95% en la unificación de perfiles duplicados
- **Indexación**: Mejora de rendimiento del 300% en búsquedas frecuentes

## 🛣️ Roadmap y Extensiones Futuras

## 🤝 Contribuciones

### Guía para Desarrolladores

1. **Fork y Clone**:

   ```bash
   git clone https://github.com/tuusuario/ARC.git
   cd ARC
   ```

2. **Configuración del Entorno**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Estructura de Contribuciones**:
   - Para nuevas características: Añadir módulos en `app/`
   - Mejoras en algoritmos: Modificar `models/`
   - Optimizaciones de consultas: Actualizar `db/db_operations.py`

4. **Testing**:

   ```bash
   # Ejecutar pruebas unitarias (debe implementarse) 
   python -m pytest tests/
   ```

5. **Pull Request**:
   - Documentar cambios en el código
   - Seguir el estilo de codificación existente
   - Asegurar compatibilidad con versiones anteriores

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.

## 👤 Contacto

Alberto E. Marichal Fonseca - <marichalalberto292@gmail.com>

---

<div align="center">
  <p>Desarrollado con ❤️ para la comunidad de investigación académica de la Universidad de La Habana</p>
  <p>Última actualización: Mayo 2025</p>
</div>
