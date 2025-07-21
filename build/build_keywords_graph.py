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
        import re
        name = re.sub(r'\s+', ' ', name)  
        name = re.sub(r'[^\w\s-]', '', name)  
        return name
    
    def save(self, filename):
        """Guarda el grafo convirtiendo listas a strings para compatibilidad con GraphML"""
        graph_copy = self.key_graph.copy()

        for node, data in graph_copy.nodes(data=True):
            for key, value in data.items():
                if isinstance(value, (list,set)):
                    data[key] = ','.join(map(str, value))
        
        for u, v, data in graph_copy.edges(data=True):
            for key, value in data.items():
                if isinstance(value, (list,set)):
                    data[key] = ','.join(map(str, value))
        
        nx.write_graphml(graph_copy, filename)
        print(f"Grafo guardado en {filename}")
        print(f"Nodos: {graph_copy.number_of_nodes()}, Aristas: {graph_copy.number_of_edges()}")
    def find_similar_keyword(self, keyword):
        """
        Busca keywords existentes similares al nuevo keyword.
        Puede implementarse usando distancia de Levenshtein, 
        coincidencia de substrings, o algún otro método.
        """
        for existing in self.key_graph.nodes():
            if keyword.lower() in existing.lower() or existing.lower() in keyword.lower():
                return existing
        return None
    def build(self):
        """Construye el grafo de palabras clave con conexiones a autores"""
        data = self.__load()
        author_graph = self.__load_graph('./graph/author_collaboration_graph.graphml')
        
        # 1. Construir mapeo paper -> autores
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
        
        # 2. Procesar cada paper
        for pdf_key, value in data.items():
            keywords = value.get('keywords', [])
            if not keywords:
                continue
                
            # Normalizar y procesar keywords
            normalized_keywords = []
            for keyword in keywords:
                if not keyword or not keyword.strip():
                    continue
                    
                norm_keyword = self.normalize(keyword)
                if not norm_keyword or len(norm_keyword) <= 1:
                    continue
                    
                # Buscar keyword similar existente
                similar_keyword = self.find_similar_keyword(norm_keyword)
                target_keyword = similar_keyword if similar_keyword else norm_keyword
                
                # Añadir/actualizar nodo de keyword
                if not self.key_graph.has_node(target_keyword):
                    self.key_graph.add_node(
                        target_keyword,
                        type='keyword',
                        original_forms=set([keyword]),  # Usamos set para evitar duplicados
                        papers=set([pdf_key]),         # Usamos set para evitar duplicados
                        frequency=1
                    )
                else:
                    node_data = self.key_graph.nodes[target_keyword]
                    node_data['original_forms'].add(keyword)
                    if pdf_key not in node_data['papers']:
                        node_data['papers'].add(pdf_key)
                        node_data['frequency'] += 1
                
                normalized_keywords.append(target_keyword)
            
            # 3. Conectar con autores
            authors_in_paper = paper_to_authors.get(pdf_key, [])
            for author_info in authors_in_paper:
                author_node = f"author_{author_info['id']}"
                
                if not self.key_graph.has_node(author_node):
                    self.key_graph.add_node(
                        author_node,
                        type='author',
                        name=author_info['name'],
                        all_names=author_info['all_names'],
                        papers=set([pdf_key]))
                else:
                    self.key_graph.nodes[author_node]['papers'].add(pdf_key)
                
                # Conectar keywords con autores
                for norm_keyword in normalized_keywords:
                    if not self.key_graph.has_edge(norm_keyword, author_node):
                        self.key_graph.add_edge(
                            norm_keyword,
                            author_node,
                            type='author_keyword',
                            papers=set([pdf_key]),
                            weight=1
                        )
                    else:
                        edge_data = self.key_graph.edges[norm_keyword, author_node]
                        edge_data['papers'].add(pdf_key)
                        edge_data['weight'] += 1
            
            # 4. Conectar keywords co-ocurrentes
            for i, keyword1 in enumerate(normalized_keywords):
                for keyword2 in normalized_keywords[i+1:]:
                    if keyword1 != keyword2:
                        if not self.key_graph.has_edge(keyword1, keyword2):
                            self.key_graph.add_edge(
                                keyword1,
                                keyword2,
                                type='keyword_cooccurrence',
                                papers=set([pdf_key]),
                                weight=1
                            )
                        else:
                            edge_data = self.key_graph.edges[keyword1, keyword2]
                            edge_data['papers'].add(pdf_key)
                            edge_data['weight'] += 1
        
        # 5. Reporte final
        print(f"Grafo construido con {self.key_graph.number_of_nodes()} nodos y {self.key_graph.number_of_edges()} aristas")
        
        keyword_nodes = [n for n, d in self.key_graph.nodes(data=True) if d['type'] == 'keyword']
        author_nodes = [n for n, d in self.key_graph.nodes(data=True) if d['type'] == 'author']
        
        print(f"Palabras clave: {len(keyword_nodes)}")
        print(f"Autores: {len(author_nodes)}")
        
        keyword_freq = [(n, d['frequency']) for n, d in self.key_graph.nodes(data=True) 
                    if d['type'] == 'keyword']
        keyword_freq.sort(key=lambda x: x[1], reverse=True)
        
        print("\nTop 10 palabras clave más frecuentes:")
        for keyword, freq in keyword_freq[:10]:
            print(f"  {keyword}: {freq}")
if __name__ == "__main__":
    g = KeywordGraph('./data/extract_result.json')
    g.build()
    g.save('./graph/keywords_graph.graphml')