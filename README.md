# ARC - Academic Research Connections

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.11-green)
![Neo4j](https://img.shields.io/badge/Neo4j-5.x-orange)

## 📚 Descripción

ARC (Academic Research Connections) es una herramienta diseñada para extraer, procesar y analizar datos académicos de OpenAlex utilizando una base de datos de grafos Neo4j. Este proyecto permite visualizar y explorar las conexiones entre autores y sus publicaciones científicas de la Universidad de La Habana, facilitando el análisis de colaboraciones académicas y tendencias de investigación en la institución.

## 🚀 Características

- Extracción automática de datos de artículos académicos de la Universidad de La Habana desde OpenAlex
- Procesamiento de datos de autores y sus conexiones dentro del ecosistema universitario
- Almacenamiento en base de datos de grafos Neo4j para análisis de relaciones
- Pipeline automatizado para todo el proceso de ETL
- Visualización de redes de colaboración académica entre investigadores de la UH

## 🛠️ Requisitos del Sistema

- Python 3.11 o superior
- Neo4j Database
- Cuenta en OpenAlex (opcional para algunas características avanzadas)
- Espacio en disco para almacenar datasets (mínimo 1GB recomendado)

## ⚙️ Instalación

1. Clona este repositorio:

   ```
   git clone [URL-del-repositorio]
   cd ARC
   ```

2. Crea y activa un entorno virtual:

   ```
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instala las dependencias:

   ```
   pip install -r requirements.txt
   ```

4. Configura las credenciales:

   ```
   cp .env.example .env
   ```

   Edita el archivo `.env` con tus credenciales de Neo4j.

## 📋 Uso

### Ejecución del Pipeline Completo

Para ejecutar todo el proceso de extracción, procesamiento y carga de datos:

```bash
./run.sh
```

Este script realizará de forma automática:

1. Extracción de datos de artículos
2. Extracción y procesamiento de datos de autores
3. Creación de la base de datos de grafos en Neo4j

### Ejecución por Fases

Si prefieres ejecutar cada fase por separado:

1. **Extracción de datos de artículos**:

   ```
   python extract_data/extract_data_works.py
   ```

2. **Extracción de datos de autores**:

   ```
   python extract_data/extract_data_authors.py
   ```

3. **Creación de la base de datos**:

   ```
   python create_db/create_graph_author_to_articles.py
   ```

## 🗄️ Estructura del Proyecto

```
├── README.md              # Este archivo
├── requirements.txt       # Dependencias del proyecto
├── run.sh                 # Script para ejecutar el pipeline completo
├── create_db/             # Scripts para crear la base de datos
├── data/                  # Directorio para almacenar los datos extraídos
├── db/                    # Módulos de conexión a la base de datos
└── extract_data/          # Scripts de extracción de datos
```

## 🔄 Flujo de Trabajo

1. Los datos iniciales de artículos de la Universidad de La Habana se procesan desde archivos CSV
2. Se extraen metadatos de artículos y se almacenan en formato JSON
3. Se procesan datos de autores y sus relaciones
4. Se carga la información en Neo4j creando nodos y relaciones
5. Los datos quedan listos para consultas y análisis de grafos sobre la producción científica de la UH

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, sigue estos pasos:

1. Haz fork del repositorio
2. Crea una rama para tu característica (`git checkout -b feature/amazing-feature`)
3. Haz commit de tus cambios (`git commit -m 'Add some amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.

## 📞 Contacto

Alberto E Marichal Fonseca - <marichalalberto292@gmail.com>

---

Desarrollado con ❤️ para la comunidad de investigación académica de la Universidad de La Habana.
