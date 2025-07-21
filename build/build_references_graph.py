import networkx as nx
import json

def build_citation_graph(pdf_data):
    citation_graph = nx.DiGraph()

    reference_map = {}
    
    for pdf_id, pdf_info in pdf_data.items():
        citation_graph.add_node(pdf_id, 
                             title=pdf_info.get('title', ''),
                             authors=pdf_info.get('authors', []),
                             type='paper')

        for ref in pdf_info.get('references', []):
            
            ref_authors = ref.get('authors', [])
            ref_journal = ref.get('journal', [''])[0] if ref.get('journal') else ''
            ref_year = ref.get('year', [''])[0] if ref.get('year') else ''
            title = ref.get('title', [''])[0] if ref.get('title') else ''
            if (not ref_authors and not ref_journal and not title):
                continue
            
            ref_key = f"{'_'.join(ref_authors)}_{ref_journal}_{ref_year}_{title}"
            reference_map[ref_key] = ref
            
            if ref_key not in citation_graph:
                citation_graph.add_node(ref_key,
                                     title=title,
                                     authors=ref_authors,
                                     journal=ref_journal,
                                     year=ref_year,
                                     type='reference')
            
            citation_graph.add_edge(pdf_id, ref_key)

    return citation_graph, reference_map


with open('./data/extract_ref.json') as f:
    pdf_data = json.load(f)


citation_graph,ref = build_citation_graph(pdf_data)


print(f"Número de nodos: {citation_graph.number_of_nodes()}")
print(f"Número de aristas: {citation_graph.number_of_edges()}")
print(f"Densidad: {nx.density(citation_graph):.4f}")


in_degree = citation_graph.in_degree()
top_cited = sorted(in_degree, key=lambda x: x[1], reverse=True)[:5]
print("\nPapers más citados:")
for node, count in top_cited:
    if citation_graph.nodes[node]['type'] == 'reference':
        print(f"- {node}: {count} citas")
        print(f"  Autores: {', '.join(citation_graph.nodes[node]['authors'][:3])}...")
        print(f"  Journal: {citation_graph.nodes[node]['journal']} ({citation_graph.nodes[node]['year']})")