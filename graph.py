import os
import re
import pdfplumber
import networkx as nx
from pyvis.network import Network
from google import genai
from trie import Trie


class Article:
    def __init__(self, pdf_folder, API_TOKEN):
        self.API_TOKEN = API_TOKEN
        self.client = genai.Client(api_key=API_TOKEN)
        self.pdf_folder = pdf_folder
        self.name_trie = Trie()
        self.last_name_trie = Trie()
        self.name_to_last_names = {}

    def extract_text_before_abstract(self, text):
        abstract_match = re.search(r"\bAbstract\b", text, re.IGNORECASE)
        return text[: abstract_match.start()] if abstract_match else text

    def extract_text_from_pdf(self, pdf_path):
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text
                    if re.search(r"\bAbstract\b", page_text, re.IGNORECASE):
                        text = self.extract_text_before_abstract(text)
                        break
        except Exception as e:
            print(f"Error al procesar el archivo {pdf_path}: {e}")

        return text

    def normalize_name(self, name):
        name = name.lower()
        name = re.sub(r"\b(dr|prof|mr|mrs|ms)\.?\s*", "", name)
        return name.strip()

    def extract_data_with_api(self, prompt):
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text

    def split_name(self, full_name):
        parts = full_name.split()
        if len(parts) == 1:
            return parts[0], []
        else:
            return (
                parts[0],
                parts[1:],
            )

    def find_author_match(self, first_name, last_names):
        if not last_names:
            return False
        found, stored_last_names = self.name_trie.search(first_name)
        if found:
            for stored_last_name in stored_last_names:
                if stored_last_name in last_names:
                    return True

        if self.last_name_trie.starts_with(last_names[0]):
            if self.name_trie.starts_with(first_name[0]):
                return True

        return False

    def process_pdfs_in_batch(self, batch_size=10):
        G = nx.DiGraph()
        index = 0
        pdf_files = [f for f in os.listdir(self.pdf_folder) if f.endswith(".pdf")]
        total_files = len(pdf_files)
        print(f"Total de archivos PDF encontrados: {total_files}")

        processed_files = 0
        failed_files = 0

        for i in range(0, total_files, batch_size):
            batch = pdf_files[i : i + batch_size]
            batch_texts = []

            for pdf_file in batch:
                pdf_path = os.path.join(self.pdf_folder, pdf_file)
                print(f"Procesando archivo: {pdf_file}")

                try:
                    text = self.extract_text_from_pdf(pdf_path)
                    batch_texts.append(text)
                    processed_files += 1
                except Exception as e:
                    print(f"Error al procesar el archivo {pdf_file}: {e}")
                    failed_files += 1
                    continue

            if not batch_texts:
                print("No se pudo extraer texto de ningún archivo en este lote.")
                continue

            prompt = "Extrae el título y todos los autores de los siguientes textos de artículos científicos:\n"
            for idx, text in enumerate(batch_texts):
                prompt += f"\nArtículo {idx + 1}:\n{text}\n"

            prompt += "\nDevuelve el título y los autores en este formato para cada artículo:\n"
            prompt += "Artículo <número>:\nTítulo: <título del artículo>\nAutores: <lista de autores separados por coma,al final de los nombre pon pon un punto y un espacio y los apellidos separados por espacios, en caso de un autor tener dos nombres poner el punto despues del segundo nombre>Ejemplo:Artículo 1- Título: Machine Learning Approaches to Climate Modeling\n -Autores: John A. Smith, María. García López, Chen. Wei"

            response = self.extract_data_with_api(prompt).strip()
            print(f"Título y autores extraídos:\n{response}")

            articles = re.split(r"Artículo \d+:", response)
            for article in articles:
                if not article.strip():
                    continue

                title_match = re.search(r"Título:\s*(.+)", article)
                authors_match = re.search(r"Autores:\s*(.+)", article)

                if title_match and authors_match:
                    title = title_match.group(1).strip()
                    authors = [
                        author.strip() for author in authors_match.group(1).split(",")
                    ]
                    G.add_node(
                        f"artículo:{index}",
                        type="article",
                        color="lightgreen",
                        title=title,
                    )
                    for author in authors:
                        first_name, last_names = self.split_name(author)
                        normalized_first_name = self.normalize_name(first_name)
                        normalized_last_names = [
                            self.normalize_name(last_name) for last_name in last_names
                        ]

                        if not self.find_author_match(
                            normalized_first_name, normalized_last_names
                        ):
                            self.name_trie.insert(
                                normalized_first_name, normalized_last_names
                            )
                            for last_name in normalized_last_names:
                                self.last_name_trie.insert(last_name)
                            self.name_to_last_names[normalized_first_name] = (
                                normalized_last_names
                            )

                            author_node = f"{normalized_first_name} {' '.join(normalized_last_names)}"
                            G.add_node(
                                author_node,
                                type="author",
                                color="lightblue",
                            )
                        else:
                            author_node = f"{normalized_first_name} {' '.join(normalized_last_names)}"

                        G.add_edge(author_node, f"artículo:{index}", relacion="author")

                    index += 1
                    print(f"Procesado artículo {index}: {title}")

        print(f"\nResumen de procesamiento:")
        print(f"- Archivos procesados correctamente: {processed_files}")
        print(f"- Archivos con errores: {failed_files}")
        print(f"- Total de artículos añadidos al grafo: {index}")

        return G

    def main(self):
        if not os.path.exists("grafo.graphml"):
            G = self.process_pdfs_in_batch()
            nx.write_graphml(G, "grafo.graphml")

        G = nx.read_graphml("grafo.graphml")
        net = Network(
            notebook=True,
            height="100%",
            width="100%",
            bgcolor="#222222",
            font_color="white",
        )
        net.from_nx(G)
        net.set_options(
            """
        {
            "nodes": {
                "font": {
                    "size": 12,
                    "color": "white"
                }
            },
            "edges": {
                "color": {
                    "inherit": true
                },
                "smooth": false
            },
            "physics": {
                "enabled": true,
                "barnesHut": {
                    "gravitationalConstant": -10000,
                    "centralGravity": 0.5,
                    "springLength": 250,
                    "springConstant": 0.04,
                    "damping": 0.09,
                    "avoidOverlap": 0.1
                },
                "minVelocity": 0.75
            }
        }
        """
        )

        net.show("grafo.html")


if __name__ == "__main__":
    art = Article("articles", os.getenv("token"))
    art.main()
