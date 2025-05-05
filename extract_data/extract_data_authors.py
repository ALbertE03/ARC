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
        """Load existing data from JSON file if it exists"""
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data)} existing authors from file")
                    return data
                except json.JSONDecodeError:
                    logger.warning(
                        "File exists but is not valid JSON, creating a new one"
                    )
                    return {}
        return {}

    def fetch_author(self, author_id):
        """Gets complete author data from the API"""
        # Check if author already exists
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
                logger.warning(f"Error {response.status_code} for author {author_id}")
                with self.lock:
                    self.failed_requests += 1
        except Exception as e:
            logger.error(f"Exception while fetching author {author_id}: {str(e)}")
            with self.lock:
                self.failed_requests += 1
        return None

    def log_progress(self):
        """Displays current progress"""
        elapsed = time.time() - self.start_time
        processed = self.processed_count
        remaining = self.total_authors - processed
        if processed > 0:
            time_per_author = elapsed / processed
            eta = remaining * time_per_author
        else:
            eta = 0

        logger.info(
            f"Processed: {processed}/{self.total_authors} "
            f"({processed/self.total_authors:.1%}) | "
            f"New: {self.new_authors_added} | "
            f"Failed: {self.failed_requests} | "
            f"ETA: {eta:.1f}s"
        )

    def save_to_file(self):
        """Saves data to a JSON file"""
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.author_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Data saved to {OUTPUT_FILE}")


class Worker(Thread):
    """Worker thread to process authors"""

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
                logger.error(f"Error in worker for {author_id}: {str(e)}")
            finally:
                self.queue.task_done()


def get_unique_authors(input_file):
    """Gets unique authors from the data file"""
    with open(input_file, "r") as f:
        data = json.load(f)

    authors = set()
    for work in data:
        for authorship in work.get("authorships", []):
            author_id = authorship.get("author", {}).get("id", "")
            if author_id:
                authors.add(author_id.split("/")[-1])

    logger.info(f"Found {len(authors)} unique authors")
    return authors


def main():
    logger.info("Starting author data extraction")

    input_file = "data/openalex_data.json"
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return

    unique_authors = get_unique_authors(input_file)

    fetcher = AuthorDataFetcher()

    authors_to_process = [
        aid for aid in unique_authors if aid not in fetcher.author_data
    ]
    fetcher.total_authors = len(authors_to_process)

    logger.info(f"New authors to process: {len(authors_to_process)}")

    if not authors_to_process:
        logger.info("No new authors to process")
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

    logger.info("Process completed!")
    logger.info(f"Authors processed: {fetcher.processed_count}")
    logger.info(f"New authors added: {fetcher.new_authors_added}")
    logger.info(f"Failed requests: {fetcher.failed_requests}")


if __name__ == "__main__":
    main()
