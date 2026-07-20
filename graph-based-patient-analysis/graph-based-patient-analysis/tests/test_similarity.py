from app.core.graph_builder import PatientGraphBuilder
from app.core.similarity import PatientSimilarityEngine
from app.models.schemas import Diagnosis, Medication, PatientRecord, Sex


def _build_graph() -> PatientGraphBuilder:
    records = [
        PatientRecord(
            patient_id="P1",
            age=50,
            sex=Sex.male,
            diagnoses=[Diagnosis(code="E11.9"), Diagnosis(code="I10")],
            medications=[Medication(code="860975")],
        ),
        PatientRecord(
            patient_id="P2",
            age=52,
            sex=Sex.male,
            diagnoses=[Diagnosis(code="E11.9"), Diagnosis(code="I10")],
            medications=[Medication(code="860975")],
        ),
        PatientRecord(
            patient_id="P3",
            age=20,
            sex=Sex.female,
            diagnoses=[Diagnosis(code="F41.1")],
            medications=[],
        ),
    ]
    builder = PatientGraphBuilder()
    builder.build(records)
    return builder


def test_identical_patients_score_higher_than_unrelated():
    builder = _build_graph()
    engine = PatientSimilarityEngine(builder.graph)

    p1_p2 = engine.score_pair("patient:P1", "patient:P2")
    p1_p3 = engine.score_pair("patient:P1", "patient:P3")

    assert p1_p2.score > p1_p3.score
    assert "E11.9" in p1_p2.shared_diagnoses
    assert "I10" in p1_p2.shared_diagnoses


def test_top_k_similar_excludes_self_and_respects_k():
    builder = _build_graph()
    engine = PatientSimilarityEngine(builder.graph)

    results = engine.top_k_similar("patient:P1", k=1)

    assert len(results) == 1
    assert results[0].patient_id == "P2"


def test_materialize_similarity_edges_adds_edges():
    builder = _build_graph()
    engine = PatientSimilarityEngine(builder.graph)

    added = engine.materialize_similarity_edges(min_score=0.1, top_k_per_patient=2)

    assert added > 0
    assert builder.graph.has_edge("patient:P1", "patient:P2")
