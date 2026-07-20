"""REST API routes for building and querying the patient graph."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core import analytics
from app.core.graph_builder import PatientGraphBuilder
from app.core.similarity import PatientSimilarityEngine
from app.models.schemas import (
    BuildGraphResponse,
    CentralityResponse,
    CommunitiesResponse,
    GraphSummary,
    NeighborhoodResponse,
    PatientRecordBatch,
    PathResponse,
    SharedDiagnosesResponse,
    SimilarPatientsResponse,
)

router = APIRouter()

# Single in-memory graph instance for this base project. For multi-user /
# production use, this should be scoped per session or backed by a real
# graph database (see README "Extending this base project").
_builder = PatientGraphBuilder()


@router.post("/graph/build", response_model=BuildGraphResponse)
def build_graph(batch: PatientRecordBatch, compute_similarity: bool = True) -> BuildGraphResponse:
    if not batch.records:
        raise HTTPException(status_code=400, detail="No patient records provided")

    _builder.build(batch.records)

    if compute_similarity:
        engine = PatientSimilarityEngine(_builder.graph)
        engine.materialize_similarity_edges()

    return BuildGraphResponse(
        message=f"Graph built from {len(batch.records)} patient records",
        summary=GraphSummary(**_builder.summary()),
    )


@router.get("/graph/summary", response_model=GraphSummary)
def graph_summary() -> GraphSummary:
    return GraphSummary(**_builder.summary())


def _require_graph() -> None:
    if not _builder.is_built:
        raise HTTPException(
            status_code=409,
            detail="Graph has not been built yet. Call POST /graph/build first.",
        )


def _require_patient_node(patient_id: str) -> str:
    node = _builder.get_patient_node(patient_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
    return node


@router.get("/patients/{patient_id}/similar", response_model=SimilarPatientsResponse)
def similar_patients(patient_id: str, k: int = 5, min_score: float = 0.0) -> SimilarPatientsResponse:
    _require_graph()
    node = _require_patient_node(patient_id)

    engine = PatientSimilarityEngine(_builder.graph)
    results = engine.top_k_similar(node, k=k, min_score=min_score)

    return SimilarPatientsResponse(
        patient_id=patient_id,
        results=[
            {
                "patient_id": r.patient_id,
                "similarity_score": r.score,
                "shared_diagnoses": r.shared_diagnoses,
                "shared_medications": r.shared_medications,
            }
            for r in results
        ],
    )


@router.get("/patients/{patient_id}/neighborhood", response_model=NeighborhoodResponse)
def patient_neighborhood(patient_id: str) -> NeighborhoodResponse:
    _require_graph()
    node = _require_patient_node(patient_id)
    g = _builder.graph

    diagnoses, medications, providers = [], [], []
    for neighbor in g.neighbors(node):
        node_type = g.nodes[neighbor].get("node_type")
        if node_type == "diagnosis":
            diagnoses.append(g.nodes[neighbor].get("code", neighbor))
        elif node_type == "medication":
            medications.append(g.nodes[neighbor].get("code", neighbor))
        elif node_type == "provider":
            providers.append(g.nodes[neighbor].get("provider_id", neighbor))

    return NeighborhoodResponse(
        patient_id=patient_id,
        diagnoses=sorted(diagnoses),
        medications=sorted(medications),
        providers=sorted(providers),
    )


@router.get("/analytics/centrality", response_model=CentralityResponse)
def centrality(top_n: int = 10) -> CentralityResponse:
    _require_graph()
    results = analytics.compute_centrality(_builder.graph, top_n=top_n)
    return CentralityResponse(top_n=top_n, results=results)


@router.get("/analytics/communities", response_model=CommunitiesResponse)
def communities() -> CommunitiesResponse:
    _require_graph()
    results = analytics.detect_communities(_builder.graph)
    return CommunitiesResponse(total_communities=len(results), communities=results)


@router.get("/analytics/shared-diagnoses", response_model=SharedDiagnosesResponse)
def shared_diagnoses(min_patients: int = 2, top_n: int = 20) -> SharedDiagnosesResponse:
    _require_graph()
    pairs = analytics.shared_diagnosis_pairs(
        _builder.graph, min_patients=min_patients, top_n=top_n
    )
    return SharedDiagnosesResponse(pairs=pairs)


@router.get("/analytics/path/{source_id}/{target_id}", response_model=PathResponse)
def shortest_path(source_id: str, target_id: str) -> PathResponse:
    _require_graph()
    source_node = _require_patient_node(source_id)
    target_node = _require_patient_node(target_id)

    result = analytics.shortest_relational_path(_builder.graph, source_node, target_node)
    return PathResponse(
        source=source_id,
        target=target_id,
        found=result["found"],
        length=result["length"],
        path=result["path"],
    )
