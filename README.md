# 📊 ARC - Academic Research Connections

![Version](https://img.shields.io/badge/version-1.0.0-blue)
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

- **Consolidación Inteligente de Identidades**: Algoritmos de ML para identificar y unificar perfiles de autores duplicados
- **Exploración Interactiva**: Interfaz de usuario intuitiva desarrollada con Streamlit
- **Análisis de Comunidades**: Descubre grupos de investigación y colaboraciones frecuentes
- **Visualizaciones Dinámicas**: Gráficos y métricas para entender patrones de colaboración
- **Búsqueda Avanzada**: Localiza autores y trabajos por nombre, tema o afiliación
- **Optimización para Neo4j**: Consultas Cypher optimizadas para análisis de grafos

## 🔍 Casos de Uso

- **Encontrar Expertos**: Identifica investigadores especializados en áreas específicas
- **Mapear Colaboraciones**: Visualiza redes de colaboración entre diferentes autores
- **Descubrir Tendencias**: Analiza los temas más populares por año o área de estudio
- **Evaluar Producción**: Consulta métricas de productividad e impacto por investigador

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
- **🌐 Análisis de Red de Colaboración**: Visualiza comunidades de investigación

## 💻 Arquitectura del Sistema

### Componentes Principales

```
ARC/
├── data/                      # Almacenamiento de datos
│   ├── openalex_authors_complete.json   # Datos de autores
│   ├── openalex_data.json               # Datos de trabajos
│   └── works-*.csv                      # Dataset de trabajos con fecha
├── db/                        # Conexión a base de datos
│   └── db_connection.py       # Clase para conectar con Neo4j
├── extract_data/              # Scripts de extracción 
│   ├── extract_data_authors.py          # Extracción de autores
│   └── extract_data_works.py            # Extracción de trabajos
├── create_db/                 # Creación de base de datos
│   └── create_graph_author_to_articles.py  # Creación del grafo
├── main.py                    # Aplicación Streamlit
├── requirements.txt           # Dependencias
└── run.sh                     # Script de ejecución
```

### Flujo de Datos

1. **Extracción**: Se obtienen datos desde OpenAlex API
2. **Consolidación**: Se aplican algoritmos ML para unificar identidades
3. **Almacenamiento**: Se crea un grafo en Neo4j con nodos (Author, Work) y relaciones
4. **Visualización**: La interfaz Streamlit consulta la BD para presentar información

## 🧠 Algoritmo de Consolidación de Identidad

El corazón del sistema es un algoritmo sofisticado para consolidar identidades de autores:

1. **Vectorización TF-IDF de nombres**: Comparación eficiente de nombres y variantes
2. **Agrupamiento DBSCAN**: Identifica clusters de autores potencialmente duplicados
3. **Análisis Multicriterio**: Combina información de ORCIDs, afiliaciones y trabajos compartidos
4. **Selección de Identidad Principal**: Elige el perfil más completo para cada autor
5. **Fusión de Metadatos**: Consolida información para crear perfiles unificados

## 📊 Resultados y Visualizaciones

### Estadísticas del Grafo

La aplicación muestra métricas clave del grafo académico:

- Total de autores y trabajos
- Relaciones de autoría
- Densidad de colaboración
- Distribución temporal de publicaciones

### Visualizaciones Avanzadas

- **Redes de Colaboración**: Grafos interactivos que muestran comunidades de investigación
- **Distribución Temporal**: Evolución de publicaciones por año
- **Análisis de Palabras Clave**: Visualización de temas predominantes

## 🔮 Roadmap y Extensiones Futuras

- **Análisis de Sentimientos**: Evaluar la recepción de trabajos académicos
- **Predicción de Colaboraciones**: Sugerir posibles colaboradores basado en intereses
- **Integración con Más Fuentes**: Scopus, Web of Science, Google Scholar
- **Métricas Avanzadas**: Índice h, g-index y otras métricas de impacto académico
- **Visualización Geoespacial**: Mapear colaboraciones internacionales

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Proceso para colaborar:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/amazing-feature`)
3. Commitea tus cambios (`git commit -m 'Add some amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.

## 👤 Contacto

Alberto E. Marichal Fonseca - <marichalalberto292@gmail.com>

---

<div align="center">
  <p>Desarrollado con ❤️ para la comunidad de investigación académica de la Universidad de La Habana</p>
</div>
