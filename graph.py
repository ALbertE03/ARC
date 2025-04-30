import os
import re
import networkx as nx
from pyvis.network import Network
import pdfplumber
import requests
import nltk
from datetime import datetime

nltk.download("punkt_tab")


class Article:
    def __init__(self, pdf_folder, model, JAN_API_URL="http://localhost:1337/v1"):
        self.JAN_API_URL = JAN_API_URL
        self.pdf_folder = pdf_folder
        self.current_graph = nx.Graph()
        self.model = model
        self.graph_dir = "graph"
        self.visualization_dir = "visu"
        self.processed_files = set()

        os.makedirs(self.graph_dir, exist_ok=True)
        os.makedirs(self.visualization_dir, exist_ok=True)

        self.load_existing_graph()

    def load_existing_graph(self):
        """Carga el grafo existente y la lista de archivos procesados"""
        graph_path = os.path.join(self.graph_dir, "graph.graphml")
        processed_files_path = os.path.join(self.graph_dir, "processed_files.txt")

        if os.path.exists(graph_path):
            self.current_graph = nx.read_graphml(graph_path)
            print("Grafo existente cargado con éxito")

            if os.path.exists(processed_files_path):
                with open(processed_files_path, "r") as f:
                    self.processed_files = set(f.read().splitlines())

    def save_graph_and_processed_files(self):
        """Guarda el grafo y la lista de archivos procesados"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        main_graph_path = os.path.join(self.graph_dir, "graph.graphml")
        nx.write_graphml(self.current_graph, main_graph_path)

        backup_graph_path = os.path.join(
            self.graph_dir, f"graph_backup_{timestamp}.graphml"
        )
        nx.write_graphml(self.current_graph, backup_graph_path)

        processed_files_path = os.path.join(self.graph_dir, "processed_files.txt")
        with open(processed_files_path, "w") as f:
            f.write("\n".join(self.processed_files))

        print(f"Grafo guardado en {main_graph_path} (backup en {backup_graph_path})")

    def query_local_llm(self, prompt):
        """Consulta al modelo LLM local en JAN"""
        try:
            headers = {
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 30000,
            }

            response = requests.post(
                f"{self.JAN_API_URL}/chat/completions",
                headers=headers,
                json=payload,
            )

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                print(
                    f"Error en la API local: {response.status_code} - {response.text}"
                )
                return None
        except Exception as e:
            print(f"Error al conectar con JAN: {str(e)}")
            return None

    def normalize_name(self, name):
        return " ".join(list(nltk.word_tokenize(name.lower())))

    def is_same_author(self, name1, name2):
        """Usa el LLM para determinar si dos nombres son el mismo autor"""
        prompt = (
            f"¿compara el Nombre 1 con la lista de nombres de autores académicos, Nombre 1 está en la lista nombres? \n"
            f"Nombre 1: {name1}\n"
            f"nombres: {name2}\n\n"
            f"Considera:\n"
            f"- Iniciales vs nombres completos\n"
            f"- Órdenes de nombres invertidos\n"
            f"- Variaciones culturales\n"
            f"- Títulos (Dr., Prof., etc.)\n\n"
            f"Responde SOLO con el nombre de la lista de nombres que sea el mismo que Nombre 1 y en caso de no estar pon NO"
            f"IMPORTANTE: NO AGREGAR OTRAS COSAS A LA RESPUESTA"
        )

        response = self.query_local_llm(prompt)
        if response is None:
            raise Exception("Error al consultar la API para comparar autores")
        return response if "NO" not in response.upper() else "NO"

    def find_existing_author(self, new_author, G):
        """Compara un nuevo autor con todos los autores existentes en el grafo"""
        normalized_new = self.normalize_name(new_author)
        a = []
        for node in G.nodes():
            if G.nodes[node].get("type") == "author":
                existing_name = G.nodes[node].get("label", "")
                normalized_existing = self.normalize_name(existing_name)
                if normalized_new == normalized_existing:
                    return node
                a.append(normalized_existing)

        if len(a) <= 30:
            node = self.is_same_author(new_author, a)
            if node != "NO":
                return node
        elif len(a) >= 30:
            c = a[: len(a) // 2]
            d = a[len(c) :]
            node1 = self.is_same_author(new_author, c)
            node2 = self.is_same_author(new_author, d)
            if node1 == "NO" and node2 == "NO":
                return None
            return node1 if node1 != "NO" else node2

        return None

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
            raise

        return text

    def extract_metadata(self, text):
        """Extrae título y autores usando el LLM local"""
        prompt = (
            "Extrae el título y todos los autores del siguiente texto de artículo científico.\n"
            "Devuélvelos en este formato exacto:\n"
            "TÍTULO: <título del artículo>\n"
            "AUTORES: <lista de autores separados por coma>\n\n"
            f"Texto:\n{text}"
        )

        response = self.query_local_llm(prompt)
        if not response:
            raise Exception("Error al extraer metadatos: respuesta de API vacía")

        title = None
        authors = []

        for line in response.split("\n"):
            if line.startswith("TÍTULO:"):
                title = line.replace("TÍTULO:", "").strip()
            elif line.startswith("AUTORES:"):
                authors = [a.strip() for a in line.replace("AUTORES:", "").split(",")]

        if not title or not authors:
            raise Exception("No se pudieron extraer título o autores del texto")

        return title, authors

    def process_pdfs(self):
        """Procesa todos los PDFs nuevos en la carpeta especificada"""
        G = self.current_graph
        pdf_files = [f for f in os.listdir(self.pdf_folder) if f.endswith(".pdf")]

        new_pdf_files = [f for f in pdf_files if f not in self.processed_files]

        if not new_pdf_files:
            print("No hay nuevos archivos PDF para procesar")
            return G

        for i, pdf_file in enumerate(new_pdf_files):
            print(f"\nProcesando archivo {i+1}/{len(new_pdf_files)}: {pdf_file}")
            pdf_path = os.path.join(self.pdf_folder, pdf_file)
            processed_successfully = False

            try:
                text = self.extract_text_from_pdf(pdf_path)
                if not text:
                    print("No se pudo extraer texto")
                    continue

                title, authors = self.extract_metadata(text)
                print(f"Título: {title}")
                print(f"Autores: {', '.join(authors)}")

                article_node = f"artículo:{pdf_file}"
                G.add_node(
                    article_node,
                    type="article",
                    color="lightgreen",
                    title=title,
                    pdf_file=pdf_file,
                )

                for author in authors:
                    if not author:
                        continue
                    try:
                        existing_node = self.find_existing_author(author, G)

                        if existing_node:
                            print(
                                f"Autor existente: {author} -> {G.nodes[existing_node]['label']}"
                            )
                            author_node = existing_node
                        else:
                            author_node = f"autor:{len([n for n in G.nodes() if n.startswith('autor:')])}"
                            G.add_node(
                                author_node,
                                type="author",
                                color="lightblue",
                                label=author,
                                normalized_name=self.normalize_name(author),
                            )
                            print(f"Nuevo autor añadido: {author}")

                        G.add_edge(author_node, article_node, relacion="author")

                    except Exception as e:
                        print(f"Error procesando autor {author}: {str(e)}")
                        if article_node in G:
                            G.remove_node(article_node)
                        raise

                processed_successfully = True

            except Exception as e:
                print(f"Error procesando archivo {pdf_file}: {str(e)}")
                article_node = f"artículo:{pdf_file}"
                if article_node in G:
                    G.remove_node(article_node)
            finally:
                if processed_successfully:
                    self.processed_files.add(pdf_file)
                    print(f"Archivo {pdf_file} procesado con éxito")
                else:
                    print(f"Archivo {pdf_file} NO se agregó al grafo por errores")

        self.save_graph_and_processed_files()
        return G

    def visualize_graph(self, G):
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
        visualization_path = os.path.join(self.visualization_dir, "graph.html")
        net.show(visualization_path)
        print(f"Visualización guardada en {visualization_path}")

    def main(self):
        G = self.process_pdfs()
        self.visualize_graph(G)


if __name__ == "__main__":
    article_processor = Article("articles", "Deepseek-R1-Distill-Qwen-7b")
    article_processor.main()
