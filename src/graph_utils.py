"""
Utilidades adicionales para la aplicación Streamlit
"""

import pandas as pd
import numpy as np
import networkx as nx
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import community as community_louvain
from collections import defaultdict
import json
import plotly.express as px


def hex_to_rgba(hex_color, alpha=1.0):
    """Convierte color hexadecimal a formato rgba"""
    if not hex_color.startswith('#'):
        return f'rgba(125,125,125,{alpha})'
    
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)  
        b = int(hex_color[5:7], 16)
        return f'rgba({r},{g},{b},{alpha})'
    except (ValueError, IndexError):
        return f'rgba(125,125,125,{alpha})'


class GraphAnalyzer:
    """Clase para análisis avanzado del grafo"""
    
    def __init__(self, graph):
        self.graph = graph.graph
        
    def detect_communities(self, method='louvain', weight_threshold=None, resolution=1.0):
        """Detecta comunidades en el grafo con diferentes métodos basados en peso
        
        Args:
            method: 'louvain', 'leiden', 'weighted_louvain', 'edge_betweenness', 'girvan_newman'
            weight_threshold: Umbral mínimo de peso para considerar las aristas
            resolution: Parámetro de resolución para algoritmos de modularidad
        """
        try:
            G = self.graph
            if weight_threshold is not None:
                G = self._filter_by_weight(G, weight_threshold)
            
            if method == 'louvain':
                partition = community_louvain.best_partition(G, resolution=resolution)
            elif method == 'weighted_louvain':
                partition = community_louvain.best_partition(G, weight='weight', resolution=resolution)
            elif method == 'leiden':
                partition = self._leiden_communities(G, resolution)
            elif method == 'edge_betweenness':
                partition = self._edge_betweenness_communities(G)
            elif method == 'girvan_newman':
                partition = self._girvan_newman_communities(G)
            elif method == 'strong_ties':
                partition = self._strong_ties_communities(G)
            elif method == 'weak_ties':
                partition = self._weak_ties_communities(G)
            else:
                partition = community_louvain.best_partition(G, resolution=resolution)
            
            return partition
        except Exception as e:
            print(f"Error en detección de comunidades: {e}")
            return {}
    
    def _filter_by_weight(self, graph, threshold):
        """Filtra el grafo por peso mínimo de aristas"""
        G = graph.copy()
        edges_to_remove = []
        for u, v, data in G.edges(data=True):
            weight = data.get('weight', 1)
            if weight < threshold:
                edges_to_remove.append((u, v))
        
        G.remove_edges_from(edges_to_remove)
        return G
    
    def _leiden_communities(self, graph, resolution=1.0):
        """Algoritmo de Leiden para detección de comunidades"""
        try:
            import leidenalg
            import igraph as ig
            
            g = ig.Graph.from_networkx(graph)
            
            partition = leidenalg.find_partition(g, leidenalg.ModularityVertexPartition, 
                                               resolution_parameter=resolution)
            communities = {}
            for i, community in enumerate(partition):
                for node in community:
                    communities[list(graph.nodes())[node]] = i
            
            return communities
        except ImportError:
            print("Leiden requiere las librerías 'leidenalg' e 'igraph-python'")
            return community_louvain.best_partition(graph, resolution=resolution)
    
    def _edge_betweenness_communities(self, graph):
        """Detección de comunidades basada en edge betweenness"""
        try:
            communities = nx.community.girvan_newman(graph)
            partition = next(communities)

            result = {}
            for i, community in enumerate(partition):
                for node in community:
                    result[node] = i
            
            return result
        except:
            return community_louvain.best_partition(graph)
    
    def _girvan_newman_communities(self, graph):
        """Algoritmo de Girvan-Newman para detección de comunidades"""
        try:
            communities = nx.community.girvan_newman(graph)

            best_partition = None
            best_modularity = -1
            
            for partition in communities:
                modularity = nx.community.modularity(graph, partition)
                if modularity > best_modularity:
                    best_modularity = modularity
                    best_partition = partition

                if len(partition) > 10:
                    break
            
            if best_partition:
                result = {}
                for i, community in enumerate(best_partition):
                    for node in community:
                        result[node] = i
                return result
            
            return community_louvain.best_partition(graph)
        except:
            return community_louvain.best_partition(graph)
    
    def _strong_ties_communities(self, graph):
        """Detección de comunidades basada solo en lazos fuertes (peso >= 3)"""
        strong_graph = self._filter_by_weight(graph, 3)
        if strong_graph.number_of_edges() == 0:
            strong_graph = self._filter_by_weight(graph, 2)
        
        return community_louvain.best_partition(strong_graph)
    
    def _weak_ties_communities(self, graph):
        """Detección de comunidades excluyendo lazos muy fuertes (peso <= 2)"""
        weak_graph = graph.copy()
        edges_to_remove = []
        for u, v, data in weak_graph.edges(data=True):
            weight = data.get('weight', 1)
            if weight > 2:
                edges_to_remove.append((u, v))
        
        weak_graph.remove_edges_from(edges_to_remove)
        return community_louvain.best_partition(weak_graph)
    
    def get_community_analysis(self, communities):
        """Analiza las comunidades detectadas"""
        if not communities:
            return {}
        
        community_stats = defaultdict(lambda: {
            'size': 0,
            'nodes': [],
            'internal_edges': 0,
            'external_edges': 0,
            'total_weight': 0,
            'avg_weight': 0,
            'modularity': 0
        })

        for node, comm_id in communities.items():
            community_stats[comm_id]['size'] += 1
            community_stats[comm_id]['nodes'].append(node)
        
        for u, v, data in self.graph.edges(data=True):
            weight = data.get('weight', 1)
            if u in communities and v in communities:
                if communities[u] == communities[v]:
                    # Arista interna
                    community_stats[communities[u]]['internal_edges'] += 1
                    community_stats[communities[u]]['total_weight'] += weight
                else:
                    # Arista externa
                    community_stats[communities[u]]['external_edges'] += 1
                    community_stats[communities[v]]['external_edges'] += 1
        
        for comm_id in community_stats:
            if community_stats[comm_id]['internal_edges'] > 0:
                community_stats[comm_id]['avg_weight'] = (
                    community_stats[comm_id]['total_weight'] / 
                    community_stats[comm_id]['internal_edges']
                )
        

        partition = []
        for comm_id in set(communities.values()):
            partition.append(community_stats[comm_id]['nodes'])
        
        try:
            modularity = nx.community.modularity(self.graph, partition)
        except:
            modularity = 0
        
        return {
            'communities': dict(community_stats),
            'num_communities': len(community_stats),
            'modularity': modularity,
            'largest_community': max(community_stats.keys(), 
                                   key=lambda x: community_stats[x]['size']) if community_stats else None
        }
    
    def get_centrality_measures(self):
        """Calcula medidas de centralidad"""
        try:
            measures = {
                'degree_centrality': nx.degree_centrality(self.graph),
                'betweenness_centrality': nx.betweenness_centrality(self.graph),
                'closeness_centrality': nx.closeness_centrality(self.graph),
                'eigenvector_centrality': nx.eigenvector_centrality(self.graph, max_iter=1000)
            }
            return measures
        except:
            return {}
    
    def get_collaboration_patterns(self):
        """Analiza patrones de colaboración"""
        patterns = {
            'total_collaborations': self.graph.number_of_edges(),
            'avg_collaborations': np.mean([d for n, d in self.graph.degree()]),
            'collaboration_distribution': dict(self.graph.degree()),
            'strong_collaborations': [],
            'weak_collaborations': []
        }
        
        for u, v, data in self.graph.edges(data=True):
            weight = data.get('weight', 1)
            if weight >= 3:
                patterns['strong_collaborations'].append((u, v, weight))
            elif weight == 1:
                patterns['weak_collaborations'].append((u, v, weight))
        
        return patterns
    
    def get_author_recommendations(self, author_name, top_n=5):
        """Sugiere colaboradores potenciales para un autor"""
        author_node = None
        for node, data in self.graph.nodes(data=True):
            if author_name.lower() in [name.lower() for name in data.get('all_names', [])]:
                author_node = node
                break
        
        if not author_node:
            return []
        
        current_collaborators = set(self.graph.neighbors(author_node))

        second_degree = set()
        for collaborator in current_collaborators:
            for second_collab in self.graph.neighbors(collaborator):
                if second_collab != author_node and second_collab not in current_collaborators:
                    second_degree.add(second_collab)
        
        recommendations = []
        for candidate in second_degree:
            mutual_connections = len(set(self.graph.neighbors(candidate)) & current_collaborators)
            
            candidate_data = self.graph.nodes[candidate]
            paper_count = candidate_data.get('paper_count', 0)

            score = mutual_connections * 2 + paper_count * 0.1
            
            recommendations.append({
                'name': candidate_data.get('name', 'Desconocido'),
                'mutual_connections': mutual_connections,
                'paper_count': paper_count,
                'score': score
            })
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:top_n]


