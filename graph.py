import os
import requests
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
import re
from collections import defaultdict
import time

class AuthorGraphBuilder:
    def __init__(self, grobid_url="http://localhost:8070/api/processHeaderDocument"):
        self.grobid_url = grobid_url
        self.graph = nx.Graph()
        self.author_variations = defaultdict(set)  # Para manejar variaciones de nombres
        
    def normalize_name(self, name):
        """Normaliza el nombre del autor para comparación"""
        if not name:
            return ""
        # Remover caracteres especiales, convertir a minúsculas
        normalized = re.sub(r'[^\w\s-]', '', name.lower().strip())
        # Remover espacios extra
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    def similarity_score(self, name1, name2):
        """Calcula similitud entre dos nombres"""
        return SequenceMatcher(None, name1, name2).ratio()
    
    def find_similar_author(self, new_author, threshold=0.85):
        """Busca si existe un autor similar en el grafo"""
        normalized_new = self.normalize_name(new_author)
        
        for existing_author in self.graph.nodes():
            normalized_existing = self.normalize_name(existing_author)
            
            # Verificar similitud exacta primero
            if normalized_new == normalized_existing:
                return existing_author
            
            # Verificar similitud por ratio
            if self.similarity_score(normalized_new, normalized_existing) >= threshold:
                return existing_author
            
            # Verificar si son variaciones del mismo autor (iniciales vs nombre completo)
            if self.are_name_variations(normalized_new, normalized_existing):
                return existing_author
        
        return None
    
    def are_name_variations(self, name1, name2):
        """Verifica si dos nombres son variaciones del mismo autor"""
        parts1 = name1.split()
        parts2 = name2.split()
        
        # Si uno tiene iniciales y otro nombre completo
        if len(parts1) != len(parts2):
            return False
        
        for p1, p2 in zip(parts1, parts2):
            # Si uno es inicial y otro es nombre completo
            if len(p1) == 1 and len(p2) > 1:
                if not p2.startswith(p1):
                    return False
            elif len(p2) == 1 and len(p1) > 1:
                if not p1.startswith(p2):
                    return False
            elif p1 != p2:
                return False
        
        return True
    
    def extract_authors_from_pdf(self, pdf_path):
        """Extrae autores de un PDF usando GROBID"""
        try:
            with open(pdf_path, 'rb') as file:
                files = {'input': file}
                response = requests.post(self.grobid_url, files=files, timeout=30)
                
            if response.status_code == 200:
                return self.parse_authors_from_tei(response.text)
            else:
                print(f"Error al procesar {pdf_path}: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error al procesar {pdf_path}: {str(e)}")
            return []
    
    def parse_authors_from_tei(self, tei_xml):
        """Extrae autores del XML TEI devuelto por GROBID"""
        authors = []
        
        try:
            # Parsear XML
            root = ET.fromstring(tei_xml)
            
            # Buscar autores en el namespace TEI
            namespaces = {'tei': 'http://www.tei-c.org/ns/1.0'}
            
            # Buscar elementos author
            for author in root.findall('.//tei:author', namespaces):
                # Buscar persName dentro del autor
                persname = author.find('.//tei:persName', namespaces)
                if persname is not None:
                    # Extraer nombre completo
                    forename = persname.find('.//tei:forename', namespaces)
                    surname = persname.find('.//tei:surname', namespaces)
                    
                    if forename is not None and surname is not None:
                        full_name = f"{forename.text} {surname.text}".strip()
                        if full_name:
                            authors.append(full_name)
                    elif persname.text:
                        # Si no hay separación, usar el texto completo
                        authors.append(persname.text.strip())
            
            # Si no se encontraron autores con el método anterior, buscar de forma más general
            if not authors:
                for author_elem in root.findall('.//tei:author', namespaces):
                    if author_elem.text:
                        authors.append(author_elem.text.strip())
            
        except ET.ParseError as e:
            print(f"Error al parsear XML: {str(e)}")
        
        return authors
    
    def add_paper_to_graph(self, pdf_path, authors):
        """Añade un paper y sus autores al grafo"""
        paper_name = Path(pdf_path).stem
        
        # Normalizar autores y encontrar similares
        normalized_authors = []
        for author in authors:
            similar_author = self.find_similar_author(author)
            if similar_author:
                normalized_authors.append(similar_author)
                # Agregar variación al conjunto
                self.author_variations[similar_author].add(author)
            else:
                normalized_authors.append(author)
                self.author_variations[author].add(author)
        
        # Añadir autores como nodos si no existen
        for author in normalized_authors:
            if not self.graph.has_node(author):
                self.graph.add_node(author, type='author')
        
        # Añadir paper como nodo
        self.graph.add_node(paper_name, type='paper')
        
        # Conectar autores con el paper
        for author in normalized_authors:
            self.graph.add_edge(author, paper_name)
        
        # Conectar autores entre sí (co-autoría)
        for i, author1 in enumerate(normalized_authors):
            for author2 in normalized_authors[i+1:]:
                if self.graph.has_edge(author1, author2):
                    # Incrementar peso de la arista
                    self.graph[author1][author2]['weight'] += 1
                else:
                    self.graph.add_edge(author1, author2, weight=1)
    
    def process_pdf_directory(self, pdf_directory):
        """Procesa todos los PDFs en un directorio"""
        pdf_directory = Path(pdf_directory)
        pdf_files = list(pdf_directory.glob("**/*.pdf"))
        
        print(f"Procesando {len(pdf_files)} archivos PDF...")
        
        for i, pdf_file in enumerate(pdf_files):
            print(f"Procesando ({i+1}/{len(pdf_files)}): {pdf_file.name}")
            
            authors = self.extract_authors_from_pdf(pdf_file)
            
            if authors:
                print(f"  Autores encontrados: {authors}")
                self.add_paper_to_graph(pdf_file, authors)
            else:
                print(f"  No se encontraron autores")
            
            # Pausa para no sobrecargar GROBID
            time.sleep(1)
    
    def visualize_graph(self, save_path="author_graph.png"):
        """Visualiza el grafo de autores"""
        plt.figure(figsize=(15, 10))
        
        # Separar nodos por tipo
        author_nodes = [node for node, data in self.graph.nodes(data=True) if data.get('type') == 'author']
        paper_nodes = [node for node, data in self.graph.nodes(data=True) if data.get('type') == 'paper']
        
        # Crear layout
        pos = nx.spring_layout(self.graph, k=3, iterations=50)
        
        # Dibujar nodos de autores
        nx.draw_networkx_nodes(self.graph, pos, nodelist=author_nodes, 
                              node_color='lightblue', node_size=500, alpha=0.7)
        
        # Dibujar nodos de papers
        nx.draw_networkx_nodes(self.graph, pos, nodelist=paper_nodes, 
                              node_color='lightcoral', node_size=300, alpha=0.7)
        
        # Dibujar aristas
        nx.draw_networkx_edges(self.graph, pos, alpha=0.5)
        
        # Dibujar etiquetas (solo para autores si hay muchos nodos)
        if len(self.graph.nodes()) < 50:
            nx.draw_networkx_labels(self.graph, pos, font_size=8)
        
        plt.title("Grafo de Autores y Colaboraciones")
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def get_statistics(self):
        """Obtiene estadísticas del grafo"""
        author_nodes = [node for node, data in self.graph.nodes(data=True) if data.get('type') == 'author']
        paper_nodes = [node for node, data in self.graph.nodes(data=True) if data.get('type') == 'paper']
        
        print(f"Estadísticas del grafo:")
        print(f"- Total de nodos: {len(self.graph.nodes())}")
        print(f"- Autores: {len(author_nodes)}")
        print(f"- Papers: {len(paper_nodes)}")
        print(f"- Aristas: {len(self.graph.edges())}")
        
        # Autores más prolíficos
        if author_nodes:
            author_papers = {}
            for author in author_nodes:
                paper_count = sum(1 for neighbor in self.graph.neighbors(author) 
                                if self.graph.nodes[neighbor].get('type') == 'paper')
                author_papers[author] = paper_count
            
            print(f"\nAutores más prolíficos:")
            for author, count in sorted(author_papers.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"- {author}: {count} papers")
        
        # Variaciones de nombres detectadas
        print(f"\nVariaciones de nombres detectadas:")
        for main_name, variations in self.author_variations.items():
            if len(variations) > 1:
                print(f"- {main_name}: {variations}")

# Ejemplo de uso
if __name__ == "__main__":
    # Crear instancia del constructor de grafo
    builder = AuthorGraphBuilder()
    
    # Procesar directorio de PDFs
    pdf_directory = "c:/Users/Anabel/OneDrive/Desktop/ARC/pdfs_papers"
    
    # Verificar que GROBID esté ejecutándose
    try:
        response = requests.get("http://localhost:8070/api/isalive")
        if response.status_code != 200:
            print("Error: GROBID no está ejecutándose. Ejecuta: docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("Error: No se puede conectar a GROBID. Asegúrate de que Docker esté ejecutándose.")
        exit(1)
    
    # Procesar PDFs
    builder.process_pdf_directory(pdf_directory)
    
    # Mostrar estadísticas
    builder.get_statistics()
    
    # Visualizar grafo
    builder.visualize_graph()
    
    # Guardar grafo
    nx.write_gexf(builder.graph, "author_collaboration_graph.gexf")
    print("Grafo guardado en 'author_collaboration_graph.gexf'")