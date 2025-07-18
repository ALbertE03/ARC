#!/usr/bin/env python3
"""
Key-Key Graph Construction

This module creates a graph where keywords are nodes and edges connect 
keywords that appear together in the same article. The graph represents 
co-occurrence relationships between keywords across the academic corpus.
"""

import json
import networkx as nx
from itertools import combinations
from collections import defaultdict, Counter
import pandas as pd
import argparse
import os


def load_articles_data(file_path):
    """
    Load articles data from JSON file.
    
    Args:
        file_path (str): Path to the JSON file containing articles data
        
    Returns:
        dict: Articles data with article IDs as keys
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Loaded data for {len(data)} articles")
        return data
    except Exception as e:
        print(f"Error loading data from {file_path}: {e}")
        return {}


def clean_keyword(keyword):
    """
    Clean and normalize a keyword.
    
    Args:
        keyword (str): Raw keyword string
        
    Returns:
        str: Cleaned keyword
    """
    # Convert to lowercase and strip whitespace
    cleaned = keyword.lower().strip()
    
    # Remove common prefixes/suffixes that might create duplicates
    # You can expand this based on your specific needs
    cleaned = cleaned.replace(' -', '').replace('- ', '')
    
    return cleaned


def extract_keyword_cooccurrences(articles_data):
    """
    Extract keyword co-occurrences from articles data.
    
    Args:
        articles_data (dict): Articles data
        
    Returns:
        tuple: (keyword_pairs_count, keyword_frequencies, article_keywords)
    """
    keyword_pairs_count = defaultdict(int)
    keyword_frequencies = Counter()
    article_keywords = {}
    
    articles_with_keywords = 0
    total_articles = len(articles_data)
    
    for article_id, article_data in articles_data.items():
        keywords = article_data.get('keywords', [])
        
        if not keywords:
            continue
            
        # Clean keywords
        cleaned_keywords = [clean_keyword(kw) for kw in keywords if kw.strip()]
        
        # Remove empty keywords and duplicates while preserving order
        unique_keywords = []
        seen = set()
        for kw in cleaned_keywords:
            if kw and kw not in seen:
                unique_keywords.append(kw)
                seen.add(kw)
        
        if len(unique_keywords) < 2:
            continue
            
        article_keywords[article_id] = unique_keywords
        articles_with_keywords += 1
        
        # Count individual keyword frequencies
        for keyword in unique_keywords:
            keyword_frequencies[keyword] += 1
        
        # Generate all pairs of keywords for this article
        for kw1, kw2 in combinations(unique_keywords, 2):
            # Sort to ensure consistent ordering (kw1, kw2) = (kw2, kw1)
            pair = tuple(sorted([kw1, kw2]))
            keyword_pairs_count[pair] += 1
    
    print(f"Articles with keywords: {articles_with_keywords}/{total_articles}")
    print(f"Total unique keywords: {len(keyword_frequencies)}")
    print(f"Total keyword pairs: {len(keyword_pairs_count)}")
    
    return keyword_pairs_count, keyword_frequencies, article_keywords


def create_keyword_graph(keyword_pairs_count, keyword_frequencies, min_frequency=1, min_cooccurrence=1):
    """
    Create a NetworkX graph from keyword co-occurrences.
    
    Args:
        keyword_pairs_count (dict): Dictionary of keyword pairs and their counts
        keyword_frequencies (Counter): Counter of individual keyword frequencies
        min_frequency (int): Minimum frequency for a keyword to be included
        min_cooccurrence (int): Minimum co-occurrence count for an edge
        
    Returns:
        nx.Graph: NetworkX graph with keywords as nodes and co-occurrences as edges
    """
    # Filter keywords by minimum frequency
    frequent_keywords = {kw for kw, freq in keyword_frequencies.items() if freq >= min_frequency}
    
    # Create graph
    G = nx.Graph()
    
    # Add nodes with attributes
    for keyword in frequent_keywords:
        G.add_node(keyword, frequency=keyword_frequencies[keyword])
    
    # Add edges with weights
    edges_added = 0
    for (kw1, kw2), count in keyword_pairs_count.items():
        if (count >= min_cooccurrence and 
            kw1 in frequent_keywords and 
            kw2 in frequent_keywords):
            G.add_edge(kw1, kw2, weight=count, cooccurrence=count)
            edges_added += 1
    
    print(f"Graph created with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    print(f"Filtered out {len(keyword_frequencies) - G.number_of_nodes()} keywords (freq < {min_frequency})")
    print(f"Filtered out {len(keyword_pairs_count) - edges_added} edges (cooccurrence < {min_cooccurrence})")
    
    return G


def save_graph_formats(graph, output_dir, base_name="keyword_graph"):
    """
    Save the graph in multiple formats.
    
    Args:
        graph (nx.Graph): NetworkX graph to save
        output_dir (str): Directory to save files
        base_name (str): Base name for output files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save as GraphML (preserves all attributes)
    graphml_path = os.path.join(output_dir, f"{base_name}.graphml")
    nx.write_graphml(graph, graphml_path)
    print(f"Saved GraphML format to: {graphml_path}")
    
    # Save as GML
    gml_path = os.path.join(output_dir, f"{base_name}.gml")
    nx.write_gml(graph, gml_path)
    print(f"Saved GML format to: {gml_path}")
    
    # Save edge list with weights
    edgelist_path = os.path.join(output_dir, f"{base_name}_edges.csv")
    edges_data = []
    for u, v, data in graph.edges(data=True):
        edges_data.append({
            'keyword1': u,
            'keyword2': v,
            'weight': data.get('weight', 1),
            'cooccurrence': data.get('cooccurrence', 1)
        })
    
    edges_df = pd.DataFrame(edges_data)
    edges_df.to_csv(edgelist_path, index=False)
    print(f"Saved edge list to: {edgelist_path}")
    
    # Save node list with attributes
    nodes_path = os.path.join(output_dir, f"{base_name}_nodes.csv")
    nodes_data = []
    for node, data in graph.nodes(data=True):
        nodes_data.append({
            'keyword': node,
            'frequency': data.get('frequency', 0),
            'degree': graph.degree(node),
            'clustering': nx.clustering(graph, node)
        })
    
    nodes_df = pd.DataFrame(nodes_data)
    nodes_df.to_csv(nodes_path, index=False)
    print(f"Saved node list to: {nodes_path}")