class ModelMetrics:
    """Clase para métricas detalladas del modelo"""
    
    def __init__(self, performance_stats):
        self.stats = performance_stats
        
    def calculate_confusion_matrix(self):
        """Calcula matriz de confusión basada en casos con decisión manual"""
        if 'difficult_cases_data' not in self.stats:
            return None
        
        tp = fp = tn = fn = 0
        
        for case in self.stats['difficult_cases_data']:
            if 'manual_decision' in case:
                model_pred = case['prediction']
                manual_decision = case['manual_decision']
                
                if model_pred and manual_decision:
                    tp += 1
                elif model_pred and not manual_decision:
                    fp += 1
                elif not model_pred and manual_decision:
                    fn += 1
                else:
                    tn += 1
        
        return {
            'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
            'precision': tp / (tp + fp) if (tp + fp) > 0 else 0,
            'recall': tp / (tp + fn) if (tp + fn) > 0 else 0,
            'accuracy': (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
        }
    



def create_advanced_graph_visualization(graph, communities=None, centrality_measure=None,max_nodes=200):
    """Crea visualización avanzada del grafo con comunidades y centralidad"""
    G = graph.graph
    
    if G.number_of_nodes() > max_nodes:
        degrees = dict(G.degree())
        top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
        G = G.subgraph([node for node, degree in top_nodes])
    
    pos = nx.spring_layout(G, k=2, iterations=50)

    if communities:
        community_colors = {}
        unique_communities = set(communities.values())
        colors = px.colors.qualitative.Set3[:len(unique_communities)]
        for i, comm in enumerate(unique_communities):
            community_colors[comm] = colors[i % len(colors)]
    
    edge_trace = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        weight = G[edge[0]][edge[1]].get('weight', 1)
        
        edge_trace.append(go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=min(weight * 0.5, 5), color='rgba(125,125,125,0.3)'),
            hoverinfo='none',
            showlegend=False
        ))
    
    node_x = []
    node_y = []
    node_text = []
    node_size = []
    node_color = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        node_data = G.nodes[node]
        name = node_data.get('name', 'Desconocido')
        paper_count = node_data.get('paper_count', 0)
        
        hover_text = f"<b>{name}</b><br>Papers: {paper_count}<br>Colaboradores: {G.degree(node)}"
        
        if centrality_measure and node in centrality_measure:
            hover_text += f"<br>Centralidad: {centrality_measure[node]:.3f}"
        
        node_text.append(hover_text)
        node_size.append(max(15, min(paper_count * 3, 60)))

        if communities and node in communities:
            node_color.append(communities[node])
        elif centrality_measure and node in centrality_measure:
            node_color.append(centrality_measure[node])
        else:
            node_color.append(paper_count)
    
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers',
        hoverinfo='text',
        text=node_text,
        marker=dict(
            size=node_size,
            color=node_color,
            colorscale='Viridis' if not communities else None,
            showscale=True if not communities else False,
            colorbar=dict(title="Centralidad" if centrality_measure else "Papers") if not communities else None,
            line=dict(width=2)
        ),
        showlegend=False
    )

    fig = go.Figure(data=edge_trace + [node_trace])
    fig.update_layout(
        title="Grafo de Colaboración",
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20,l=5,r=5,t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        height=600
    )
    
    return fig


