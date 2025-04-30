import os
import requests
import feedparser
import json
from datetime import datetime

# Configuración
query = "Graph"
max_results = 100
output_folder = "articles"
json_filename = "arxiv_articles.json"

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

base_url = "http://export.arxiv.org/api/query?"
search_query = f"search_query=all:{query}"
start = 0
max_results_param = f"max_results={max_results}"
sort_by = "sortBy=submittedDate"
sort_order = "sortOrder=descending"

url = (
    f"{base_url}{search_query}&{sort_by}&{sort_order}&{max_results_param}&start={start}"
)

response = requests.get(url)
feed = feedparser.parse(response.content)

articles_data = []

for entry in feed.entries:
    try:
        if not hasattr(entry, "title") or not entry.title:
            print("Error: Entrada sin título. Saltando...")
            continue

        title = entry.title
        article_id = entry.id.split("/")[-1]
        published = entry.published
        summary = entry.summary if hasattr(entry, "summary") else ""

        authors = (
            [
                {
                    "name": author.name,
                    "affiliation": author.get("arxiv:affiliation", ""),
                }
                for author in entry.authors
            ]
            if hasattr(entry, "authors")
            else []
        )

        pdf_url = None
        for link in entry.links:
            if link.get("title") == "pdf":
                pdf_url = link.href
                break

        article_info = {
            "id": article_id,
            "title": title,
            "authors": authors,
            "published": published,
            "summary": summary,
            "pdf_url": pdf_url,
            "arxiv_url": entry.id,
            "download_path": None,
        }

        if pdf_url:
            safe_title = title.replace(" ", "_").replace(":", "").replace("/", "")
            pdf_name = f"{safe_title}.pdf"
            pdf_path = os.path.join(output_folder, pdf_name)

            try:
                pdf_response = requests.get(pdf_url)
                if pdf_response.status_code == 200:
                    with open(pdf_path, "wb") as pdf_file:
                        pdf_file.write(pdf_response.content)
                    article_info["download_path"] = pdf_path
                    print(f"Descargado: {pdf_name}")
                else:
                    print(
                        f"Error al descargar {title}: Código {pdf_response.status_code}"
                    )
            except Exception as download_error:
                print(f"Error al descargar {title}: {str(download_error)}")

        articles_data.append(article_info)

    except Exception as e:
        print(f"Error al procesar una entrada: {str(e)}")


try:
    with open(json_filename, "w", encoding="utf-8") as json_file:
        json.dump(articles_data, json_file, ensure_ascii=False, indent=4)
    print(f"\nDatos guardados en {json_filename}")
except Exception as e:
    print(f"Error al guardar el archivo JSON: {str(e)}")

print("Proceso completado.")
