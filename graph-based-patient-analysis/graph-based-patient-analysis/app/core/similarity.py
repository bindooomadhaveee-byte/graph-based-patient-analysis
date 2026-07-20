"""Computes pairwise patient similarity and (optionally) materializes
SIMILAR_TO edges on the graph.

Similarity = weighted sum of:
  - Jaccard(diagnosis codes)
  - Jaccard(medication codes)
  - demographic proximity (age closeness + sex match)
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from app.config import Settings, get_settings


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _demographic_proximity(age_a: int, age_b: int, sex_a: str, sex_b: str) -> float:
    age_diff = abs(age_a - age_b)
    # Full score at 0 years apart, decaying to 0 by 40+ years apart.
    age_score = max(0.0, 1 - age_diff / 40)
    sex_score = 1.0 if sex_a == sex_b else 0.0
    return 0.7 * age_score + 0.3 * sex_score


@dataclass
class SimilarityResult:
    patient_id: str
    score: float
    shared_diagnoses: list[str]
    shared_medications: list[str]


class PatientSimilarityEngine:
    def __init__(self, graph: nx.Graph, settings: Settings | None = None) -> None:
        self.graph = graph
        self.settings = settings or get_settings()

    def _patient_attrs(self, node: str) -> dict:
        return self.graph.nodes[node]

    def score_pair(self, node_a: str, node_b: str) -> SimilarityResult:
        attrs_a = self._patient_attrs(node_a)
        attrs_b = self._patient_attrs(node_b)

        dx_a = set(attrs_a.get("diagnosis_codes", []))
        dx_b = set(attrs_b.get("diagnosis_codes", []))
        med_a = set(attrs_a.get("medication_codes", []))
        med_b = set(attrs_b.get("medication_codes", []))

        dx_sim = _jaccard(dx_a, dx_b)
        med_sim = _jaccard(med_a, med_b)
        demo_sim = _demographic_proximity(
            attrs_a.get("age", 0),
            attrs_b.get("age", 0),
            attrs_a.get("sex", "U"),
            attrs_b.get("sex", "U"),
        )

        w = self.settings
        score = (
            w.sim_weight_diagnosis * dx_sim
            + w.sim_weight_medication * med_sim
            + w.sim_weight_demographic * demo_sim
        )

        return SimilarityResult(
            patient_id=attrs_b.get("patient_id", node_b),
            score=round(score, 6),
            shared_diagnoses=sorted(dx_a & dx_b),
            shared_medications=sorted(med_a & med_b),
        )

    def top_k_similar(
        self, patient_node: str, k: int = 5, min_score: float = 0.0
    ) -> list[SimilarityResult]:
        """Return the top-k most similar patients to the given patient node."""
        candidates = [
            n
            for n, d in self.graph.nodes(data=True)
            if d.get("node_type") == "patient" and n != patient_node
        ]

        results = [self.score_pair(patient_node, c) for c in candidates]
        results = [r for r in results if r.score >= min_score]
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]

    def materialize_similarity_edges(
        self, min_score: float = 0.3, top_k_per_patient: int = 5
    ) -> int:
        """Adds SIMILAR_TO edges to the graph for patient pairs above a
        threshold. Returns the number of edges added. This can be
        expensive on large graphs (O(n^2)) — fine for a base project /
        moderate patient counts, swap for approximate nearest-neighbor
        search or graph embeddings at scale.
        """
        patient_nodes = [
            n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "patient"
        ]

        added = 0
        for node in patient_nodes:
            similar = self.top_k_similar(node, k=top_k_per_patient, min_score=min_score)
            for result in similar:
                other_node = f"patient:{result.patient_id}"
                if not self.graph.has_edge(node, other_node):
                    self.graph.add_edge(
                        node,
                        other_node,
                        edge_type="SIMILAR_TO",
                        weight=result.score,
                    )
                    added += 1
        return added