def create_performance_dashboard(stats):
    """Crea un dashboard completo de rendimiento"""
    if not stats or 'predictions_data' not in stats:
        return None
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Distribución de Probabilidades', 'Evolución Temporal', 
                       'Decisiones del Modelo', 'Casos Difíciles'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"type": "pie"}, {"secondary_y": False}]]
    )
    
    predictions_data = stats['predictions_data']
    probs = [p['probability'] for p in predictions_data]
    
    fig.add_trace(
        go.Histogram(x=probs, nbinsx=20, name="Probabilidades"),
        row=1, col=1
    )
    
    if len(predictions_data) > 1:
        df_preds = pd.DataFrame(predictions_data)
        df_preds['timestamp'] = pd.to_datetime(df_preds['timestamp'])
        
        fig.add_trace(
            go.Scatter(x=df_preds['timestamp'], y=df_preds['probability'], 
                      mode='lines+markers', name="Evolución"),
            row=1, col=2
        )
    
    positive_preds = sum(p['prediction'] for p in predictions_data)
    negative_preds = len(predictions_data) - positive_preds
    
    fig.add_trace(
        go.Pie(labels=['Mismo autor', 'Diferente autor'], 
               values=[positive_preds, negative_preds]),
        row=2, col=1
    )

    difficult_cases = stats.get('difficult_cases_data', [])
    if difficult_cases:
        diff_probs = [p['probability'] for p in difficult_cases]
        fig.add_trace(
            go.Scatter(x=list(range(len(diff_probs))), y=diff_probs, 
                      mode='markers', name="Casos Difíciles", 
                      marker=dict(color='red', size=10)),
            row=2, col=2
        )
    
    fig.update_layout(height=800, showlegend=False)
    
    return fig


def create_community_comparison_visualization(graph, communities_dict):
    """Crea visualización comparativa de diferentes métodos de detección de comunidades"""
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=list(communities_dict.keys()),
        specs=[[{"type": "scatter"}, {"type": "scatter"}],
               [{"type": "scatter"}, {"type": "scatter"}]]
    )
    
    G = graph.graph
    if G.number_of_nodes() > 150:
        degrees = dict(G.degree())
        top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:150]
        G = G.subgraph([node for node, degree in top_nodes])
    
    pos = nx.spring_layout(G, k=2, iterations=50)
    
    row_col_mapping = [(1, 1), (1, 2), (2, 1), (2, 2)]
    
    for idx, (method_name, communities) in enumerate(communities_dict.items()):
        if idx >= 4:  
            break
        
        row, col = row_col_mapping[idx]
        
        unique_communities = list(set(communities.values()))
        colors = px.colors.qualitative.Set3[:len(unique_communities)]
        color_map = {comm: colors[i % len(colors)] for i, comm in enumerate(unique_communities)}
        
        node_x = []
        node_y = []
        node_colors = []
        node_text = []
        
        for node in G.nodes():
            if node in communities:
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                
                community_id = communities[node]
                node_colors.append(color_map[community_id])
                
                node_data = G.nodes[node]
                name = node_data.get('name', 'Desconocido')
                node_text.append(f"{name}<br>Comunidad: {community_id}")
        
        fig.add_trace(
            go.Scatter(
                x=node_x,
                y=node_y,
                mode='markers',
                marker=dict(
                    color=node_colors,
                    size=8,
                    line=dict(width=1, color='black')
                ),
                text=node_text,
                hoverinfo='text',
                showlegend=False,
                name=method_name
            ),
            row=row, col=col
        )
    
    fig.update_layout(
        title="Comparación de Métodos de Detección de Comunidades",
        height=800,
        showlegend=False
    )
    
    for i in range(1, 5):
        fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, row=(i-1)//2+1, col=(i-1)%2+1)
        fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, row=(i-1)//2+1, col=(i-1)%2+1)
    
    return fig


