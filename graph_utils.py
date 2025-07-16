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


class GraphAnalyzer:
    """Clase para análisis avanzado del grafo"""
    
    def __init__(self, graph):
        self.graph = graph.graph
        
    def detect_communities(self):
        """Detecta comunidades en el grafo"""
        try:
            partition = community_louvain.best_partition(self.graph)
            return partition
        except:
            return {}
    
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
    
    def get_threshold_analysis(self):
        """Analiza el rendimiento con diferentes umbrales"""
        if 'predictions_data' not in self.stats:
            return {}
        
        thresholds = np.arange(0.1, 1.0, 0.1)
        results = []
        
        for threshold in thresholds:
            tp = fp = tn = fn = 0
            
            for pred in self.stats['predictions_data']:
                model_pred = pred['probability'] >= threshold
                true_pred = pred['prediction']
                
                if model_pred and true_pred:
                    tp += 1
                elif model_pred and not true_pred:
                    fp += 1
                elif not model_pred and true_pred:
                    fn += 1
                else:
                    tn += 1
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            results.append({
                'threshold': threshold,
                'precision': precision,
                'recall': recall,
                'f1': f1
            })
        
        return results


def create_advanced_graph_visualization(graph, communities=None, centrality_measure=None):
    """Crea visualización avanzada del grafo con comunidades y centralidad"""
    G = graph.graph
    
    if G.number_of_nodes() > 200:
        degrees = dict(G.degree())
        top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:200]
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
        title="Grafo de Colaboración Avanzado",
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