def analyze_graph(graph):
    """
    Perform basic analysis of the keyword graph.
    
    Args:
        graph (nx.Graph): NetworkX graph to analyze
        
    Returns:
        dict: Analysis results
    """
    if graph.number_of_nodes() == 0:
        return {"error": "Empty graph"}
    
    analysis = {
        'nodes': graph.number_of_nodes(),
        'edges': graph.number_of_edges(),
        'density': nx.density(graph),
        'connected_components': nx.number_connected_components(graph),
        'largest_component_size': len(max(nx.connected_components(graph), key=len)) if graph.number_of_nodes() > 0 else 0,
        'average_clustering': nx.average_clustering(graph),
        'average_degree': sum(dict(graph.degree()).values()) / graph.number_of_nodes()
    }
    
    # Most frequent keywords (highest degree)
    degrees = dict(graph.degree())
    top_keywords = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:10]
    analysis['top_keywords_by_degree'] = top_keywords
    
    # Most frequent keywords by frequency attribute
    if 'frequency' in list(graph.nodes(data=True))[0][1]:
        freq_keywords = sorted(graph.nodes(data=True), 
                             key=lambda x: x[1].get('frequency', 0), 
                             reverse=True)[:10]
        analysis['top_keywords_by_frequency'] = [(kw, data['frequency']) for kw, data in freq_keywords]
    
    return analysis


def print_analysis(analysis):
    """Print analysis results in a readable format."""
    print("\n" + "="*50)
    print("KEYWORD GRAPH ANALYSIS")
    print("="*50)
    
    if 'error' in analysis:
        print(f"Error: {analysis['error']}")
        return
    
    print(f"Nodes (keywords): {analysis['nodes']:,}")
    print(f"Edges (co-occurrences): {analysis['edges']:,}")
    print(f"Graph density: {analysis['density']:.4f}")
    print(f"Connected components: {analysis['connected_components']}")
    print(f"Largest component size: {analysis['largest_component_size']:,}")
    print(f"Average clustering coefficient: {analysis['average_clustering']:.4f}")
    print(f"Average degree: {analysis['average_degree']:.2f}")
    
    print(f"\nTop 10 keywords by degree (connections):")
    for i, (keyword, degree) in enumerate(analysis['top_keywords_by_degree'], 1):
        print(f"  {i:2d}. {keyword} ({degree} connections)")
    
    if 'top_keywords_by_frequency' in analysis:
        print(f"\nTop 10 keywords by frequency (appearances):")
        for i, (keyword, freq) in enumerate(analysis['top_keywords_by_frequency'], 1):
            print(f"  {i:2d}. {keyword} ({freq} articles)")


def main():
    """Main function to build and analyze the keyword co-occurrence graph."""
    parser = argparse.ArgumentParser(description='Build keyword co-occurrence graph from academic papers')
    parser.add_argument('--input', '-i', 
                       default='data/extract_result.json',
                       help='Input JSON file with articles data')
    parser.add_argument('--output', '-o', 
                       default='.',
                       help='Output directory for graph files')
    parser.add_argument('--min-frequency', type=int, default=1,
                       help='Minimum frequency for keywords to include')
    parser.add_argument('--min-cooccurrence', type=int, default=1,
                       help='Minimum co-occurrence count for edges')
    parser.add_argument('--name', default='keyword_graph',
                       help='Base name for output files')
    
    args = parser.parse_args()
    
    print("Building keyword co-occurrence graph...")
    print(f"Input file: {args.input}")
    print(f"Output directory: {args.output}")
    print(f"Min keyword frequency: {args.min_frequency}")
    print(f"Min co-occurrence count: {args.min_cooccurrence}")
    
    # Load data
    articles_data = load_articles_data(args.input)
    if not articles_data:
        print("No data loaded. Exiting.")
        return
    
    # Extract co-occurrences
    keyword_pairs_count, keyword_frequencies, article_keywords = extract_keyword_cooccurrences(articles_data)
    
    # Create graph
    graph = create_keyword_graph(keyword_pairs_count, keyword_frequencies, 
                                args.min_frequency, args.min_cooccurrence)
    
    # Analyze graph
    analysis = analyze_graph(graph)
    print_analysis(analysis)
    
    # Save graph
    save_graph_formats(graph, args.output, args.name)
    
    print(f"\nKeyword graph construction completed!")
    print(f"Files saved in: {args.output}")


if __name__ == "__main__":
    main()