def create_weight_distribution_analysis(graph):
    """Analiza la distribución de pesos en las aristas del grafo"""
    
    weights = []
    for u, v, data in graph.graph.edges(data=True):
        weights.append(data.get('weight', 1))
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Distribución de Pesos', 'Pesos Acumulados', 
                       'Boxplot de Pesos', 'Pesos por Percentil'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    fig.add_trace(
        go.Histogram(x=weights, nbinsx=20, name="Frecuencia", opacity=0.7),
        row=1, col=1
    )

    weights_sorted = sorted(weights)
    cumulative = np.cumsum([1] * len(weights_sorted)) / len(weights_sorted)
    fig.add_trace(
        go.Scatter(x=weights_sorted, y=cumulative, mode='lines', name="Acumulado"),
        row=1, col=2
    )

    fig.add_trace(
        go.Box(y=weights, name="Pesos", boxpoints='outliers'),
        row=2, col=1
    )

    percentiles = [10, 25, 50, 75, 90, 95, 99]
    percentile_values = [np.percentile(weights, p) for p in percentiles]
    fig.add_trace(
        go.Bar(x=[f"P{p}" for p in percentiles], y=percentile_values, name="Percentiles"),
        row=2, col=2
    )
    
    fig.update_layout(
        title="Análisis de Distribución de Pesos de Aristas",
        height=600,
        showlegend=False
    )
    
    return fig, {
        'min_weight': min(weights),
        'max_weight': max(weights),
        'mean_weight': np.mean(weights),
        'median_weight': np.median(weights),
        'std_weight': np.std(weights),
        'total_edges': len(weights)
    }

