import json
import os
import time
import requests
from threading import Thread, Lock
from queue import Queue
import logging
from dotenv import load_dotenv


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

load_dotenv()


OPENALEX_API_URL = "https://api.openalex.org/authors/{}"
OUTPUT_FILE = "data/openalex_authors_complete.json"
MAX_THREADS = 5


class AuthorDataFetcher:
    def __init__(self):
        self.author_data = self.load_existing_data()
        self.lock = Lock()
        self.processed_count = 0
        self.total_authors = 0
        self.start_time = time.time()
        self.failed_requests = 0
        self.new_authors_added = 0

    def load_existing_data(self):
        """Carga los datos existentes del archivo JSON si existe"""
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    logger.info(f"Cargados {len(data)} autores existentes del archivo")
                    return data
                except json.JSONDecodeError:
                    logger.warning(
                        "El archivo existe pero no es un JSON válido, creando uno nuevo"
                    )
                    return {}
        return {}

    def fetch_author(self, author_id):
        """Obtiene los datos completos de un autor desde la API"""
        # Verificar si el autor ya existe
        if author_id in self.author_data:
            with self.lock:
                self.processed_count += 1
                self.log_progress()
            return None

        try:
            url = OPENALEX_API_URL.format(author_id)
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                with self.lock:
                    self.author_data[author_id] = data
                    self.processed_count += 1
                    self.new_authors_added += 1
                    self.log_progress()
                return data
            else:
                logger.warning(f"Error {response.status_code} para autor {author_id}")
                with self.lock:
                    self.failed_requests += 1
        except Exception as e:
            logger.error(f"Excepción al obtener autor {author_id}: {str(e)}")
            with self.lock:
                self.failed_requests += 1
        return None

    def log_progress(self):
        """Muestra el progreso actual"""
        elapsed = time.time() - self.start_time
        processed = self.processed_count
        remaining = self.total_authors - processed
        if processed > 0:
            time_per_author = elapsed / processed
            eta = remaining * time_per_author
        else:
            eta = 0

        logger.info(
            f"Procesados: {processed}/{self.total_authors} "
            f"({processed/self.total_authors:.1%}) | "
            f"Nuevos: {self.new_authors_added} | "
            f"Fallidos: {self.failed_requests} | "
            f"ETA: {eta:.1f}s"
        )

    def save_to_file(self):
        """Guarda los datos en un archivo JSON"""
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.author_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Datos guardados en {OUTPUT_FILE}")


class Worker(Thread):
    """Hilo worker para procesar autores"""

    def __init__(self, queue, fetcher):
        Thread.__init__(self)
        self.queue = queue
        self.fetcher = fetcher

    def run(self):
        while True:
            author_id = self.queue.get()
            try:
                self.fetcher.fetch_author(author_id)
            except Exception as e:
                logger.error(f"Error en worker para {author_id}: {str(e)}")
            finally:
                self.queue.task_done()


def get_unique_authors(input_file):
    """Obtiene autores únicos desde el archivo de datos"""
    with open(input_file, "r") as f:
        data = json.load(f)

    authors = set()
    for work in data:
        for authorship in work.get("authorships", []):
            author_id = authorship.get("author", {}).get("id", "")
            if author_id:
                authors.add(author_id.split("/")[-1])

    logger.info(f"Encontrados {len(authors)} autores únicos")
    return authors


def main():
    logger.info("Iniciando extracción de datos de autores")

    input_file = "data/openalex_data.json"
    if not os.path.exists(input_file):
        logger.error(f"Archivo de entrada no encontrado: {input_file}")
        return

    unique_authors = get_unique_authors(input_file)

    fetcher = AuthorDataFetcher()

    authors_to_process = [
        aid for aid in unique_authors if aid not in fetcher.author_data
    ]
    fetcher.total_authors = len(authors_to_process)

    logger.info(f"Autores nuevos a procesar: {len(authors_to_process)}")

    if not authors_to_process:
        logger.info("No hay autores nuevos para procesar")
        return

    queue = Queue()
    for _ in range(MAX_THREADS):
        worker = Worker(queue, fetcher)
        worker.daemon = True
        worker.start()

    for author_id in authors_to_process:
        queue.put(author_id)

    queue.join()

    fetcher.save_to_file()

    logger.info("Proceso completado!")
    logger.info(f"Autores procesados: {fetcher.processed_count}")
    logger.info(f"Nuevos autores agregados: {fetcher.new_authors_added}")
    logger.info(f"Requests fallidos: {fetcher.failed_requests}")


if __name__ == "__main__":
    main()
