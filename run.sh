#!/bin/bash

# Script para automatizar el pipeline completo del proyecto
# Autor: Alberto E Marichal Fonnseca
# Fecha: 2025-05-04

set -e  # Detener el script si hay algún error

echo "====================================================="
echo "    Iniciando pipeline     "
echo "====================================================="

# Crear directorios necesarios
echo "Creando directorios necesarios..."
mkdir -p data
mkdir -p db
mkdir -p __pycache__

# Verificar si existe el archivo .env
if [ ! -f .env ]; then
    echo "Archivo .env no encontrado, creando uno de ejemplo..."
    echo "URL=neo4j+s://xxxxxxxx.databases.neo4j.io" > .env
    echo "USER_NEO=neo4j" >> .env
    echo "PASS_NEO=contraseña" >> .env
    echo ""
    echo "⚠️  ATENCIÓN: Por favor, actualiza tu archivo .env con tus credenciales de Neo4j"
    read -p "Presiona Enter para continuar después de actualizar el archivo .env, o Ctrl+C para cancelar..."
fi

# Verificar requisitos
echo "Verificando requisitos..."
if ! [ -f "requirements.txt" ]; then
    echo "❌ No se encontró el archivo requirements.txt"
    exit 1
fi

# Verificar y crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "Instalando dependencias..."
pip install -r requirements.txt

# Fase 1: Extracción de datos de artículos
echo ""
echo "====================================================="
echo "    Fase 1: Extracción de datos de artículos         "
echo "====================================================="
if [ ! -f "data/works-2025-05-01T01-14-16.csv" ]; then
    echo "❌ No se encontró el archivo CSV de trabajos inicial"
    echo "Por favor, asegúrate de tener el archivo 'works-2025-05-01T01-14-16.csv' en la carpeta 'data'"
    exit 1
fi

echo "Ejecutando extracción de datos de artículos..."
python extract_data/extract_data_works.py

# Fase 2: Extracción de datos de autores
echo ""
echo "====================================================="
echo "    Fase 2: Extracción de datos de autores           "
echo "====================================================="
if [ ! -f "data/openalex_data.json" ]; then
    echo "❌ No se encontró el archivo JSON de trabajos"
    echo "Asegúrate de que la Fase 1 se haya completado correctamente"
    exit 1
fi

echo "Ejecutando extracción de datos de autores..."
python extract_data/extract_data_authors.py

# Fase 3: Creación de la base de datos de grafos
echo ""
echo "====================================================="
echo "    Fase 3: Creación de la base de datos de grafos   "
echo "====================================================="
if [ ! -f "data/openalex_authors_complete.json" ]; then
    echo "❌ No se encontró el archivo JSON de autores"
    echo "Asegúrate de que la Fase 2 se haya completado correctamente"
    exit 1
fi

echo "Ejecutando creación de la base de datos de grafos..."
python create_db/create_graph_author_to_articles.py

echo ""
echo "====================================================="
echo "         Pipeline completado con éxito               "
echo "====================================================="
echo "Datos procesados y listos para ser utilizados."

# Desactivar entorno virtual
deactivate

echo ""
echo "Para más información, consulta el archivo README.md"