from src.build_keywords_graph import KeywordGraph
class KeywordAnalyzer:
    """Analizador para el grafo de palabras clave y conexiones autor-keyword"""
    
    def __init__(self, keywords_graph_path='keywords_graph.graphml'):
        """Inicializa el analizador cargando el grafo de keywords"""
        try:
            self.keywords_graph = nx.read_graphml(keywords_graph_path)
            self._convert_strings_to_lists()
        except Exception as e:
            print(f"Error cargando grafo de keywords: {e}")
            g = KeywordGraph('../data/extract_result.json')
            g.build()
            g.save()
            self.keywords_graph = nx.read_graphml(keywords_graph_path)
    
    def _convert_strings_to_lists(self):
        """Convierte strings separados por comas de vuelta a listas"""
        for node, data in self.keywords_graph.nodes(data=True):
            for key, value in data.items():
                if key in ['original_forms', 'papers'] and isinstance(value, str):
                    data[key] = [item.strip() for item in value.split(',') if item.strip()]
        
        for u, v, data in self.keywords_graph.edges(data=True):
            for key, value in data.items():
                if key == 'papers' and isinstance(value, str):
                    data[key] = [item.strip() for item in value.split(',') if item.strip()]
    
    def get_keyword_statistics(self):
        """Obtiene estadísticas generales de las palabras clave"""
        if not self.keywords_graph:
            return None
        
        keyword_nodes = [n for n, d in self.keywords_graph.nodes(data=True) if d.get('type') == 'keyword']
        author_nodes = [n for n, d in self.keywords_graph.nodes(data=True) if d.get('type') == 'author']

        keyword_frequencies = []
        for node in keyword_nodes:
            data = self.keywords_graph.nodes[node]
            keyword_frequencies.append({
                'keyword': node,
                'frequency': data.get('frequency', 0),
                'papers': len(data.get('papers', [])),
                'author_connections': len([n for n in self.keywords_graph.neighbors(node) 
                                         if self.keywords_graph.nodes[n].get('type') == 'author'])
            })
        
        keyword_frequencies.sort(key=lambda x: x['frequency'], reverse=True)
        
        cooccurrence_edges = [(u, v, d) for u, v, d in self.keywords_graph.edges(data=True) 
                             if d.get('type') == 'keyword_cooccurrence']
        
        top_cooccurrences = sorted(cooccurrence_edges, key=lambda x: x[2].get('weight', 0), reverse=True)[:20]
        
        return {
            'total_keywords': len(keyword_nodes),
            'total_authors': len(author_nodes),
            'total_connections': self.keywords_graph.number_of_edges(),
            'keyword_frequencies': keyword_frequencies,
            'top_cooccurrences': top_cooccurrences,
            'avg_keyword_frequency': sum(kf['frequency'] for kf in keyword_frequencies) / len(keyword_frequencies) if keyword_frequencies else 0
        }
    
    def get_author_keyword_analysis(self, top_n=20):
        """Analiza las conexiones entre autores y palabras clave"""
        if not self.keywords_graph:
            return None
        
        author_keyword_data = []
        
        for node, data in self.keywords_graph.nodes(data=True):
            if data.get('type') == 'author':
                connected_keywords = []
                for neighbor in self.keywords_graph.neighbors(node):
                    if self.keywords_graph.nodes[neighbor].get('type') == 'keyword':
                        edge_data = self.keywords_graph.edges[node, neighbor]
                        connected_keywords.append({
                            'keyword': neighbor,
                            'weight': edge_data.get('weight', 1),
                            'papers': edge_data.get('papers', [])
                        })
                
                connected_keywords.sort(key=lambda x: x['weight'], reverse=True)
                
                author_keyword_data.append({
                    'author': data.get('name', 'Unknown'),
                    'total_keywords': len(connected_keywords),
                    'top_keywords': connected_keywords[:5],  
                    'papers_count': len(data.get('papers', [])),
                    'keyword_diversity': len(set(kw['keyword'] for kw in connected_keywords))
                })
        
        author_keyword_data.sort(key=lambda x: x['keyword_diversity'], reverse=True)
        
        return author_keyword_data[:top_n]
    
    def get_keyword_clusters(self):
        """Identifica clusters de palabras clave basados en co-ocurrencia"""
        if not self.keywords_graph:
            return None

        keyword_nodes = [n for n, d in self.keywords_graph.nodes(data=True) if d.get('type') == 'keyword']
        keyword_subgraph = self.keywords_graph.subgraph(keyword_nodes).copy()
        
        try:
            import networkx.algorithms.community as nx_comm
            communities = nx_comm.louvain_communities(keyword_subgraph, weight='weight')
            
            clusters = []
            for i, community in enumerate(communities):
                if len(community) > 1:  
                    cluster_keywords = list(community)

                    cluster_edges = keyword_subgraph.subgraph(cluster_keywords).edges(data=True)
                    avg_weight = sum(d.get('weight', 1) for u, v, d in cluster_edges) / len(cluster_edges) if cluster_edges else 0

                    cluster_frequencies = [self.keywords_graph.nodes[kw].get('frequency', 0) for kw in cluster_keywords]
                    
                    clusters.append({
                        'cluster_id': i,
                        'keywords': cluster_keywords,
                        'size': len(cluster_keywords),
                        'avg_weight': avg_weight,
                        'total_frequency': sum(cluster_frequencies),
                        'avg_frequency': sum(cluster_frequencies) / len(cluster_frequencies)
                    })
            
            clusters.sort(key=lambda x: x['size'], reverse=True)
            return clusters
            
        except ImportError:
            return None
    
    def get_trending_keywords(self, min_frequency=2):
        """Identifica keywords trending basándose en conexiones y frecuencia"""
        if not self.keywords_graph:
            return None
        
        trending_data = []
        
        for node, data in self.keywords_graph.nodes(data=True):
            if data.get('type') == 'keyword' and data.get('frequency', 0) >= min_frequency:
                frequency = data.get('frequency', 0)
                author_connections = len([n for n in self.keywords_graph.neighbors(node) 
                                        if self.keywords_graph.nodes[n].get('type') == 'author'])

                author_weights = []
                for neighbor in self.keywords_graph.neighbors(node):
                    if self.keywords_graph.nodes[neighbor].get('type') == 'author':
                        weight = self.keywords_graph.edges[node, neighbor].get('weight', 1)
                        author_weights.append(weight)
                
                avg_author_weight = sum(author_weights) / len(author_weights) if author_weights else 0

                trending_score = (frequency * 0.4) + (author_connections * 0.4) + (avg_author_weight * 0.2)
                
                trending_data.append({
                    'keyword': node,
                    'trending_score': trending_score,
                    'frequency': frequency,
                    'author_connections': author_connections,
                    'avg_author_weight': avg_author_weight,
                    'papers': data.get('papers', [])
                })
        
        trending_data.sort(key=lambda x: x['trending_score'], reverse=True)
        return trending_data[:20]
    
    def search_related_keywords(self, keyword_query, max_results=10):
        """Busca keywords relacionadas basándose en co-ocurrencia"""
        if not self.keywords_graph:
            return None

        query_normalized = keyword_query.lower().strip()

        matching_keywords = []
        for node, data in self.keywords_graph.nodes(data=True):
            if data.get('type') == 'keyword' and query_normalized in node.lower():
                matching_keywords.append(node)
        
        if not matching_keywords:
            return None

        related_keywords = {}
        
        for keyword in matching_keywords:
            for neighbor in self.keywords_graph.neighbors(keyword):
                neighbor_data = self.keywords_graph.nodes[neighbor]
                if neighbor_data.get('type') == 'keyword' and neighbor != keyword:
                    edge_data = self.keywords_graph.edges[keyword, neighbor]
                    weight = edge_data.get('weight', 1)
                    
                    if neighbor not in related_keywords:
                        related_keywords[neighbor] = {
                            'keyword': neighbor,
                            'total_weight': weight,
                            'connections': 1,
                            'frequency': neighbor_data.get('frequency', 0)
                        }
                    else:
                        related_keywords[neighbor]['total_weight'] += weight
                        related_keywords[neighbor]['connections'] += 1

        for data in related_keywords.values():
            data['relevance'] = (data['total_weight'] * 0.6) + (data['frequency'] * 0.4)
        
        related_list = list(related_keywords.values())
        related_list.sort(key=lambda x: x['relevance'], reverse=True)
        
        return {
            'query': keyword_query,
            'matching_keywords': matching_keywords,
            'related_keywords': related_list[:max_results]
        }

