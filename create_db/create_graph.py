import json
import pandas as pd
import networkx as nx
from tqdm import tqdm
from collections import defaultdict
import itertools
import unidecode


def normalize_name(name):
    """Normaliza nombres removiendo acentos, guiones y espacios extras"""
    if not isinstance(name, str):
        return ""
    name = unidecode.unidecode(name.lower().replace("-", " ").replace(".", " ").strip())
    return " ".join(name.split())


def consolidate_large_dataset(authors_data):
    print("\nCargando y preparando datos...")
    df = pd.DataFrame.from_dict(authors_data, orient="index")

    for col in ["works_count", "cited_by_count"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], downcast="integer")

    df["all_names"] = df.apply(
        lambda x: [normalize_name(x["display_name"])]
        + [normalize_name(n) for n in x.get("display_name_alternatives", [])],
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
            name_index[name].append(author_id)

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

    for name, group in tqdm(name_index.items(), desc="Nombres"):
        if len(group) > 1:
            for i, j in itertools.combinations(group, 2):
                if (i, j) not in seen_pairs:
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
        main_name = df.loc[main_author, "display_name"]
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


def find_author_improved(name, consolidated_data):
    """Busca autores considerando variaciones de nombres con guiones y acentos"""
    normalized_search = normalize_name(name)

    for author_id, author_data in consolidated_data.items():
        if normalized_search == normalize_name(author_data["display_name"]):
            return author_data

        for alt_name in author_data.get("display_name_alternatives", []):
            if normalized_search == normalize_name(alt_name):
                return author_data

    for author_id, author_data in consolidated_data.items():
        main_normalized = normalize_name(author_data["display_name"])
        if normalized_search in main_normalized or main_normalized in normalized_search:
            return author_data

        for alt_name in author_data.get("display_name_alternatives", []):
            alt_normalized = normalize_name(alt_name)
            if (
                normalized_search in alt_normalized
                or alt_normalized in normalized_search
            ):
                return author_data

    return None


print("Cargando datos...")
with open("data/openalex_authors_complete.json", "r") as f:
    data_authors = json.load(f)


print("\nIniciando consolidación optimizada...")
consolidated_authors, author_graph = consolidate_large_dataset(data_authors)

print(f"\nResumen:")
print(f"- Autores originales: {len(data_authors):,}")
print(f"- Autores consolidados: {len(consolidated_authors):,}")
print(f"- Reducción: {(1 - len(consolidated_authors)/len(data_authors))*100:.1f}%")

print("\nBuscando autores específicos:")


def show_author_info(name, consolidated_data):
    author = find_author_improved(name, consolidated_data)
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
        normalized_search = normalize_name(name)
        print("¿Quizás buscabas alguno de estos?")
        matches = []
        for author_id, author_data in consolidated_data.items():
            main_normalized = normalize_name(author_data["display_name"])
            if (
                normalized_search.split()[0] in main_normalized
                or normalized_search.split()[-1] in main_normalized
            ):
                matches.append(author_data["display_name"])
            if len(matches) >= 5:
                break
        for match in matches:
            print(f"- {match}")


show_author_info("Suilán Estévez-Velarde", consolidated_authors)
show_author_info("Alejandro Piad Morffis", consolidated_authors)
