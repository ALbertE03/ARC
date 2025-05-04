import json
import pandas as pd
import networkx as nx
from tqdm import tqdm
from collections import defaultdict
import itertools
import unidecode
import matplotlib.pyplot as plt


def normalize_name(name):
    """Normaliza nombres para comparación exacta"""
    if not isinstance(name, str):
        return ""
    name = unidecode.unidecode(name.lower().replace("-", " ").replace(".", " ").strip())
    return name


def is_same_person(name1, name2):
    """Comparación para determinar si dos nombres son la misma persona"""
    if normalize_name(name1) == normalize_name(name2):
        return True

    name1_parts = normalize_name(name1).split()
    name2_parts = normalize_name(name2).split()

    if any(len(part) == 1 for part in name1_parts + name2_parts):
        if len(name1_parts) > 1 and len(name2_parts) > 1:
            return name1_parts[-1] == name2_parts[-1]

    return False


def consolidate_large_dataset(authors_data):
    print("\Preparando datos...", flush=True)
    df = pd.DataFrame.from_dict(authors_data, orient="index")

    for col in ["works_count", "cited_by_count"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], downcast="integer")

    df["all_names"] = df.apply(
        lambda x: [x["display_name"]] + x.get("display_name_alternatives", []),
        axis=1,
    )

    G = nx.Graph()

    print("\nAñadiendo autores al grafo...")
    for author_id, row in tqdm(df.iterrows(), total=len(df), desc="Nodos"):
        G.add_node(author_id, **row.to_dict())

    print("\nConstruyendo índices para búsquedas rápidas...")
    orcid_index = defaultdict(list)
    name_index = defaultdict(list)

    for author_id, row in tqdm(df.iterrows(), total=len(df), desc="Indexando"):
        if pd.notna(row.get("orcid")):
            orcid_index[row["orcid"]].append(author_id)

        for name in row["all_names"]:
            name_index[normalize_name(name)].append(author_id)

    def connect_group(items, reason):
        for i, j in itertools.combinations(items, 2):
            if not G.has_edge(i, j):
                G.add_edge(i, j, reason=reason)

    print("\nConectando autores con mismo ORCID...")
    for orcid, group in tqdm(orcid_index.items(), desc="ORCID"):
        if len(group) > 1:
            connect_group(group, "same_orcid")

    print("\nConectando autores con nombres similares...")
    seen_pairs = set()

    for norm_name, group in tqdm(name_index.items(), desc="Nombres"):
        if len(group) > 1:
            for i, j in itertools.combinations(group, 2):
                if (i, j) not in seen_pairs:
                    i_names = df.loc[i, "all_names"]
                    j_names = df.loc[j, "all_names"]

                    match_found = False
                    for name_i in i_names:
                        for name_j in j_names:
                            if is_same_person(name_i, name_j):
                                match_found = True
                                break
                        if match_found:
                            break

                    if match_found:
                        G.add_edge(i, j, reason="name_match")
                        seen_pairs.add((i, j))
                        seen_pairs.add((j, i))

    print("\nIdentificando grupos de autores únicos...")
    components = list(nx.connected_components(G))

    print("\nConsolidando autores...")
    consolidated = {}

    for component in tqdm(components, desc="Consolidando"):
        component_list = list(component)
        main_author = max(component_list, key=lambda x: df.loc[x].get("works_count", 0))

        combined = df.loc[main_author].to_dict()
        combined["alias_ids"] = [x for x in component_list if x != main_author]

        all_names = set()
        if isinstance(combined.get("display_name_alternatives"), list):
            all_names.update(combined["display_name_alternatives"])

        for author_id in component_list:
            if author_id != main_author:
                all_names.add(df.loc[author_id, "display_name"])
                alts = df.loc[author_id].get("display_name_alternatives", [])
                if isinstance(alts, list):
                    all_names.update(alts)

        combined["display_name_alternatives"] = list(all_names)
        combined["works_count"] = df.loc[component_list, "works_count"].sum()
        combined["cited_by_count"] = df.loc[component_list, "cited_by_count"].sum()

        consolidated[main_author] = combined

    return consolidated, G


def find_author_exact(name, consolidated_data):
    """Búsqueda exacta considerando todas las variantes del nombre"""
    normalized_search = normalize_name(name)

    for author_id, author_data in consolidated_data.items():
        if normalized_search == normalize_name(author_data["display_name"]):
            return author_data

        for alt_name in author_data.get("display_name_alternatives", []):
            if normalized_search == normalize_name(alt_name):
                return author_data

    return None


print("Cargando datos de autores...")
with open("data/openalex_authors_complete.json", "r") as f:
    data_authors = json.load(f)

print("\nIniciando consolidación optimizada...", flush=True)
consolidated_authors, author_graph = consolidate_large_dataset(data_authors)

print(f"\nResumen:")
print(f"- Autores originales: {len(data_authors):,}")
print(f"- Autores consolidados: {len(consolidated_authors):,}")
print(f"- Reducción: {(1 - len(consolidated_authors)/len(data_authors))*100:.1f}%")


def show_author_info_exact(name, consolidated_data):
    author = find_author_exact(name, consolidated_data)
    if author:
        print(f"\n{name}:")
        print(f"Nombre principal: {author['display_name']}")
        print(f"Trabajos: {author['works_count']}")
        print(f"Citaciones: {author['cited_by_count']}")
        print(f"Aliases: {len(author['alias_ids'])} autores")
        if author["alias_ids"]:
            print("Nombres alternativos:", author["display_name_alternatives"])
    else:
        print(f"\nNo se encontró a {name} en los datos consolidados")


"""show_author_info_exact("Suilán Estevez Velarde", consolidated_authors)
show_author_info_exact("yudivian almeida cruz", consolidated_authors)
show_author_info_exact("wilfredo morales", consolidated_authors)
show_author_info_exact("idania urrutia romani", consolidated_authors)
show_author_info_exact("Wilfredo Martín Casapía Morales", consolidated_authors)
"""

print("\nCargando datos de articulos...", flush=True)
with open("data/openalex_data.json", "r") as f:
    data_work = json.load(f)

G = nx.Graph()
for work in tqdm(data_work, desc="Añadienndo articulos"):
    work_id = work.get("id", " ").split("/")[-1]
    G.add_node(
        work_id, **{k: v for (k, v) in work.items() if k != "id"}, type_node="Work"
    )

for author_id, author_data in tqdm(
    consolidated_authors.items(), desc="Añadienndo Autores"
):
    G.add_node(author_id, **author_data, type_node="Author")

for work in tqdm(data_work, desc="Añadienndo enlaces"):
    work_id = work.get("id", "").split("/")[-1]
    if work_id not in G:
        continue

    for authorship in work.get("authorships", []):
        author_id = authorship.get("author", {}).get("id", "").split("/")[-1]

        if author_id in consolidated_authors:
            G.add_edge(author_id, work_id, type="authored")
        else:
            for consolidated_id, data in consolidated_authors.items():
                if author_id in data.get("alias_ids", []):
                    G.add_edge(consolidated_id, work_id, type="authored")
                    break

print(f"- Total nodos: {G.number_of_nodes()}")
print(f"- Total aristas: {G.number_of_edges()}")
print(f"- Autores: {len(consolidated_authors)}")
print(f"- Articulos: {len(data_work)}")
