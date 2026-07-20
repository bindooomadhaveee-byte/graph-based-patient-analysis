from app.core.graph_builder import PatientGraphBuilder
from app.models.schemas import Diagnosis, Encounter, Medication, PatientRecord, Sex


def _sample_records() -> list[PatientRecord]:
    return [
        PatientRecord(
            patient_id="P1",
            age=55,
            sex=Sex.male,
            diagnoses=[Diagnosis(code="E11.9", description="Type 2 diabetes")],
            medications=[Medication(code="860975", name="Metformin")],
            encounters=[Encounter(provider_id="PR-001")],
        ),
        PatientRecord(
            patient_id="P2",
            age=60,
            sex=Sex.female,
            diagnoses=[Diagnosis(code="E11.9", description="Type 2 diabetes")],
            medications=[],
            encounters=[Encounter(provider_id="PR-001")],
        ),
    ]


def test_build_creates_expected_nodes():
    builder = PatientGraphBuilder()
    graph = builder.build(_sample_records())

    assert graph.has_node("patient:P1")
    assert graph.has_node("patient:P2")
    assert graph.has_node("diagnosis:E11.9")
    assert graph.has_node("medication:860975")
    assert graph.has_node("provider:PR-001")


def test_build_creates_expected_edges():
    builder = PatientGraphBuilder()
    graph = builder.build(_sample_records())

    assert graph.has_edge("patient:P1", "diagnosis:E11.9")
    assert graph.has_edge("patient:P1", "medication:860975")
    assert graph.has_edge("patient:P1", "provider:PR-001")
    assert graph.has_edge("patient:P2", "diagnosis:E11.9")


def test_summary_counts():
    builder = PatientGraphBuilder()
    builder.build(_sample_records())
    summary = builder.summary()

    assert summary["node_type_counts"]["patient"] == 2
    assert summary["node_type_counts"]["diagnosis"] == 1
    assert summary["is_built"] is True


def test_patient_nodes_and_lookup():
    builder = PatientGraphBuilder()
    builder.build(_sample_records())

    assert set(builder.patient_nodes()) == {"patient:P1", "patient:P2"}
    assert builder.get_patient_node("P1") == "patient:P1"
    assert builder.get_patient_node("does-not-exist") is None


def test_reset_clears_graph():
    builder = PatientGraphBuilder()
    builder.build(_sample_records())
    builder.reset()

    assert builder.graph.number_of_nodes() == 0
    assert builder.is_built is False