def create_keyword_analysis_visualization(keyword_stats):
    """Crea visualizaciones para el análisis de palabras clave"""
    if not keyword_stats:
        return None
    
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    
    top_keywords = keyword_stats['keyword_frequencies'][:12]  
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            'Temas de Investigación Más Frecuentes',
            'Distribución de Frecuencias de Todos los Temas'
        ),
        specs=[[{"type": "bar"}, {"type": "histogram"}]]
    )
    
    fig.add_trace(
        go.Bar(
            y=[kw['keyword'][:30] + "..." if len(kw['keyword']) > 30 else kw['keyword'] for kw in top_keywords],
            x=[kw['frequency'] for kw in top_keywords],
            orientation='h',
            name='Frecuencia de Aparición',
            marker=dict(
                color=[kw['frequency'] for kw in top_keywords],
                colorscale='viridis',
                showscale=False,
                line=dict(color='rgba(50,50,50,0.5)', width=0.5)
            ),
            text=[f"{kw['frequency']}" for kw in top_keywords],
            textposition='inside',
            textfont=dict(color='white', size=10),
            hovertemplate='<b>%{y}</b><br>Frecuencia: %{x}<br>Papers: %{customdata}<extra></extra>',
            customdata=[kw['papers'] for kw in top_keywords]
        ),
        row=1, col=1
    )

    frequencies = [kw['frequency'] for kw in keyword_stats['keyword_frequencies']]
    fig.add_trace(
        go.Histogram(
            x=frequencies,
            nbinsx=25,
            name='Distribución de Frecuencias',
            marker=dict(
                color='lightblue',
                line=dict(color='darkblue', width=1)
            ),
            opacity=0.7,
            hovertemplate='Frecuencia: %{x}<br>Cantidad de Temas: %{y}<extra></extra>'
        ),
        row=1, col=2
    )

    fig.update_layout(
        height=500,  
        showlegend=False,  
        title=dict(
            text="Panorama de Investigación - Análisis de Temas",
            font=dict(size=16),
            x=0.5
        ),
        margin=dict(l=20, r=20, t=80, b=20)
    )
    

    fig.update_xaxes(
        title_text="Frecuencia en Literatura",
        row=1, col=1,
        tickfont=dict(size=10)
    )
    fig.update_yaxes(
        title_text="Temas de Investigación",
        row=1, col=1,
        tickfont=dict(size=9)
    )
    fig.update_xaxes(
        title_text="Frecuencia",
        row=1, col=2,
        tickfont=dict(size=10)
    )
    fig.update_yaxes(
        title_text="Cantidad de Temas",
        row=1, col=2,
        tickfont=dict(size=10)
    )
    
    return fig

def create_keyword_network_visualization(keywords_graph, max_nodes=100):
    """Crea una visualización de red de las palabras clave más importantes"""
    if not keywords_graph:
        return None
    
    import plotly.graph_objects as go
    import networkx as nx
    
    keyword_nodes = [(n, d) for n, d in keywords_graph.nodes(data=True) if d.get('type') == 'keyword']
    keyword_nodes.sort(key=lambda x: x[1].get('frequency', 0), reverse=True)
    
    top_keywords = [n for n, d in keyword_nodes[:max_nodes//2]]
    
    nodes_to_include = set(top_keywords)
    
    author_count = 0
    for keyword in top_keywords:
        for neighbor in keywords_graph.neighbors(keyword):
            if (keywords_graph.nodes[neighbor].get('type') == 'author' and 
                author_count < max_nodes//2):
                nodes_to_include.add(neighbor)
                author_count += 1
    
    subgraph = keywords_graph.subgraph(nodes_to_include)
    
    pos = nx.spring_layout(subgraph, k=3, iterations=50)

    edge_x = []
    edge_y = []
    edge_weights = []
    
    for edge in subgraph.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_weights.append(edge[2].get('weight', 1))
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    node_x = []
    node_y = []
    node_text = []
    node_color = []
    node_size = []
    node_info = []
    
    for node in subgraph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        node_data = subgraph.nodes[node]
        node_type = node_data.get('type', 'unknown')
        
        if node_type == 'keyword':
            node_text.append(node)
            node_color.append('lightblue')
            freq = node_data.get('frequency', 0)
            node_size.append(max(10, freq * 3))
            node_info.append(f"Tema: {node}<br>Frecuencia: {freq}<br>Papers: {len(node_data.get('papers', []))}")
        else:  
            name = node_data.get('name', 'Unknown')
            node_text.append(name[:20] + '...' if len(name) > 20 else name)
            node_color.append('lightcoral')
            papers = len(node_data.get('papers', []))
            node_size.append(max(8, papers * 2))
            node_info.append(f"Investigador: {name}<br>Papers: {papers}")
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=node_text,
        textposition="middle center",
        hovertext=node_info,
        marker=dict(
            showscale=False,
            color=node_color,
            size=node_size,
            line=dict(width=2, color='white')
        )
    )

    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                        title=dict(text='Red de Temas de Investigación', font=dict(size=16)),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        annotations=[ dict(
                            text="Azul: Temas de Investigación, Coral: Investigadores",
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002,
                            xanchor='left', yanchor='bottom',
                            font=dict(color='gray', size=12)
                        )],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        height=600
                   ))
    
    return fig

