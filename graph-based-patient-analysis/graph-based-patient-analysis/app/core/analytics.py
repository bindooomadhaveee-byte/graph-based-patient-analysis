"""Graph analytics: centrality, community detection, comorbidity pairs,
and shortest-path queries over the patient graph.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations

import networkx as nx

try:
    import community as community_louvain  # python-louvain package
except ImportError:  # pragma: no cover
    community_louvain = None


def compute_centrality(graph: nx.Graph, top_n: int = 10) -> list[dict]:
    """Degree + betweenness centrality across all node types.

    Betweenness centrality on the full heterogeneous graph highlights nodes
    (patients, but also diagnoses/providers) that sit "between" many other
    nodes — a reasonable proxy for clinically important hubs (e.g. a
    diagnosis that bridges otherwise unrelated patient clusters).
    """
    if graph.number_of_nodes() == 0:
        return []

    degree_c = nx.degree_centrality(graph)
    # betweenness centrality is O(V*E); use approximate sampling on large graphs
    k = min(500, graph.number_of_nodes())
    betweenness_c = nx.betweenness_centrality(graph, k=k, seed=42)

    rows = []
    for node in graph.nodes():
        rows.append(
            {
                "node_id": node,
                "node_type": graph.nodes[node].get("node_type", "unknown"),
                "degree_centrality": round(degree_c.get(node, 0.0), 6),
                "betweenness_centrality": round(betweenness_c.get(node, 0.0), 6),
            }
        )

    rows.sort(key=lambda r: r["betweenness_centrality"], reverse=True)
    return rows[:top_n]


def detect_communities(graph: nx.Graph) -> list[dict]:
    """Community detection restricted to the patient-patient projection of
    the graph (via shared diagnoses), using the Louvain method.

    Falls back to connected-components if python-louvain isn't installed.
    """
    patient_nodes = [
        n for n, d in graph.nodes(data=True) if d.get("node_type") == "patient"
    ]

    # Build a patient-patient projection: edge if patients share >=1 diagnosis
    projection = nx.Graph()
    projection.add_nodes_from(patient_nodes)

    diagnosis_to_patients: dict[str, list[str]] = {}
    for node, data in graph.nodes(data=True):
        if data.get("node_type") == "diagnosis":
            neighbors = [
                nb
                for nb in graph.neighbors(node)
                if graph.nodes[nb].get("node_type") == "patient"
            ]
            diagnosis_to_patients[data.get("code", node)] = neighbors

    for code, patients in diagnosis_to_patients.items():
        for a, b in combinations(patients, 2):
            if projection.has_edge(a, b):
                projection[a][b]["weight"] += 1
            else:
                projection.add_edge(a, b, weight=1)

    if projection.number_of_edges() == 0:
        # No shared diagnoses at all -> each patient is its own community
        partition = {n: i for i, n in enumerate(patient_nodes)}
    elif community_louvain is not None:
        partition = community_louvain.best_partition(projection, random_state=42)
    else:  # pragma: no cover - fallback path
        partition = {}
        for i, component in enumerate(nx.connected_components(projection)):
            for node in component:
                partition[node] = i
        for n in patient_nodes:
            partition.setdefault(n, max(partition.values(), default=-1) + 1)

    communities: dict[int, list[str]] = {}
    for node, comm_id in partition.items():
        communities.setdefault(comm_id, []).append(node)

    results = []
    for comm_id, members in communities.items():
        dx_counter: Counter[str] = Counter()
        for m in members:
            dx_counter.update(graph.nodes[m].get("diagnosis_codes", []))
        common_dx = [code for code, _ in dx_counter.most_common(5)]

        results.append(
            {
                "community_id": comm_id,
                "patient_ids": sorted(
                    graph.nodes[m].get("patient_id", m) for m in members
                ),
                "size": len(members),
                "common_diagnoses": common_dx,
            }
        )

    results.sort(key=lambda r: r["size"], reverse=True)
    return results


def shared_diagnosis_pairs(graph: nx.Graph, min_patients: int = 2, top_n: int = 20) -> list[dict]:
    """Finds the most common co-occurring diagnosis pairs across patients —
    a simple comorbidity signal.
    """
    patient_nodes = [
        n for n, d in graph.nodes(data=True) if d.get("node_type") == "patient"
    ]

    pair_counter: Counter[tuple[str, str]] = Counter()
    for node in patient_nodes:
        dx_codes = sorted(graph.nodes[node].get("diagnosis_codes", []))
        for a, b in combinations(dx_codes, 2):
            pair_counter[(a, b)] += 1

    results = [
        {"diagnosis_a": a, "diagnosis_b": b, "patient_count": count}
        for (a, b), count in pair_counter.items()
        if count >= min_patients
    ]
    results.sort(key=lambda r: r["patient_count"], reverse=True)
    return results[:top_n]


def shortest_relational_path(graph: nx.Graph, source_node: str, target_node: str) -> dict:
    """Shortest path between two patient nodes through the heterogeneous
    graph (i.e. via shared diagnoses/medications/providers/similarity
    edges) — useful for explaining *why* two patients are connected.
    """
    if not graph.has_node(source_node) or not graph.has_node(target_node):
        return {"found": False, "length": None, "path": []}

    try:
        path = nx.shortest_path(graph, source_node, target_node)
        return {"found": True, "length": len(path) - 1, "path": path}
    except nx.NetworkXNoPath:
        return {"found": False, "length": None, "path": []}
