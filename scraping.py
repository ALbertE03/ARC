import os
import requests
import feedparser

# Configuración
query = "Graph"
max_results = 100
output_folder = "articles"


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


for entry in feed.entries:
    try:

        if not hasattr(entry, "title") or not entry.title:
            print("Error: Entrada sin título. Saltando...")
            continue

        title = entry.title.replace(" ", "_").replace(":", "").replace("/", "")
        pdf_url = None

        for link in entry.links:
            if link.get("title") == "pdf":
                pdf_url = link.href
                break
        if pdf_url:
            pdf_response = requests.get(pdf_url)
            if pdf_response.status_code == 200:
                pdf_name = f"{title}.pdf"
                pdf_path = os.path.join(output_folder, pdf_name)
                with open(pdf_path, "wb") as pdf_file:
                    pdf_file.write(pdf_response.content)
                print(f"Descargado: {pdf_name}")
            else:
                print(f"Error al descargar {title}: Código {pdf_response.status_code}")
        else:
            print(f"No se encontró enlace PDF para: {title}")
    except Exception as e:
        print(f"Error al procesar una entrada: {str(e)}")

print("Descarga completada.")
