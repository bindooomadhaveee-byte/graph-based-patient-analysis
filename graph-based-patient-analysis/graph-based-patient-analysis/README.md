# Graph-Based Patient Analysis

A base framework for modeling patients and their clinical relationships as a
graph, and running network analytics on top of it — similarity search,
comorbidity clustering, centrality-based risk signals, and community
detection over a patient population.

This is a **starter / base project**: it gives you a working end-to-end
pipeline (synthetic data → graph → analytics → API) that you can extend with
a real EHR data source, a persistent graph database, and production auth.

---

## Why a graph?

Traditional tabular patient analysis treats each patient as an independent
row. A lot of clinically useful structure lives in the *relationships*
between patients and clinical entities:

- Patients who **share diagnoses** cluster into comorbidity groups
- Patients **referred** to/from the same providers form care pathways
- Patients with overlapping **medications** reveal polypharmacy risk
- **Central** patients/entities in the graph often correspond to complex or
  high-risk cases

Modeling this explicitly as a graph makes those relationships queryable and
analyzable with standard graph algorithms (centrality, shortest path,
community detection) instead of ad-hoc joins.

## Graph model

The graph is heterogeneous (multiple node types), built with NetworkX:

| Node type    | Represents                          |
|--------------|--------------------------------------|
| `patient`    | A (de-identified) patient             |
| `diagnosis`  | An ICD-10 diagnosis code              |
| `medication` | A medication (RxNorm-style code)      |
| `provider`   | A treating provider                   |

| Edge type         | Between                  | Meaning                              |
|--------------------|---------------------------|----------------------------------------|
| `HAS_DIAGNOSIS`     | patient → diagnosis       | patient was diagnosed with condition  |
| `PRESCRIBED`        | patient → medication      | patient was prescribed medication     |
| `TREATED_BY`         | patient → provider        | patient had an encounter with provider|
| `SIMILAR_TO`         | patient → patient         | computed similarity edge (weighted)   |

`SIMILAR_TO` edges are derived, not loaded — see `app/core/similarity.py`.

## Project structure

```
graph-based-patient-analysis/
├── app/
│   ├── main.py                 # FastAPI application entrypoint
│   ├── config.py                # Settings (env-driven)
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response models
│   ├── core/
│   │   ├── graph_builder.py     # Builds the NetworkX graph from records
│   │   ├── similarity.py        # Patient-patient similarity computation
│   │   ├── analytics.py         # Centrality, communities, paths, risk
│   │   └── deidentify.py        # Basic de-identification utilities
│   ├── api/
│   │   └── routes.py            # REST endpoints
│   └── data/
│       └── synthetic_data.py    # Synthetic patient dataset generator
├── data/
│   └── sample_patients.json     # Generated sample dataset (gitignored input)
├── tests/
│   ├── test_graph_builder.py
│   ├── test_similarity.py
│   └── test_analytics.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quickstart

### Local (no Docker)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# generate a synthetic dataset to play with
python -m app.data.synthetic_data --n-patients 200 --out data/sample_patients.json

# run the API
uvicorn app.main:app --reload
```

Then open http://localhost:8000/docs for interactive API docs.

### Docker

```bash
docker compose up --build
```

This starts the API on `:8000`. A `neo4j` service is included (commented in
`docker-compose.yml`) for when you outgrow the in-memory NetworkX graph and
want a persistent graph database backend.

## API overview

| Method | Path                                | Description                                   |
|--------|--------------------------------------|------------------------------------------------|
| POST   | `/graph/build`                       | Build the graph from uploaded patient records |
| GET    | `/graph/summary`                     | Node/edge counts, density, component count    |
| GET    | `/patients/{patient_id}/similar`     | Top-K most similar patients                   |
| GET    | `/patients/{patient_id}/neighborhood`| Diagnoses/meds/providers connected to patient |
| GET    | `/analytics/centrality`              | Degree/betweenness centrality (risk proxy)    |
| GET    | `/analytics/communities`             | Louvain-style community detection             |
| GET    | `/analytics/shared-diagnoses`        | Most common comorbidity pairs                 |
| GET    | `/analytics/path/{a}/{b}`            | Shortest relational path between two patients |

Full request/response schemas are in `app/models/schemas.py` and are
browsable live at `/docs` (Swagger) or `/redoc`.

## Similarity method

Patient similarity is computed as a weighted combination of:

- **Jaccard similarity** of diagnosis code sets
- **Jaccard similarity** of medication code sets
- **Demographic proximity** (age bucket, sex match)

Weights are configurable in `app/config.py`. This is intentionally simple —
swap in embeddings (e.g. patient2vec, node2vec over the graph) for a more
sophisticated similarity backend without changing the API surface.

## De-identification

`app/core/deidentify.py` provides a minimal Safe Harbor-style transform
(name/MRN hashing, date shifting, age capping at 90) applied to synthetic
data before it enters the graph. **This is a starting point, not a
compliance guarantee** — a real deployment handling PHI needs a formal HIPAA
risk assessment, access controls, and audit logging beyond what's in this
base project.

## Extending this base project

- Swap `NetworkX` for `Neo4j` (via the `neo4j` Python driver) for
  persistence and Cypher queries at scale — the `docker-compose.yml`
  already has a Neo4j service stubbed in.
- Replace `synthetic_data.py` with a real FHIR/HL7 ingestion pipeline.
- Add authentication (JWT) to the API layer.
- Replace Jaccard similarity with learned graph embeddings (node2vec,
  GraphSAGE) for the `SIMILAR_TO` edges.
- Add a `risk_propagation.py` module that diffuses a risk score across
  the graph (e.g. personalized PageRank from known high-risk patients).

## Testing

```bash
pytest -v
```

## Disclaimer

This project is a technical base for graph analytics research and
prototyping. It is not a validated clinical decision support tool and
should not be used to make patient care decisions without appropriate
clinical and regulatory review.
