import networkx as nx 
import json

class KeywordGraph:

    def __init__(self, path):
        self.path = path
        self.key_graph = nx.Graph()

    def __load(self):
        try:
            with open(self.path, 'r') as f:
                return json.load(f)
        except:
            raise FileNotFoundError(f"path incorrecto: {self.path}")
    
    def __load_graph(self, filename):
        try:
            return nx.read_graphml(filename)
        except:
            raise FileNotFoundError("ruta incorrecta")
        
    def normalize(self, name):
        """Normaliza el nombre de las palabras clave"""
        name = name.lower().strip()
        # Eliminar espacios extra y caracteres especiales
        import re
        name = re.sub(r'\s+', ' ', name)  # múltiples espacios a uno solo
        name = re.sub(r'[^\w\s-]', '', name)  # mantener solo letras, números, espacios y guiones
        return name
    
    def save(self, filename):
        """Guarda el grafo convirtiendo listas a strings para compatibilidad con GraphML"""
        graph_copy = self.key_graph.copy()
        
        # Convertir listas a strings para compatibilidad con GraphML
        for node, data in graph_copy.nodes(data=True):
            for key, value in data.items():
                if isinstance(value, list):
                    data[key] = ','.join(map(str, value))
        
        for u, v, data in graph_copy.edges(data=True):
            for key, value in data.items():
                if isinstance(value, list):
                    data[key] = ','.join(map(str, value))
        
        nx.write_graphml(graph_copy, filename)
        print(f"Grafo guardado en {filename}")
        print(f"Nodos: {graph_copy.number_of_nodes()}, Aristas: {graph_copy.number_of_edges()}")
    
    def build(self):
        """Construye el grafo de palabras clave con conexiones a autores"""
        data = self.__load()
        author_graph = self.__load_graph('../author_collaboration_graph.graphml')
        
        # Crear un mapeo de papers a autores desde el grafo de autores
        paper_to_authors = {}
        for node_id, node_data in author_graph.nodes(data=True):
            papers = node_data.get('papers', '').split(',') if node_data.get('papers') else []
            for paper in papers:
                paper = paper.strip()
                if paper:
                    if paper not in paper_to_authors:
                        paper_to_authors[paper] = []
                    paper_to_authors[paper].append({
                        'id': node_id,
                        'name': node_data.get('name', ''),
                        'all_names': node_data.get('all_names', '')
                    })
        
        # Procesar cada PDF y sus palabras clave
        for pdf_key, value in data.items():
            keywords = value.get('keywords', [])
            if not keywords:
                continue
            
            # Normalizar y añadir palabras clave
            normalized_keywords = []
            for keyword in keywords:
                if keyword and keyword.strip():
                    norm_keyword = self.normalize(keyword)
                    if norm_keyword and len(norm_keyword) > 1:  
                        normalized_keywords.append(norm_keyword)
                        
                        # Añadir nodo de palabra clave si no existe
                        if not self.key_graph.has_node(norm_keyword):
                            self.key_graph.add_node(norm_keyword, 
                                                  type='keyword',
                                                  original_forms=[keyword],
                                                  papers=[pdf_key],
                                                  frequency=1)
                        else:
                            # Actualizar información del nodo existente
                            node_data = self.key_graph.nodes[norm_keyword]
                            if keyword not in node_data['original_forms']:
                                node_data['original_forms'].append(keyword)
                            if pdf_key not in node_data['papers']:
                                node_data['papers'].append(pdf_key)
                                node_data['frequency'] += 1
            
            # Conectar palabras clave con autores a través de papers
            authors_in_paper = paper_to_authors.get(pdf_key, [])
            for author_info in authors_in_paper:
                author_node = f"author_{author_info['id']}"
                
                # Añadir nodo de autor si no existe
                if not self.key_graph.has_node(author_node):
                    self.key_graph.add_node(author_node,
                                          type='author',
                                          name=author_info['name'],
                                          all_names=author_info['all_names'],
                                          papers=[pdf_key])
                else:
                    # Actualizar papers del autor
                    if pdf_key not in self.key_graph.nodes[author_node]['papers']:
                        self.key_graph.nodes[author_node]['papers'].append(pdf_key)
                
                # Conectar palabras clave con autores
                for norm_keyword in normalized_keywords:
                    if not self.key_graph.has_edge(norm_keyword, author_node):
                        self.key_graph.add_edge(norm_keyword, author_node,
                                              type='author_keyword',
                                              papers=[pdf_key],
                                              weight=1)
                    else:
                        # Incrementar peso de la conexión
                        edge_data = self.key_graph.edges[norm_keyword, author_node]
                        if pdf_key not in edge_data['papers']:
                            edge_data['papers'].append(pdf_key)
                            edge_data['weight'] += 1
            
            # Conectar palabras clave entre sí (co-ocurrencia en el mismo paper)
            for i, keyword1 in enumerate(normalized_keywords):
                for keyword2 in normalized_keywords[i+1:]:
                    if keyword1 != keyword2:
                        if not self.key_graph.has_edge(keyword1, keyword2):
                            self.key_graph.add_edge(keyword1, keyword2,
                                                  type='keyword_cooccurrence',
                                                  papers=[pdf_key],
                                                  weight=1)
                        else:
                            # Incrementar peso de co-ocurrencia
                            edge_data = self.key_graph.edges[keyword1, keyword2]
                            if pdf_key not in edge_data['papers']:
                                edge_data['papers'].append(pdf_key)
                                edge_data['weight'] += 1
        
        print(f"Grafo construido con {self.key_graph.number_of_nodes()} nodos y {self.key_graph.number_of_edges()} aristas")
        
        # Estadísticas del grafo
        keyword_nodes = [n for n, d in self.key_graph.nodes(data=True) if d['type'] == 'keyword']
        author_nodes = [n for n, d in self.key_graph.nodes(data=True) if d['type'] == 'author']
        
        print(f"Palabras clave: {len(keyword_nodes)}")
        print(f"Autores: {len(author_nodes)}")
        
        # Top palabras clave por frecuencia
        keyword_freq = [(n, d['frequency']) for n, d in self.key_graph.nodes(data=True) 
                       if d['type'] == 'keyword']
        keyword_freq.sort(key=lambda x: x[1], reverse=True)
        
        print("\nTop 10 palabras clave más frecuentes:")
        for keyword, freq in keyword_freq[:10]:
            print(f"  {keyword}: {freq}")


if __name__ == "__main__":
    g = KeywordGraph('../data/extract_result.json')
    g.build()
    g.save('../keywords_graph.graphml')