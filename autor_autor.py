import networkx as nx
from itertools import combinations
from collections import defaultdict
import json
def crear_grafo_autor_autor(ruta_subgrafo_articulos, ruta_salida=None):
    """
    Crea un grafo autor-autor donde dos autores están conectados si y solo si 
    tienen un artículo en común.
    
    Args:
        ruta_subgrafo_articulos (str): Ruta al archivo GraphML del subgrafo con artículos
        ruta_salida (str, opcional): Ruta donde guardar el grafo autor-autor
    
    Returns:
        networkx.Graph: Grafo autor-autor
    """
    print("Cargando subgrafo con artículos...")
    G_articulos = nx.read_graphml(ruta_subgrafo_articulos)
    
    # Crear el grafo autor-autor (no dirigido)
    G_autor_autor = nx.Graph()
    
    # Diccionario para almacenar los artículos de cada autor
    autor_articulos = defaultdict(set)
    
    print("Identificando autores y artículos...")
    # Identificar nodos de tipo artículo y sus autores
    articulos = []
    autores = set()
    
    for nodo in G_articulos.nodes():
        tipo_nodo = G_articulos.nodes[nodo].get('node_type', 'unknown')
        if tipo_nodo == 'article':
            articulos.append(nodo)
        else:
            # Asumimos que los nodos que no son artículos son autores
            autores.add(nodo)
    
    print(f"Encontrados {len(articulos)} artículos y {len(autores)} autores")
    
    # Para cada artículo, obtener sus autores
    print("Mapeando autores a artículos...")
    for articulo in articulos:
        autores_del_articulo = []
        for vecino in G_articulos.neighbors(articulo):
            if vecino in autores:
                autores_del_articulo.append(vecino)
                autor_articulos[vecino].add(articulo)
        
        # Agregar los autores al grafo autor-autor si no están ya
        for autor in autores_del_articulo:
            if not G_autor_autor.has_node(autor):
                # Copiar atributos del autor desde el grafo original
                atributos_autor = G_articulos.nodes[autor].copy()
                G_autor_autor.add_node(autor, **atributos_autor)
    
    print("Creando conexiones entre autores...")
    # Crear conexiones entre autores que comparten artículos
    conexiones_agregadas = 0
    
    for articulo in articulos:
        autores_del_articulo = [vecino for vecino in G_articulos.neighbors(articulo) 
                               if vecino in autores]
        
        # Crear todas las combinaciones posibles de pares de autores
        for autor1, autor2 in combinations(autores_del_articulo, 2):
            if not G_autor_autor.has_edge(autor1, autor2):
                # Agregar arista con información sobre artículos compartidos
                articulos_compartidos = autor_articulos[autor1].intersection(autor_articulos[autor2])
                G_autor_autor.add_edge(autor1, autor2, 
                                     articulos_compartidos=list(articulos_compartidos),
                                     num_articulos_compartidos=len(articulos_compartidos))
                conexiones_agregadas += 1
            else:
                # Si ya existe la arista, actualizar la lista de artículos compartidos
                articulos_compartidos = autor_articulos[autor1].intersection(autor_articulos[autor2])
                G_autor_autor[autor1][autor2]['articulos_compartidos'] = list(articulos_compartidos)
                G_autor_autor[autor1][autor2]['num_articulos_compartidos'] = len(articulos_compartidos)
    
    print(f"Grafo autor-autor creado con {G_autor_autor.number_of_nodes()} autores y {G_autor_autor.number_of_edges()} conexiones")
    print(f"Se agregaron {conexiones_agregadas} nuevas conexiones")
    for n, d in G_autor_autor.nodes(data=True):
        for k, v in list(d.items()):
            if v is None:
                d[k] = ""
            elif isinstance(v, (dict, list)):
                d[k] = json.dumps(v)

    for u, v, d in G_autor_autor.edges(data=True):
        for k, v2 in list(d.items()):
            if v2 is None:
                d[k] = ""
            elif isinstance(v2, (dict, list)):
                d[k] = json.dumps(v2)
    # Guardar el grafo si se especifica una ruta
    if ruta_salida:
        print(f"Guardando grafo autor-autor en {ruta_salida}")
        nx.write_graphml(G_autor_autor, ruta_salida)
    
    return G_autor_autor

def analizar_grafo_autor_autor(G_autor_autor):
    """
    Analiza las características básicas del grafo autor-autor.
    
    Args:
        G_autor_autor (networkx.Graph): Grafo autor-autor
    """
    print("\n=== ANÁLISIS DEL GRAFO AUTOR-AUTOR ===")
    print(f"Número de autores (nodos): {G_autor_autor.number_of_nodes()}")
    print(f"Número de colaboraciones (aristas): {G_autor_autor.number_of_edges()}")
    print(f"Densidad del grafo: {nx.density(G_autor_autor):.6f}")
    
    if G_autor_autor.number_of_edges() > 0:
        print(f"Grado promedio: {sum(dict(G_autor_autor.degree()).values()) / G_autor_autor.number_of_nodes():.2f}")
        
        # Encontrar autores con más colaboraciones
        grados = dict(G_autor_autor.degree())
        autor_max_colaboraciones = max(grados, key=grados.get)
        print(f"Autor con más colaboraciones: {G_autor_autor.nodes[autor_max_colaboraciones].get('display_name', autor_max_colaboraciones)} ({grados[autor_max_colaboraciones]} colaboraciones)")
        
        # Estadísticas de artículos compartidos
        articulos_compartidos = [data['num_articulos_compartidos'] 
                               for _, _, data in G_autor_autor.edges(data=True)]
        print(f"Promedio de artículos compartidos por colaboración: {sum(articulos_compartidos) / len(articulos_compartidos):.2f}")
        print(f"Máximo artículos compartidos entre dos autores: {max(articulos_compartidos)}")
        
        # Componentes conexas
        num_componentes = nx.number_connected_components(G_autor_autor)
        print(f"Número de componentes conexas: {num_componentes}")
        
        if num_componentes > 1:
            tamaños_componentes = [len(c) for c in nx.connected_components(G_autor_autor)]
            tamaños_componentes.sort(reverse=True)
            print(f"Tamaño de la componente más grande: {tamaños_componentes[0]}")
            print(f"Tamaños de las 5 componentes más grandes: {tamaños_componentes[:5]}")

if __name__ == "__main__":
    # Crear el grafo autor-autor
    ruta_entrada = "data/subgrafo_con_articulos.graphml"
    ruta_salida = "data/grafo_autor_autor.graphml"
    
    print("Iniciando creación del grafo autor-autor...")
    grafo_autor_autor = crear_grafo_autor_autor(ruta_entrada, ruta_salida)
    
    # Analizar el grafo creado
    analizar_grafo_autor_autor(grafo_autor_autor)
    
    print(f"\nGrafo autor-autor guardado en: {ruta_salida}")
