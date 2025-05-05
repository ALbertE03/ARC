#!/bin/bash

set -e  

echo "====================================================="
echo "    Starting pipeline     "
echo "====================================================="


echo "Creating necessary directories..."
mkdir -p data
mkdir -p db



if [ ! -f .env ]; then
    echo ".env file not found, creating an example one..."
    echo "⚠️  ATTENTION: Please update your .env file with your Neo4j credentials"
    exit 1
fi


echo "Verifying requirements..."
if ! [ -f "requirements.txt" ]; then
    echo "❌ requirements.txt file not found"
    exit 1
fi


if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi


echo "Activating virtual environment..."
source venv/bin/activate


echo "Installing dependencies..."
pip install -r requirements.txt


echo ""
echo "====================================================="
echo "    Phase 1: Extracting article data         "
echo "====================================================="
if [ ! -f "data/works-2025-05-01T01-14-16.csv" ]; then
    echo "❌ Initial works CSV file not found"
    echo "Please make sure you have the 'works-2025-05-01T01-14-16.csv' file in the 'data' folder"
    exit 1
fi

echo "Executing article data extraction..."
python extract_data/extract_data_works.py


echo ""
echo "====================================================="
echo "    Phase 2: Extracting author data           "
echo "====================================================="
if [ ! -f "data/openalex_data.json" ]; then
    echo "❌ Works JSON file not found"
    echo "Make sure that Phase 1 completed successfully"
    exit 1
fi

echo "Executing author data extraction..."
python extract_data/extract_data_authors.py


echo ""
echo "====================================================="
echo "    Phase 3: Creating graph database   "
echo "====================================================="
if [ ! -f "data/openalex_authors_complete.json" ]; then
    echo "❌ Authors JSON file not found"
    echo "Make sure that Phase 2 completed successfully"
    exit 1
fi

echo "Executing graph database creation..."
python create_db/create_graph_author_to_articles.py

echo ""
echo "====================================================="
echo "         Pipeline completed successfully               "
echo "====================================================="
echo "Data processed and ready to use."

echo ""
echo "For more information, check the README.md file"
python streamlit run main.py