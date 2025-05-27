#!/bin/bash

set -e  

# =============================================================================
# CONFIGURATION SECTION - Modify these variables to change behavior
# =============================================================================

# Author Matcher Configuration
# EXHAUSTIVE_MODE: true = exhaustive N×N comparison (slower, more accurate)
#                  false = batch-optimized comparison (faster, good accuracy)
EXHAUSTIVE_MODE=true

# Similarity threshold for author matching (0.0 to 1.0)
SIMILARITY_THRESHOLD=0.95

# Additional flags for the author matching process
# Uncomment any of these to enable specific features:
# MATCHER_FLAGS="--benchmark"                    # Run benchmark comparison
# MATCHER_FLAGS="--limit 1000"                  # Test with limited dataset
# MATCHER_FLAGS="--export-results"              # Export detailed metrics
# MATCHER_FLAGS="--skip-neo4j"                  # Skip database insertion
MATCHER_FLAGS=""

# =============================================================================

echo "====================================================="
echo "    Starting Enhanced ARC Pipeline     "
echo "====================================================="
echo "Configuration:"
if [ "$EXHAUSTIVE_MODE" = true ]; then
    echo "  🔍 Mode: Exhaustive N×N comparison (maximum accuracy)"
else
    echo "  🚀 Mode: Batch-optimized comparison (faster processing)"
fi
echo "  📊 Similarity threshold: $SIMILARITY_THRESHOLD"
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
# Build the command with the configured options
PYTHON_CMD="python create_db/create_graph_author_to_articles.py --threshold $SIMILARITY_THRESHOLD"

# Add exhaustive mode configuration
if [ "$EXHAUSTIVE_MODE" = false ]; then
    PYTHON_CMD="$PYTHON_CMD --no-exhaustive"
fi

# Add any additional flags
if [ ! -z "$MATCHER_FLAGS" ]; then
    PYTHON_CMD="$PYTHON_CMD $MATCHER_FLAGS"
fi

echo "Running: $PYTHON_CMD"
echo "📋 Enhanced Author Matcher Configuration:"
if [ "$EXHAUSTIVE_MODE" = true ]; then
    echo "   🔍 Exhaustive N×N comparison (maximum accuracy)"
else
    echo "   🚀 Batch-optimized comparison (faster processing)"
fi
echo "   📊 Similarity threshold: $SIMILARITY_THRESHOLD"
echo ""

# Execute the command
eval $PYTHON_CMD

echo ""
echo "====================================================="
echo "     Enhanced ARC Pipeline Completed Successfully     "
echo "====================================================="
echo "✅ Data processed with Enhanced Author Matcher"
if [ "$EXHAUSTIVE_MODE" = true ]; then
    echo "🔍 Used exhaustive N×N comparison for maximum accuracy"
else
    echo "🚀 Used batch-optimized comparison for faster processing"
fi
echo "📊 Similarity threshold: $SIMILARITY_THRESHOLD"
echo "🎯 Data ready for analysis and visualization"
echo ""
echo "🚀 Starting Streamlit dashboard..."
echo "For more information, check the README.md file"
streamlit run main.py