"""Builds a heterogeneous patient graph from a list of PatientRecord objects.

Node types: patient, diagnosis, medication, provider
Edge types: HAS_DIAGNOSIS, PRESCRIBED, TREATED_BY, SIMILAR_TO (added later
by app.core.similarity)
"""

from __future__ import annotations

import networkx as nx

from app.models.schemas import PatientRecord

PATIENT = "patient"
DIAGNOSIS = "diagnosis"
MEDICATION = "medication"
PROVIDER = "provider"


def _patient_node_id(patient_id: str) -> str:
    return f"patient:{patient_id}"


def _diagnosis_node_id(code: str) -> str:
    return f"diagnosis:{code}"


def _medication_node_id(code: str) -> str:
    return f"medication:{code}"


def _provider_node_id(provider_id: str) -> str:
    return f"provider:{provider_id}"


class PatientGraphBuilder:
    """Builds and holds the in-memory patient graph.

    A thin wrapper around networkx.Graph so the rest of the app can stay
    agnostic to the underlying graph library (and be swapped for a Neo4j
    session later without touching callers).
    """

    def __init__(self) -> None:
        self.graph: nx.Graph = nx.Graph()
        self._built = False

    @property
    def is_built(self) -> bool:
        return self._built

    def reset(self) -> None:
        self.graph = nx.Graph()
        self._built = False

    def build(self, records: list[PatientRecord]) -> nx.Graph:
        """Build the graph from scratch given a batch of patient records."""
        self.reset()

        for record in records:
            self._add_patient(record)

        self._built = True
        return self.graph

    def add_records(self, records: list[PatientRecord]) -> nx.Graph:
        """Incrementally add records to an existing graph (or start one)."""
        for record in records:
            self._add_patient(record)
        self._built = True
        return self.graph

    def _add_patient(self, record: PatientRecord) -> None:
        g = self.graph
        p_node = _patient_node_id(record.patient_id)

        g.add_node(
            p_node,
            node_type=PATIENT,
            patient_id=record.patient_id,
            age=record.age,
            sex=record.sex.value if hasattr(record.sex, "value") else record.sex,
            diagnosis_codes=sorted({d.code for d in record.diagnoses}),
            medication_codes=sorted({m.code for m in record.medications}),
        )

        for dx in record.diagnoses:
            d_node = _diagnosis_node_id(dx.code)
            g.add_node(
                d_node,
                node_type=DIAGNOSIS,
                code=dx.code,
                description=dx.description,
            )
            g.add_edge(p_node, d_node, edge_type="HAS_DIAGNOSIS")

        for med in record.medications:
            m_node = _medication_node_id(med.code)
            g.add_node(
                m_node,
                node_type=MEDICATION,
                code=med.code,
                name=med.name,
            )
            g.add_edge(p_node, m_node, edge_type="PRESCRIBED")

        for enc in record.encounters:
            pr_node = _provider_node_id(enc.provider_id)
            g.add_node(
                pr_node,
                node_type=PROVIDER,
                provider_id=enc.provider_id,
            )
            g.add_edge(p_node, pr_node, edge_type="TREATED_BY")

    # -- convenience accessors -------------------------------------------------

    def patient_nodes(self) -> list[str]:
        return [
            n for n, d in self.graph.nodes(data=True) if d.get("node_type") == PATIENT
        ]

    def get_patient_node(self, patient_id: str) -> str | None:
        node = _patient_node_id(patient_id)
        return node if self.graph.has_node(node) else None

    def summary(self) -> dict:
        node_type_counts: dict[str, int] = {}
        for _, data in self.graph.nodes(data=True):
            t = data.get("node_type", "unknown")
            node_type_counts[t] = node_type_counts.get(t, 0) + 1

        edge_type_counts: dict[str, int] = {}
        for _, _, data in self.graph.edges(data=True):
            t = data.get("edge_type", "unknown")
            edge_type_counts[t] = edge_type_counts.get(t, 0) + 1

        n = self.graph.number_of_nodes()
        e = self.graph.number_of_edges()
        density = nx.density(self.graph) if n > 1 else 0.0
        components = (
            nx.number_connected_components(self.graph) if n > 0 else 0
        )

        return {
            "node_count": n,
            "edge_count": e,
            "node_type_counts": node_type_counts,
            "edge_type_counts": edge_type_counts,
            "density": round(density, 6),
            "connected_components": components,
            "is_built": self._built,
        }
