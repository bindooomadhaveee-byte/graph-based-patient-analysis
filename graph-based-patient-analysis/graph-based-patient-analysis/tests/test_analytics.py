from app.core import analytics
from app.core.graph_builder import PatientGraphBuilder
from app.models.schemas import Diagnosis, PatientRecord, Sex


def _build_graph() -> PatientGraphBuilder:
    records = [
        PatientRecord(
            patient_id="P1",
            age=50,
            sex=Sex.male,
            diagnoses=[Diagnosis(code="E11.9"), Diagnosis(code="I10")],
        ),
        PatientRecord(
            patient_id="P2",
            age=52,
            sex=Sex.male,
            diagnoses=[Diagnosis(code="E11.9"), Diagnosis(code="I10")],
        ),
        PatientRecord(
            patient_id="P3",
            age=20,
            sex=Sex.female,
            diagnoses=[Diagnosis(code="F41.1")],
        ),
    ]
    builder = PatientGraphBuilder()
    builder.build(records)
    return builder


def test_compute_centrality_returns_rows():
    builder = _build_graph()
    results = analytics.compute_centrality(builder.graph, top_n=5)

    assert len(results) > 0
    assert all("degree_centrality" in r for r in results)


def test_detect_communities_groups_shared_diagnosis_patients():
    builder = _build_graph()
    communities = analytics.detect_communities(builder.graph)

    # P1 and P2 share both diagnoses and should end up in the same community
    p1_community = next(c for c in communities if "P1" in c["patient_ids"])
    assert "P2" in p1_community["patient_ids"]


def test_shared_diagnosis_pairs():
    builder = _build_graph()
    pairs = analytics.shared_diagnosis_pairs(builder.graph, min_patients=1)

    assert any(
        {p["diagnosis_a"], p["diagnosis_b"]} == {"E11.9", "I10"} for p in pairs
    )


def test_shortest_relational_path_found():
    builder = _build_graph()
    result = analytics.shortest_relational_path(
        builder.graph, "patient:P1", "patient:P2"
    )

    assert result["found"] is True
    assert result["length"] == 2  # P1 -> diagnosis -> P2


def test_shortest_relational_path_missing_node():
    builder = _build_graph()
    result = analytics.shortest_relational_path(
        builder.graph, "patient:P1", "patient:does-not-exist"
    )

    assert result["found"] is False
    assert result["path"] == []
