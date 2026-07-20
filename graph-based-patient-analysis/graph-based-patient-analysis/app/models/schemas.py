"""Pydantic models for patient records and API request/response bodies."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Sex(str, Enum):
    male = "M"
    female = "F"
    other = "O"
    unknown = "U"


class Diagnosis(BaseModel):
    code: str = Field(..., description="ICD-10 diagnosis code, e.g. 'E11.9'")
    description: Optional[str] = None


class Medication(BaseModel):
    code: str = Field(..., description="Medication code (RxNorm-style)")
    name: Optional[str] = None


class Encounter(BaseModel):
    provider_id: str
    encounter_type: Optional[str] = "outpatient"


class PatientRecord(BaseModel):
    """A single (de-identified) patient record used to build the graph."""

    patient_id: str
    age: int = Field(..., ge=0, le=120)
    sex: Sex = Sex.unknown
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    encounters: list[Encounter] = Field(default_factory=list)


class PatientRecordBatch(BaseModel):
    records: list[PatientRecord]


class GraphSummary(BaseModel):
    node_count: int
    edge_count: int
    node_type_counts: dict[str, int]
    edge_type_counts: dict[str, int]
    density: float
    connected_components: int
    is_built: bool


class SimilarPatient(BaseModel):
    patient_id: str
    similarity_score: float
    shared_diagnoses: list[str]
    shared_medications: list[str]


class SimilarPatientsResponse(BaseModel):
    patient_id: str
    results: list[SimilarPatient]


class NeighborhoodResponse(BaseModel):
    patient_id: str
    diagnoses: list[str]
    medications: list[str]
    providers: list[str]


class CentralityEntry(BaseModel):
    node_id: str
    node_type: str
    degree_centrality: float
    betweenness_centrality: float


class CentralityResponse(BaseModel):
    top_n: int
    results: list[CentralityEntry]


class CommunityEntry(BaseModel):
    community_id: int
    patient_ids: list[str]
    size: int
    common_diagnoses: list[str]


class CommunitiesResponse(BaseModel):
    total_communities: int
    communities: list[CommunityEntry]


class SharedDiagnosisPair(BaseModel):
    diagnosis_a: str
    diagnosis_b: str
    patient_count: int


class SharedDiagnosesResponse(BaseModel):
    pairs: list[SharedDiagnosisPair]


class PathResponse(BaseModel):
    source: str
    target: str
    found: bool
    length: Optional[int] = None
    path: list[str] = Field(default_factory=list)


class BuildGraphResponse(BaseModel):
    message: str
    summary: GraphSummary