def create_community_graph_visualization(graph, communities_dict, max_nodes=200, min_community_size=5):
    """Crea visualización específica del grafo con comunidades coloreadas y bien separadas"""
    import plotly.graph_objects as go
    import plotly.express as px
    import networkx as nx
    import numpy as np
    
    G = graph.graph.copy()
    
    filtered_communities = {
        comm_id: stats for comm_id, stats in communities_dict.items()
        if stats['size'] >= min_community_size
    }
    
    node_to_community = {}
    for comm_id, stats in filtered_communities.items():
        for node in stats['nodes']:
            node_to_community[node] = comm_id

    relevant_nodes = set(node_to_community.keys())
 
    if len(relevant_nodes) > max_nodes:
        node_scores = {}
        for node in relevant_nodes:
            degree = G.degree(node)
            comm_size = filtered_communities[node_to_community[node]]['size']
            node_scores[node] = degree * comm_size
        
        top_nodes = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
        relevant_nodes = {node for node, score in top_nodes}
    
 
    G = G.subgraph(relevant_nodes)
    
    sorted_communities = sorted(filtered_communities.keys(), 
                               key=lambda x: filtered_communities[x]['size'], 
                               reverse=True)
    

    pos_initial = nx.spring_layout(G, k=1.0, iterations=50, seed=42)
    
    pos = {}
    community_centers = {}
    

    for comm_id in sorted_communities:
        nodes_in_comm = [node for node in G.nodes() if node_to_community.get(node) == comm_id]
        if nodes_in_comm:

            center_x = np.mean([pos_initial[node][0] for node in nodes_in_comm])
            center_y = np.mean([pos_initial[node][1] for node in nodes_in_comm])
            community_centers[comm_id] = (center_x, center_y)
    
    angle_step = 2 * np.pi / len(community_centers)
    radius = 3.0 
    
    for i, comm_id in enumerate(sorted_communities):
        if comm_id in community_centers:
            angle = i * angle_step
            new_center_x = radius * np.cos(angle)
            new_center_y = radius * np.sin(angle)
            
            nodes_in_comm = [node for node in G.nodes() if node_to_community.get(node) == comm_id]
            if nodes_in_comm:
                old_center = community_centers[comm_id]
                
                for node in nodes_in_comm:
                    if node in pos_initial:
                        relative_x = pos_initial[node][0] - old_center[0]
                        relative_y = pos_initial[node][1] - old_center[1]

                        scale_factor = 0.5
                        pos[node] = (
                            new_center_x + relative_x * scale_factor,
                            new_center_y + relative_y * scale_factor
                        )

    for node in G.nodes():
        if node not in pos:
            pos[node] = pos_initial[node]
    
    def generate_community_colors(num_communities):
        """Genera colores distintivos automáticamente usando HSV"""
        import colorsys
        colors = []
        for i in range(num_communities):
            hue = i / num_communities
            saturation = 0.7 + (i % 3) * 0.1  
            value = 0.8 + (i % 2) * 0.15    
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            hex_color = '#{:02x}{:02x}{:02x}'.format(
                int(rgb[0] * 255),
                int(rgb[1] * 255), 
                int(rgb[2] * 255)
            )
            colors.append(hex_color)
        return colors
    
    colors = generate_community_colors(len(sorted_communities))
    
    community_colors = {}
    
    for i, comm_id in enumerate(sorted_communities):
        community_colors[comm_id] = colors[i]
    
    edge_traces = []
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        weight = G[edge[0]][edge[1]].get('weight', 1)
        
        node1_comm = node_to_community.get(edge[0])
        node2_comm = node_to_community.get(edge[1])
        
        if node1_comm == node2_comm and node1_comm is not None:
            hex_color = community_colors.get(node1_comm, '#7D7D7D')
            edge_color = hex_to_rgba(hex_color, 0.8)
            width = min(weight * 1.5, 6)
        else:
            edge_color = 'rgba(125,125,125,0.3)'
            width = min(weight * 0.8, 3)
        
        edge_traces.append(go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=width, color=edge_color),
            hoverinfo='none',
            showlegend=False
        ))

    node_traces = []
    
    for comm_id in sorted_communities:
        nodes_in_comm = [node for node in G.nodes() if node_to_community.get(node) == comm_id]
        
        if not nodes_in_comm:
            continue
            
        node_x = []
        node_y = []
        node_text = []
        node_size = []
        
        for node in nodes_in_comm:
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            node_data = G.nodes[node]
            name = node_data.get('name', 'Desconocido')
            paper_count = node_data.get('paper_count', 0)
            
            hover_text = f"<b>{name}</b><br>Papers: {paper_count}<br>Colaboradores: {G.degree(node)}<br>Comunidad: Grupo {comm_id}"
            node_text.append(hover_text)
            node_size.append(max(15, min(paper_count * 3, 60)))
        
        comm_stats = filtered_communities[comm_id]
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers',
            hoverinfo='text',
            text=node_text,
            marker=dict(
                size=node_size,
                color=community_colors[comm_id],
                line=dict(width=2.5, color='white'),
                opacity=0.8
            ),
            name=f"Grupo {comm_id} ({comm_stats['size']} miembros)",
            showlegend=True
        )
        
        node_traces.append(node_trace)
    
    fig = go.Figure(data=edge_traces + node_traces)
    
    fig.update_layout(
        title=f"Red de Colaboración Científica - {len(filtered_communities)} Comunidades de Investigación",
        showlegend=True,
        hovermode='closest',
        margin=dict(b=80, l=40, r=40, t=80),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        height=850,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="rgba(0,0,0,0.3)",
            borderwidth=1,
            font=dict(size=11)
        )
    )
    
    return fig

