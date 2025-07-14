import requests
import re
import os
import PyPDF2
import pdfplumber
from pathlib import Path
import json
from typing import List
import time

class Actor:
    def __init__(self, name: str = '', doi: str = '', email: str = ''):
        self.name = name
        self.doi = doi
        self.email = email
    
    def to_dict(self):
        return {
            'name': self.name,
            'doi': self.doi,
            'email': self.email
        }
    
    def __str__(self):
        return f"Actor(name='{self.name}', doi='{self.doi}', email='{self.email}')"

class PdfMetaData:
    def __init__(self, pdf_path: str = ''):
        self.actors: List[Actor] = []
        self.title: str = ''
        self.pdf_path = pdf_path
        self.text_content = ''
        self.doi = ''
        self.id_arxiv=''
        self.id_punchem=''
        self.abstract = ''
        self.authors_text = ''
        self.api_metadata = {}
        self.journal = ''
        self.year = ''
        self.publisher = ''
    def search_arxiv(self):
        pass
    def search_doi(self) -> bool:
        """Verifica si el PDF tiene DOI y obtiene metadatos de la API"""
        if self.doi and self.api_metadata:
            return True
        
        doi_patterns = [
            r'doi:\s*([^\s]+)',
            r'DOI:\s*([^\s]+)',
            r'https?://doi\.org/([^\s]+)',
            r'(10\.\d{4,}/[^\s]+)'
        ]
        
        for pattern in doi_patterns:
            match = re.search(pattern, self.text_content, re.IGNORECASE)
            if match:
                try:
                    self.doi = match.group(1) if len(match.groups()) > 0 else match.group(0)  
                    self.api_metadata = get_metadata_from_doi(self.doi)
                    
                    if self.api_metadata:
                        self.update_from_api_metadata()
                    
                    return True
                except IndexError:
                    self.doi = match.group(0)
                    
                    self.api_metadata = get_metadata_from_doi(self.doi)
                    if self.api_metadata:
                        self.update_from_api_metadata()
                    
                    return True
        return False
    
    def update_from_api_metadata(self):
        """Actualiza los metadatos usando la información de la API"""
        if not self.api_metadata:
            return

        if self.api_metadata.get('title'):
            self.title = self.api_metadata['title']

        self.actors = []
        for author_data in self.api_metadata.get('authors', []):
            actor = Actor(
                name=author_data['name'],
                doi=author_data.get('orcid', ''),
                email=''  
            )
            self.actors.append(actor)

        self.journal = self.api_metadata.get('journal', '')
        self.year = self.api_metadata.get('year', '')
        self.publisher = self.api_metadata.get('publisher', '')
        self.abstract = self.api_metadata.get('abstract', '')
    
    def extract_title(self) -> str:
        """Extrae el título del PDF"""
        if not self.text_content:
            return ''
        
        lines = self.text_content.split('\n')[:10]
        for line in lines:
            line = line.strip()
            # Filtrar líneas que probablemente sean títulos
            if len(line) > 10 and len(line) < 200 and not line.startswith('Abstract'):
                if not re.match(r'^(arXiv:|doi:|www\.|http)', line.lower()):
                    self.title = line
                    return line
        

        if self.pdf_path:
            self.title = Path(self.pdf_path).stem.replace('_', ' ')
        
        return self.title
    
    def extract_actors(self) -> List[Actor]:
        """Extrae los actores/autores del PDF"""
        if not self.text_content:
            return []
        
        author_patterns = [
            r'Authors?:\s*([^\n]+)',
            r'By\s+([^\n]+)',
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)*)',
        ]

        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, self.text_content)

        lines = self.text_content.split('\n')[:20]
        authors_found = []
        
        for line in lines:
            line = line.strip()
            # Buscar líneas que contengan nombres de autores
            if re.search(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)*$', line):
                # Separar múltiples autores
                authors_in_line = re.split(r',\s*|\s+and\s+', line)
                for author in authors_in_line:
                    author = author.strip()
                    if len(author) > 3 and author not in authors_found:
                        authors_found.append(author)
        
        # Crear objetos Actor
        for i, author_name in enumerate(authors_found):
            actor = Actor(name=author_name)
            # Asignar email si hay disponible
            if i < len(emails):
                actor.email = emails[i]
            self.actors.append(actor)
        
        return self.actors
    
    def extract_text_from_pdf(self):
        """Extrae texto del PDF usando pdfplumber"""
        if not self.pdf_path or not os.path.exists(self.pdf_path):
            return
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                text = ""
                for page in pdf.pages: 
                    text += page.extract_text() + "\n"
                self.text_content = text
        except Exception as e:
            print(f"Error al extraer texto de {self.pdf_path}: {e}")
            try:
                with open(self.pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages[:3]:
                        text += page.extract_text() + "\n"
                    self.text_content = text
            except Exception as e2:
                print(f"Error también con PyPDF2: {e2}")
    
    def process_pdf(self):
        """Procesa el PDF y extrae toda la información"""
        self.extract_text_from_pdf()
        
        self.search_doi()
        if not self.doi:
            self.search_arxiv()

        if not self.title:
            self.extract_title()

        if not self.actors:
            self.extract_actors()
    
    def to_dict(self):
        return {
            'title': self.title,
            'pdf_path': self.pdf_path,
            'doi': self.doi,
            'actors': [actor.to_dict() for actor in self.actors],
            'abstract': self.abstract,
            'journal': self.journal,
            'year': self.year,
            'publisher': self.publisher,
            'api_metadata': self.api_metadata
        }
    
    def __str__(self):
        return f"PdfMetaData(title='{self.title}', actors={len(self.actors)}, doi='{self.doi}')"


def process_pdfs_folder(folder_path: str = "pdfs_papers") -> List[PdfMetaData]:
    """Procesa todos los PDFs en una carpeta"""
    results = []
    
    if not os.path.exists(folder_path):
        print(f"La carpeta {folder_path} no existe")
        return results
    
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No se encontraron archivos PDF en {folder_path}")
        return results
    
    print(f"Procesando {len(pdf_files)} archivos PDF...")
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(folder_path, pdf_file)
        print(f"Procesando: {pdf_file}")
        
        metadata = PdfMetaData(pdf_path)
        metadata.process_pdf()
        results.append(metadata)     
        time.sleep(1)
    
    return results


def save_results_to_json(results: List[PdfMetaData], output_file: str = "pdf_metadata.json"):
    """Guarda los resultados en un archivo JSON"""
    data = [result.to_dict() for result in results]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Resultados guardados en {output_file}")


def get_metadata_from_doi(doi: str) -> dict:
    """
    Obtiene metadatos desde la API de CrossRef usando el DOI
    """
    if not doi:
        return {}
    
    clean_doi = doi.strip()
    if clean_doi.startswith('https://doi.org/'):
        clean_doi = clean_doi.replace('https://doi.org/', '')
    elif clean_doi.startswith('http://doi.org/'):
        clean_doi = clean_doi.replace('http://doi.org/', '')
    
    url = f"https://api.crossref.org/works/{clean_doi}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        print(f"  Consultando API de CrossRef para DOI: {clean_doi}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            work = data.get('message', {})
            
            metadata = {
                'title': '',
                'authors': [],
                'journal': '',
                'year': '',
                'abstract': '',
                'url': '',
                'doi': clean_doi,
                'type': work.get('type', ''),
                'publisher': work.get('publisher', ''),
                'subject': work.get('subject', [])
            }
            
            titles = work.get('title', [])
            if titles:
                metadata['title'] = titles[0]
            
            # Autores
            authors = work.get('author', [])
            for author in authors:
                given = author.get('given', '')
                family = author.get('family', '')
                name = f"{given} {family}".strip()
                if name:
                    metadata['authors'].append({
                        'name': name,
                        'given': given,
                        'family': family,
                        'orcid': author.get('ORCID', ''),
                        'affiliation': author.get('affiliation', [])
                    })
            
            container_titles = work.get('container-title', [])
            if container_titles:
                metadata['journal'] = container_titles[0]
            
       
            published = work.get('published-print') or work.get('published-online')
            if published and 'date-parts' in published:
                date_parts = published['date-parts'][0]
                if date_parts:
                    metadata['year'] = str(date_parts[0])
       
            urls = work.get('URL', [])
            if urls:
                metadata['url'] = urls[0] if isinstance(urls, list) else urls
            
            print(f"  ✓ Metadatos obtenidos: {metadata['title'][:50]}...")
            print(f"  ✓ Autores encontrados: {len(metadata['authors'])}")
            
            return metadata
            
        else:
            print(f"  ✗ Error en API: {response.status_code}")
            return {}
            
    except requests.RequestException as e:
        print(f"  ✗ Error de conexión: {e}")
        return {}
    except Exception as e:
        print(f"  ✗ Error procesando respuesta: {e}")
        return {}


if __name__ == "__main__":
    results = process_pdfs_folder()

    save_results_to_json(results)

    print(f"\n=== RESUMEN ===")
    print(f"Total de PDFs procesados: {len(results)}")
    print(f"PDFs con DOI: {sum(1 for r in results if r.search_doi())}")
    print(f"Total de autores encontrados: {sum(len(r.actors) for r in results)}")
    
    print("\n=== EJEMPLOS ===")
    for i, result in enumerate(results[:3]):  
        print(f"\nPDF {i+1}:")
        print(f"  Título: {result.title}")
        print(f"  Autores: {[actor.name for actor in result.actors]}")
        print(f"  DOI: {result.doi if result.doi else 'No encontrado'}")