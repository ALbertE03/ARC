import requests
import json
from queue import Queue
import threading
import time
import os
import pandas as pd


df = pd.read_csv("./data/works-2025-07-15T13-00-19.csv")

JSON_PATH = "./data/openalex_data.json"
MAX_THREADS = 5
REQUEST_RATE = 1
SAVE_POINTS = [0.5, 1.0]

os.makedirs("./data", exist_ok=True)
try:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        existing_data = json.load(f)
    existing_ids = {work["id"].split("/")[-1] for work in existing_data}
    print(f"🔍 {len(existing_data)} records loaded previously")
except FileNotFoundError:
    existing_data = []
    existing_ids = set()
    print("🆕 Creating new JSON file")


json_lock = threading.Lock()
progress_lock = threading.Lock()
total_processed = 0
total_to_process = 0
new_data_buffer = []
last_save_point = 0


def save_data():
    global existing_data, new_data_buffer
    with json_lock:
        existing_data.extend(new_data_buffer)
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
        new_data_buffer = []
        print(f"💾 Data saved. Current total: {len(existing_data)} records")


def check_save_point(progress):
    global last_save_point
    for point in SAVE_POINTS:
        if last_save_point < point <= progress:
            save_data()
            last_save_point = point
            return True
    return False


def worker(queue):
    global total_processed, new_data_buffer

    while not queue.empty():
        start_time = time.time()
        id = queue.get()

        url = f"https://api.openalex.org/works/{id}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            work_data = response.json()

            with json_lock:
                new_data_buffer.append(work_data)
                existing_ids.add(id)

            with progress_lock:
                total_processed += 1
                progress = total_processed / total_to_process
                elapsed = time.time() - start_time
                print(
                    f"✅ [{threading.current_thread().name}] {id} processed | "
                    f"Progress: {total_processed}/{total_to_process} "
                    f"({progress*100:.1f}%) | "
                    f"Time: {elapsed:.2f}s"
                )

                check_save_point(progress)

        except requests.exceptions.RequestException as e:
            with progress_lock:
                print(
                    f"❌ [{threading.current_thread().name}] Error with {id}: {str(e)}"
                )
                queue.put(id)
        except Exception as e:
            with progress_lock:
                print(
                    f"⚠️ [{threading.current_thread().name}] Unexpected error with {id}: {str(e)}"
                )

        processing_time = time.time() - start_time
        sleep_time = max(0, 1.0 - processing_time)
        time.sleep(sleep_time)

        queue.task_done()


queue = Queue()
for _, row in df.iterrows():
    id = row["id"].split("/")[-1]
    if id not in existing_ids:
        queue.put(id)

total_to_process = queue.qsize()
print(f"🚀 Starting download of {total_to_process} new records")


threads = []
for i in range(min(MAX_THREADS, queue.qsize())):
    t = threading.Thread(target=worker, args=(queue,), name=f"Worker-{i+1}")
    t.daemon = True
    t.start()
    threads.append(t)


try:
    while any(t.is_alive() for t in threads):
        time.sleep(5)
        with progress_lock:
            remaining = queue.qsize()
            processed = total_processed
            progress = processed / total_to_process
            print(
                f"\n📊 Current progress: {processed}/{total_to_process} "
                f"({progress*100:.1f}%) | "
                f"Remaining: {remaining} | "
                f"Active threads: {sum(1 for t in threads if t.is_alive())}\n"
            )
            check_save_point(progress)

except KeyboardInterrupt:
    print("\n🛑 Interruption received, saving collected data...")
    save_data()


queue.join()
save_data()
print(f"\n🎉 Process completed! JSON updated at '{JSON_PATH}'")
print(f"📂 Total records: {len(existing_data)}")