def create_wordcloud_visualization(keyword_stats, max_words=100, colormap='viridis'):
    """Crea una nube de palabras con las palabras clave más frecuentes"""
    try:
        from wordcloud import WordCloud
        import plotly.graph_objects as go
        import io
        import base64
        from PIL import Image
        
        if not keyword_stats or 'keyword_frequencies' not in keyword_stats:
            return None
        
        # Preparar los datos para la nube de palabras
        word_freq = {}
        try:
            for keyword_data in keyword_stats['keyword_frequencies'][:max_words]:
                if isinstance(keyword_data, (list, tuple)) and len(keyword_data) >= 2:
                    keyword = keyword_data[0]  # Nombre del tema
                    frequency = keyword_data[1]  # Frecuencia
                    if isinstance(keyword, str) and isinstance(frequency, (int, float)):
                        word_freq[keyword] = frequency
        except (TypeError, IndexError) as e:
            print(f"Error procesando keyword_frequencies: {e}")
            return None
        
        if not word_freq:
            return None
        
        # Configurar la nube de palabras
        wordcloud = WordCloud(
            width=800, 
            height=400,
            background_color='white',
            max_words=max_words,
            colormap=colormap,
            relative_scaling=0.5,
            font_path=None,
            prefer_horizontal=0.7,
            min_font_size=10,
            max_font_size=80,
            random_state=42
        ).generate_from_frequencies(word_freq)
        
        # Convertir a imagen para mostrar en Plotly
        img = wordcloud.to_image()
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        # Crear figura de Plotly con la imagen
        fig = go.Figure()
        
        fig.add_layout_image(
            dict(
                source=f"data:image/png;base64,{img_base64}",
                xref="x",
                yref="y",
                x=0,
                y=1,
                sizex=1,
                sizey=1,
                sizing="stretch",
                opacity=1,
                layer="below"
            )
        )
        
        # Configurar el layout
        fig.update_layout(
            title=dict(
                text="🏷️ Nube de Palabras Clave Más Utilizadas",
                font=dict(size=18),
                x=0.5
            ),
            xaxis=dict(
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                range=[0, 1]
            ),
            yaxis=dict(
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                range=[0, 1]
            ),
            height=450,
            margin=dict(l=20, r=20, t=50, b=20),
            showlegend=False,
            annotations=[
                dict(
                    text=f"Mostrando los {len(word_freq)} temas más frecuentes",
                    showarrow=False,
                    xref="paper", 
                    yref="paper",
                    x=0.5, 
                    y=-0.1,
                    xanchor='center', 
                    yanchor='top',
                    font=dict(color='gray', size=12)
                )
            ]
        )
        
        return fig
        
    except ImportError:
        # Si wordcloud no está instalada, crear una visualización alternativa
        return create_alternative_wordcloud_visualization(keyword_stats, max_words)
    except Exception as e:
        print(f"Error creando nube de palabras: {e}")
        return create_alternative_wordcloud_visualization(keyword_stats, max_words)

def create_alternative_wordcloud_visualization(keyword_stats, max_words=50):
    """Visualización alternativa cuando wordcloud no está disponible"""
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd
    import numpy as np
    
    if not keyword_stats or 'keyword_frequencies' not in keyword_stats:
        return None
    
    # Preparar datos
    keywords_data = keyword_stats['keyword_frequencies'][:max_words]
    
    df = pd.DataFrame(keywords_data, columns=['Tema', 'Frecuencia', 'Papers', 'Investigadores'])
    
    # Crear gráfico de burbujas como alternativa
    fig = px.scatter(
        df.head(30),
        x=np.random.uniform(0, 10, len(df.head(30))),  # Posiciones aleatorias
        y=np.random.uniform(0, 10, len(df.head(30))),
        size='Frecuencia',
        color='Investigadores',
        hover_name='Tema',
        hover_data={'Frecuencia': True, 'Papers': True, 'Investigadores': True},
        title="📊 Visualización de Temas de Investigación (Alternativa)",
        color_continuous_scale='viridis',
        size_max=60
    )
    
    # Agregar etiquetas de texto
    for i, row in df.head(15).iterrows():  # Solo los 15 principales para evitar sobreposición
        fig.add_annotation(
            x=np.random.uniform(1, 9),
            y=np.random.uniform(1, 9),
            text=row['Tema'][:20] + '...' if len(row['Tema']) > 20 else row['Tema'],
            showarrow=False,
            font=dict(size=max(8, min(16, row['Frecuencia'])), color='white'),
            bgcolor=f'rgba(0,0,0,0.5)',
            bordercolor='white',
            borderwidth=1
        )
    
    fig.update_layout(
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        height=450,
        showlegend=False
    )
    
    return fig
