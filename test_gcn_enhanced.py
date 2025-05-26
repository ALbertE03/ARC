#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for enhanced GCN author matcher with preprocessing.
This script demonstrates how to use the GCN model with separate author and paper JSON files.
"""

import os
import logging
import networkx as nx
import matplotlib.pyplot as plt
from models.GCN import create_gcn_matcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    """Run the GCN test with preprocessing."""
    # File paths to data
    current_dir = os.path.dirname(os.path.abspath(__file__))
    authors_path = os.path.join(current_dir, 'data', 'openalex_authors_complete.json')
    papers_path = os.path.join(current_dir, 'data', 'openalex_data.json')
    
    # Check if files exist
    if not os.path.exists(authors_path):
        logger.error(f"Authors file not found: {authors_path}")
        return
    if not os.path.exists(papers_path):
        logger.error(f"Papers file not found: {papers_path}")
        return
    
    # Create GCN matcher with appropriate parameters
    gcn_matcher = create_gcn_matcher(
        embedding_dim=128,
        hidden_dims=[64, 32],
        learning_rate=0.005,
        margin=0.3,
        device='cpu'  # Use 'cuda' if GPU is available
    )
    
    # Run the GCN-based author consolidation
    # Using the improved method with direct file paths
    result_graph = gcn_matcher.find_candidates(
        authors_data_path=authors_path,
        papers_data_path=papers_path
    )
    
    # Display results
    logger.info(f"GCN consolidation result: {result_graph.number_of_nodes()} nodes, {result_graph.number_of_edges()} edges")
    
    # Save consolidated authors to file
    save_consolidation_results(result_graph)
    
    # Visualize the graph if it's small enough
    if result_graph.number_of_nodes() < 100:
        visualize_graph(result_graph)
    else:
        logger.info(f"Graph too large to visualize ({result_graph.number_of_nodes()} nodes)")

def save_consolidation_results(graph):
    """Save consolidation results to file."""
    if not graph or graph.number_of_edges() == 0:
        logger.warning("No consolidation results to save")
        return
        
    try:
        # Create connected components (clusters of potentially same authors)
        components = list(nx.connected_components(graph))
        
        # Sort by size (number of authors in the cluster)
        components = sorted(components, key=len, reverse=True)
        
        # Save to file
        with open('gcn_consolidation_results.txt', 'w') as f:
            f.write(f"GCN Consolidation Results\n")
            f.write(f"Total author clusters: {len(components)}\n\n")
            
            for i, component in enumerate(components):
                if len(component) > 1:  # Only save clusters with multiple authors
                    f.write(f"Cluster {i+1} ({len(component)} authors):\n")
                    for author_id in component:
                        author_data = graph.nodes[author_id]
                        name = author_data.get('name', author_id)
                        institution = author_data.get('institution', 'Unknown')
                        f.write(f"  - {name} ({institution})\n")
                    f.write("\n")
        
        logger.info(f"Saved {len(components)} author clusters to gcn_consolidation_results.txt")
    except Exception as e:
        logger.error(f"Error saving consolidation results: {e}")

def visualize_graph(graph):
    """Visualize the author consolidation graph."""
    try:
        plt.figure(figsize=(10, 8))
        
        # Use spring layout for visualization
        pos = nx.spring_layout(graph)
        
        # Draw nodes
        nx.draw_networkx_nodes(graph, pos, node_size=100, alpha=0.7)
        
        # Draw edges
        nx.draw_networkx_edges(graph, pos, alpha=0.4)
        
        # Draw labels (use short names or IDs for clarity)
        labels = {}
        for node in graph.nodes():
            node_data = graph.nodes[node]
            name = node_data.get('name', '')
            if name:
                # Use only first name and last initial for label clarity
                name_parts = name.split()
                if len(name_parts) > 1:
                    labels[node] = f"{name_parts[0]} {name_parts[-1][0]}."
                else:
                    labels[node] = name
            else:
                # Use last part of ID if no name
                labels[node] = node.split('/')[-1]
        
        nx.draw_networkx_labels(graph, pos, labels=labels, font_size=8)
        
        plt.title('Author Consolidation Graph')
        plt.axis('off')
        plt.tight_layout()
        
        # Save to file
        plt.savefig('gcn_consolidation_graph.png', dpi=300)
        logger.info("Graph visualization saved to gcn_consolidation_graph.png")
        
    except Exception as e:
        logger.error(f"Error visualizing graph: {e}")

if __name__ == "__main__":
    main()
