import sqlite3
import networkx as nx
from typing import Tuple
from networkx.classes.graph import Graph


def gen_nodes_and_edges() -> Tuple[list, list]:
    conn = sqlite3.connect('keywords.db')
    cursor = conn.cursor()
    nodes = cursor.execute('''select target, count(*) from keywords group by target''').fetchall()
    nodes = [(node[0], {'count': node[1]}) for node in nodes]

    suggestions = cursor.execute('SELECT * from keywords').fetchall()
    edges = []
    weights = {suggestion[:2]: suggestion[2] for suggestion in suggestions}
    for suggestion in suggestions:
        source, target, weight = suggestion
        total_weight = weight + weights.get((target, source), 0)
        distance = 11 - total_weight
        edge = (source, target, {'weight': total_weight, 'distance': distance})
        edges.append(edge)
    return nodes, edges


def gen_graph(keyword: str) -> Graph:
    nodes, edges = gen_nodes_and_edges()
    G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    # BUILD THE EGO GRAPH FOR TENSORFLOW
    EG = nx.ego_graph(G, keyword, distance='distance', radius=23)

    # FIND THE 2-CONNECTED SUBGRAPHS
    subgraphs = nx.algorithms.connectivity.edge_kcomponents.k_edge_subgraphs(EG, k=3)

    # GET THE SUBGRAPH THAT CONTAINS TENSORFLOW
    for s in subgraphs:
        if keyword in s:
            break
    pruned_EG = EG.subgraph(s)
    return pruned_EG


def write_to_csv() -> None:
    nodes, edges = gen_nodes_and_edges()
    with open('points.csv', 'w') as f:
        for node in nodes:
            f.write(f"{node[0]}, {node[1]['count']}\n")
    with open('links.csv', 'w') as f:
        for edge in edges:
            f.write(f"{edge[0]}, {edge[1]}, {edge[2]['weight']}\n")


if __name__ == '__main__':
    write_to_csv()
