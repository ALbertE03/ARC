import networkx as nx
import json
from collections import defaultdict
import re
import joblib
import pandas as pd
from jellyfish import jaro_winkler_similarity, levenshtein_distance, soundex, metaphone
from unidecode import unidecode
import pickle
import time
from datetime import datetime


class ModelPerformanceTracker:
    def __init__(self):
        self.predictions = []
        self.difficult_cases = []
        self.start_time = None
        self.end_time = None
        
    def start_tracking(self):
        self.start_time = time.time()
        
    def end_tracking(self):
        self.end_time = time.time()
        
    def add_prediction(self, name1, name2, probability, prediction, threshold, is_difficult=False):
        prediction_data = {
            'name1': name1,
            'name2': name2,
            'probability': probability,
            'prediction': prediction,
            'threshold': threshold,
            'timestamp': datetime.now().isoformat(),
            'is_difficult': is_difficult
        }
        
        self.predictions.append(prediction_data)
        
        # Considerar casos difíciles si la probabilidad está cerca del umbral
        if abs(probability - threshold) < 0.5:
            self.difficult_cases.append(prediction_data)
            
    def get_performance_stats(self):
        if not self.predictions:
            return {}
            
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        probabilities = [p['probability'] for p in self.predictions]
        predictions = [p['prediction'] for p in self.predictions]
        
        return {
            'total_predictions': len(self.predictions),
            'difficult_cases': len(self.difficult_cases),
            'avg_probability': sum(probabilities) / len(probabilities),
            'positive_predictions': sum(predictions),
            'negative_predictions': len(predictions) - sum(predictions),
            'total_time': total_time,
            'avg_time_per_prediction': total_time / len(self.predictions) if self.predictions else 0,
            'predictions_data': self.predictions,
            'difficult_cases_data': self.difficult_cases
        }
        
    def save_performance(self, filename='model_performance.pkl'):
        with open(filename, 'wb') as f:
            pickle.dump(self.get_performance_stats(), f)
            
    @staticmethod
    def load_performance(filename='model_performance.pkl'):
        try:
            with open(filename, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return {}


class Graph:
    def __init__(self,path):
        self.graph = nx.Graph()
        self.path = path
        self.dict = defaultdict(set)
        self.data = self._load_data()
        self.model = self._load_model()
        self.threshold = 0.85
        self.performance_tracker = ModelPerformanceTracker()  


    def _load_model(self):
        try:
            return joblib.load('model.pkl')
        except FileNotFoundError:
            print("Modelo no encontrado. Asegúrate de que model.pkl esté en el directorio.")
            return None

    def normalize_name(self, name):
        if not name:
            return ""
        name = name.lower()
        name = unidecode(name)
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()

        replacements = {
            'jr': '', 'sr': '', 'dr': '', 'lic': '', 'ing': '', 
            'mtro': '', 'phd': '', 'c': '', 's a': '', 's.a.': ''
        }
        
        for k, v in replacements.items():
            name = name.replace(k, v)
        
        return name.strip()
    
    def advanced_features(self, name1, name2):
        """Extrae características avanzadas para comparar dos nombres"""
        n1 = self.normalize_name(name1)
        n2 = self.normalize_name(name2)
        
        tokens1 = n1.split()
        tokens2 = n2.split()
        
        features = {
            'jaro_winkler': jaro_winkler_similarity(n1, n2),
            'levenshtein': levenshtein_distance(n1, n2),
            'length_diff': abs(len(n1) - len(n2)),
            'length_ratio': min(len(n1), len(n2)) / max(len(n1), len(n2), 1),
            'same_soundex': int(soundex(n1) == soundex(n2)),
            'same_metaphone': int(metaphone(n1) == metaphone(n2)),
        }
        
        common_tokens = set(tokens1) & set(tokens2)
        features.update({
            'common_token_count': len(common_tokens),
            'token_ratio': len(common_tokens) / max(len(set(tokens1 + tokens2)), 1),
            'token_jaccard': len(common_tokens) / len(set(tokens1 + tokens2)) if tokens1 or tokens2 else 0,
            'first_token_match': int(tokens1[0] == tokens2[0]) if tokens1 and tokens2 else 0,
            'last_token_match': int(tokens1[-1] == tokens2[-1]) if tokens1 and tokens2 else 0,
        })
        
        initials1 = ''.join([t[0] for t in tokens1 if t])
        initials2 = ''.join([t[0] for t in tokens2 if t])
        features.update({
            'initials_match': int(initials1 == initials2),
            'initials_jaro': jaro_winkler_similarity(initials1, initials2),
        })
        features['inverted_name'] = int(
            " ".join(tokens1[::-1]) == " ".join(tokens2[::-1])
        )
        
        return features
    
    def _load_data(self):
        """Carga los datos de los PDFs extraídos"""
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Archivo no encontrado: {self.path}")
            return {}
    
    def predict_if_same_author(self, name1, name2):
        """Predice si dos nombres pertenecen al mismo autor usando el modelo ML"""
        if not self.model:
            print("Modelo no cargado. Usando similitud básica.")
            return self.normalize_name(name1) == self.normalize_name(name2)
        
        features = self.advanced_features(name1, name2)
        features_df = pd.DataFrame([features])

        try:
            proba = self.model.predict_proba(features_df)[0][1]
            prediction = proba >= self.threshold
 
            is_difficult = abs(proba - self.threshold) < 0.5

            self.performance_tracker.add_prediction(
                name1, name2, proba, prediction, self.threshold, is_difficult
            )
            
            print(f"Probabilidad de ser el mismo autor: {proba:.2f} (umbral: {self.threshold})")
            return prediction
        except Exception as e:
            print(f"Error en predicción: {e}")
            return False
    
    def build_graph(self):
        """Construye el grafo de autores"""
        print("Construyendo grafo de autores...")

        self.performance_tracker.start_tracking()
        
        all_authors = []
        author_to_papers = defaultdict(set)
        
        for pdf_key, pdf_data in self.data.items():
            if 'authors' in pdf_data:
                for author in pdf_data['authors']:
                    if author.get('name'):
                        author_name = author['name'].strip()
                        if author_name:
                            all_authors.append(author_name)
                            author_to_papers[author_name].add(pdf_key)
        
        print(f"Total de autores encontrados: {len(all_authors)}")
        
        unique_authors = list(set(all_authors))
        author_clusters = {}  # Mapea autor -> cluster_id
        cluster_counter = 0
        
        print("Agrupando autores similares...")
        for i, author1 in enumerate(unique_authors):
            if i % 100 == 0:
                print(f"Procesando autor {i+1}/{len(unique_authors)}")
            
            if author1 not in author_clusters:
                author_clusters[author1] = cluster_counter
                cluster_counter += 1
            
            for j, author2 in enumerate(unique_authors[i+1:], i+1):
                if author2 not in author_clusters:
                    
                    if self.predict_if_same_author(author1, author2):
                        author_clusters[author2] = author_clusters[author1]
                        print(f"Autores agrupados: '{author1}' y '{author2}'")
                    else:
                        author_clusters[author2] = cluster_counter
                        cluster_counter += 1
        
        print("Construyendo grafo final...")
        

        cluster_to_authors = defaultdict(set)
        cluster_to_papers = defaultdict(set)
        
        for author, cluster_id in author_clusters.items():
            cluster_to_authors[cluster_id].add(author)
            cluster_to_papers[cluster_id].update(author_to_papers[author])
        
        for cluster_id, authors in cluster_to_authors.items():
            representative_name = max(authors, key=len)
            
            self.graph.add_node(
                cluster_id,
                name=representative_name,
                all_names=list(authors),
                papers=list(cluster_to_papers[cluster_id]),
                paper_count=len(cluster_to_papers[cluster_id])
            )
        
        for pdf_key, pdf_data in self.data.items():
            if 'authors' in pdf_data and len(pdf_data['authors']) > 1:
                paper_clusters = set()
                for author in pdf_data['authors']:
                    if author.get('name'):
                        author_name = author['name'].strip()
                        if author_name in author_clusters:
                            paper_clusters.add(author_clusters[author_name])
                
                paper_clusters = list(paper_clusters)
                for i in range(len(paper_clusters)):
                    for j in range(i+1, len(paper_clusters)):
                        cluster1, cluster2 = paper_clusters[i], paper_clusters[j]
                        
                        if self.graph.has_edge(cluster1, cluster2):
                            self.graph[cluster1][cluster2]['weight'] += 1
                            self.graph[cluster1][cluster2]['papers'].append(pdf_key)
                        else:
                            self.graph.add_edge(
                                cluster1, cluster2,
                                weight=1,
                                papers=[pdf_key]
                            )
        
        self.performance_tracker.end_tracking()
        
        print(f"Grafo construido con {self.graph.number_of_nodes()} nodos y {self.graph.number_of_edges()} aristas")
        
 
        self.performance_tracker.save_performance()
        
    def get_author_info(self, author_name):
        """Obtiene información sobre un autor específico"""
        normalized_name = self.normalize_name(author_name)
        
        for node_id, node_data in self.graph.nodes(data=True):
            for name in node_data['all_names']:
                if self.normalize_name(name) == normalized_name:
                    return {
                        'cluster_id': node_id,
                        'representative_name': node_data['name'],
                        'all_names': node_data['all_names'],
                        'papers': node_data['papers'],
                        'paper_count': node_data['paper_count']
                    }
        return None
    
    def get_collaborators(self, author_name):
        """Obtiene los colaboradores de un autor"""
        author_info = self.get_author_info(author_name)
        if not author_info:
            return []
        
        cluster_id = author_info['cluster_id']
        collaborators = []
        
        for neighbor_id in self.graph.neighbors(cluster_id):
            neighbor_data = self.graph.nodes[neighbor_id]
            edge_data = self.graph[cluster_id][neighbor_id]
            
            collaborators.append({
                'name': neighbor_data['name'],
                'all_names': neighbor_data['all_names'],
                'collaboration_count': edge_data['weight'],
                'shared_papers': edge_data['papers']
            })
        
        return sorted(collaborators, key=lambda x: x['collaboration_count'], reverse=True)
    
    def save_graph(self, filename):
        """Guarda el grafo en formato GraphML"""

        graph_copy = self.graph.copy()
        
        for node_id, node_data in graph_copy.nodes(data=True):
            if 'all_names' in node_data and isinstance(node_data['all_names'], list):
                node_data['all_names'] = '|'.join(node_data['all_names'])
            if 'papers' in node_data and isinstance(node_data['papers'], list):
                node_data['papers'] = '|'.join(node_data['papers'])
        
        for u, v, edge_data in graph_copy.edges(data=True):
            if 'papers' in edge_data and isinstance(edge_data['papers'], list):
                edge_data['papers'] = '|'.join(edge_data['papers'])
        
        nx.write_graphml(graph_copy, filename)
        print(f"Grafo guardado en {filename}")
    
    def load_graph(self, filename):
        """Carga el grafo desde un archivo GraphML"""
        self.graph = nx.read_graphml(filename)
        
        for node_id, node_data in self.graph.nodes(data=True):
            if 'all_names' in node_data and isinstance(node_data['all_names'], str):
                node_data['all_names'] = node_data['all_names'].split('|')
            if 'papers' in node_data and isinstance(node_data['papers'], str):
                node_data['papers'] = node_data['papers'].split('|')
        
        for u, v, edge_data in self.graph.edges(data=True):
            if 'papers' in edge_data and isinstance(edge_data['papers'], str):
                edge_data['papers'] = edge_data['papers'].split('|')
        
        print(f"Grafo cargado desde {filename}")
    
    def get_statistics(self):
        """Obtiene estadísticas del grafo"""
        return {
            'total_authors': self.graph.number_of_nodes(),
            'total_collaborations': self.graph.number_of_edges(),
            'average_collaborators': sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes() if self.graph.number_of_nodes() > 0 else 0,
            'most_prolific_authors': sorted(
                [(data['name'], data['paper_count']) for _, data in self.graph.nodes(data=True)],
                key=lambda x: x[1], reverse=True
            )[:10]
        }
    
    def get_difficult_cases(self):
        """Obtiene los casos difíciles para revisión manual"""
        return self.performance_tracker.difficult_cases
        
    def update_difficult_case_decision(self, case_index, manual_decision):
        """Actualiza la decisión manual para un caso difícil"""
        if case_index < len(self.performance_tracker.difficult_cases):
            self.performance_tracker.difficult_cases[case_index]['manual_decision'] = manual_decision
            self.performance_tracker.save_performance()
            return True
        return False
        
    def get_performance_stats(self):
        """Obtiene estadísticas de rendimiento del modelo"""
        return self.performance_tracker.get_performance_stats()

    def same_author(self, name1, name2):
        """Determina si dos nombres pertenecen al mismo autor"""
        return self.predict_if_same_author(name1, name2)



if __name__ == "__main__":
    graph = Graph('data/extract_result.json')
    
    graph.build_graph()
    
    stats = graph.get_statistics()
    print("Estadísticas del grafo:")
    print(f"Total de autores: {stats['total_authors']}")
    print(f"Total de colaboraciones: {stats['total_collaborations']}")
    print(f"Promedio de colaboradores: {stats['average_collaborators']:.2f}")
    
    for name, count in stats['most_prolific_authors']:
        print(f"  {name}: {count} papers")
    
    graph.save_graph('author_collaboration_graph.graphml')

