import re
import json
from pathlib import Path
from datetime import datetime
from markitdown import MarkItDown
import spacy

class ImprovedAcademicExtractor:  
    def __init__(self):
        try:
            self.nlp = spacy.load("es_core_news_sm")
        except OSError:
            print("⚠️ Modelo de spaCy no encontrado. Usando patrones regex únicamente.")
            self.nlp = None
    
    def process_academic_paper(self, text):
        """
        Procesa el paper académico completo y extrae personas usando NLP
        """
        # Extraer solo texto antes del resumen
        abstract_keywords = ['resumen', 'abstract', 'summary']
        lines = text.split('\n')
        before_abstract = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in abstract_keywords):
                break
            before_abstract.append(line)
        
        header_text = '\n'.join(before_abstract)
        
        # Identificar personas usando spaCy
        persons = self.extract_persons(header_text)
        
        return {
            'text_before_abstract': header_text,
            'persons_found': persons
        }
    
    def extract_persons(self, text):
        """
        Extrae nombres de personas del texto usando NLP y patrones específicos
        """
        persons = []
        
        # Método 1: Usar spaCy si está disponible
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ == "PER":  # PER = Persona en spaCy
                    person_name = ent.text.strip()
                    persons.append(person_name)
        
        # Método 2: Patrones específicos para textos académicos
        academic_persons = self.extract_academic_patterns(text)
        for person in academic_persons:
            if person not in persons:
                persons.append(person)
        
        return persons
    
    def extract_academic_patterns(self, text):
        """
        Extrae nombres usando patrones específicos para textos académicos
        """
        persons = []
        
        # Patrón 1: Tablas markdown con nombres 
        lines = text.split('\n')
        for line in lines:
            if '|' in line and not line.strip().startswith('|---'):
                # Limpiar la línea de markdown
                clean_line = line.replace('|', ' ').strip()
                # Buscar patrones de nombre + apellido
                name_pattern = r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\b'
                matches = re.findall(name_pattern, clean_line)
                for match in matches:
                    # Filtrar palabras comunes que no son nombres
                    if not any(word.lower() in ['departamento', 'universidad', 'ciencias', 'matemáticas', 'computación', 'central', 'villas', 'cuba'] 
                             for word in match.split()):
                        persons.append(match.strip())
        
        # Patrón 2: Nombres seguidos de números (como Carlos García1)
        number_pattern = r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\d+\b'
        matches = re.findall(number_pattern, text)
        for match in matches:
            if match.strip() not in persons:
                persons.append(match.strip())
        
        # Patrón 3: Líneas que contienen solo nombres (formato académico típico)
        author_line_pattern = r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)$'
        for line in lines:
            clean_line = line.strip()
            if clean_line and len(clean_line.split()) <= 4:  # Máximo 4 palabras para nombres
                match = re.match(author_line_pattern, clean_line)
                if match and not any(word.lower() in ['revista', 'vol', 'nos', 'departamento', 'universidad'] 
                                   for word in match.group(1).split()):
                    persons.append(match.group(1))
        
        return persons


def process_pdf_improved(pdf_path):
    """
    Procesa el PDF con los patrones mejorados
    """
    md = MarkItDown(enable_plugins=False)
    extractor = ImprovedAcademicExtractor()
    
    try:
        with open(pdf_path, 'rb') as f:
            result = md.convert(f)
        
        extracted_info = extractor.process_academic_paper(result.text_content)
        return extracted_info
        
    except Exception as e:
        return {
            'filename': Path(pdf_path).name,
            'error': str(e),
            'processed_date': datetime.now().isoformat()
        }

def main():
    """
    Función principal - Procesa todos los PDFs en la carpeta
    """
    print("🚀 Extractor Académico Mejorado V2")
    print("=" * 50)

    # Directorio donde están los PDFs
    pdf_directory = Path(r"c:\Users\Anabel\OneDrive\Desktop\ARC\pdfs_papers")
    
    # Buscar todos los archivos PDF en el directorio
    pdf_files = list(pdf_directory.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No se encontraron archivos PDF en: {pdf_directory}")
        return
    
    print(f"📁 Encontrados {len(pdf_files)} archivos PDF")
    print("=" * 50)
    
    # Procesar cada PDF
    all_results = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n📄 Procesando {i}/{len(pdf_files)}: {pdf_path.name}")
        print("-" * 60)
        
        result = process_pdf_improved(str(pdf_path))
        
        if isinstance(result, dict) and 'error' not in result:
            print(f"✅ Archivo: {pdf_path.name}")
            
           
            
            # Mostrar personas encontradas
            persons = result.get('persons_found', [])
            if persons:
                print(f"👥 Personas encontradas ({len(persons)}):")
                for j, person in enumerate(persons, 1):
                    print(f"  {j}. {person}")
            else:
                print("👥 No se encontraron personas")
            
            # Agregar nombre del archivo al resultado
            result['filename'] = pdf_path.name
            all_results.append(result)
            
        else:
            print(f"❌ Error en {pdf_path.name}: {result.get('error', 'Error desconocido')}")

    # Guardar resultados en JSON
    output_file = pdf_directory / "resultados_extraccion.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"💾 Resultados guardados en: {output_file}")
    except Exception as e:
        print(f"⚠️ Error al guardar resultados: {e}")

if __name__ == "__main__":
    main()
