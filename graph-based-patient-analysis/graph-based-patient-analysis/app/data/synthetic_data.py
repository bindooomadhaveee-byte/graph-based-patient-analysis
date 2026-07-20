"""Generates a synthetic patient dataset (JSON, matching PatientRecord
schema) for local development and testing.

Usage:
    python -m app.data.synthetic_data --n-patients 200 --out data/sample_patients.json
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from faker import Faker

fake = Faker()

# A small illustrative pool of ICD-10-like diagnosis codes, clustered into
# rough "disease families" so the synthetic graph has realistic comorbidity
# structure (patients with diabetes are more likely to also have
# hypertension, etc.) rather than pure noise.
DIAGNOSIS_CLUSTERS: dict[str, list[tuple[str, str]]] = {
    "cardiometabolic": [
        ("E11.9", "Type 2 diabetes mellitus without complications"),
        ("I10", "Essential (primary) hypertension"),
        ("E78.5", "Hyperlipidemia, unspecified"),
        ("I25.10", "Atherosclerotic heart disease"),
        ("E66.9", "Obesity, unspecified"),
    ],
    "respiratory": [
        ("J45.909", "Unspecified asthma, uncomplicated"),
        ("J44.9", "Chronic obstructive pulmonary disease, unspecified"),
        ("J06.9", "Acute upper respiratory infection, unspecified"),
    ],
    "mental_health": [
        ("F32.9", "Major depressive disorder, single episode, unspecified"),
        ("F41.1", "Generalized anxiety disorder"),
        ("F41.9", "Anxiety disorder, unspecified"),
    ],
    "musculoskeletal": [
        ("M54.5", "Low back pain"),
        ("M17.9", "Osteoarthritis of knee, unspecified"),
        ("M25.50", "Pain in unspecified joint"),
    ],
    "renal": [
        ("N18.3", "Chronic kidney disease, stage 3"),
        ("N39.0", "Urinary tract infection, site not specified"),
    ],
}

MEDICATIONS_BY_CLUSTER: dict[str, list[tuple[str, str]]] = {
    "cardiometabolic": [
        ("860975", "Metformin 500mg"),
        ("197361", "Lisinopril 10mg"),
        ("617314", "Atorvastatin 20mg"),
    ],
    "respiratory": [
        ("745679", "Albuterol HFA inhaler"),
        ("896188", "Fluticasone/salmeterol"),
    ],
    "mental_health": [
        ("312938", "Sertraline 50mg"),
        ("197380", "Escitalopram 10mg"),
    ],
    "musculoskeletal": [
        ("197806", "Ibuprofen 600mg"),
        ("866924", "Acetaminophen 500mg"),
    ],
    "renal": [
        ("866414", "Furosemide 20mg"),
    ],
}

PROVIDER_POOL = [f"PR-{i:03d}" for i in range(1, 26)]


def _pick_cluster() -> str:
    return random.choice(list(DIAGNOSIS_CLUSTERS.keys()))


def _generate_patient(index: int) -> dict:
    patient_id = f"P-{index:05d}"
    age = random.randint(1, 95)
    sex = random.choice(["M", "F"])

    n_clusters = random.choices([1, 2, 3], weights=[0.55, 0.35, 0.10])[0]
    clusters = random.sample(list(DIAGNOSIS_CLUSTERS.keys()), k=n_clusters)

    diagnoses = []
    medications = []
    for cluster in clusters:
        dx_pool = DIAGNOSIS_CLUSTERS[cluster]
        n_dx = random.randint(1, min(2, len(dx_pool)))
        for code, desc in random.sample(dx_pool, k=n_dx):
            diagnoses.append({"code": code, "description": desc})

        med_pool = MEDICATIONS_BY_CLUSTER.get(cluster, [])
        if med_pool and random.random() < 0.8:
            code, name = random.choice(med_pool)
            medications.append({"code": code, "name": name})

    n_encounters = random.randint(1, 4)
    encounters = [
        {
            "provider_id": random.choice(PROVIDER_POOL),
            "encounter_type": random.choice(["outpatient", "inpatient", "telehealth"]),
        }
        for _ in range(n_encounters)
    ]

    return {
        "patient_id": patient_id,
        "age": age,
        "sex": sex,
        "diagnoses": diagnoses,
        "medications": medications,
        "encounters": encounters,
    }


def generate_dataset(n_patients: int, seed: int | None = None) -> list[dict]:
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)
    return [_generate_patient(i) for i in range(1, n_patients + 1)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic patient data")
    parser.add_argument("--n-patients", type=int, default=200)
    parser.add_argument("--out", type=str, default="data/sample_patients.json")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    records = generate_dataset(args.n_patients, seed=args.seed)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"records": records}, indent=2))

    print(f"Wrote {len(records)} synthetic patient records to {out_path}")


if __name__ == "__main__":
    main()
