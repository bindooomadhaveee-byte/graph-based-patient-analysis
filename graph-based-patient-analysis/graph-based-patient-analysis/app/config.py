"""Application configuration, loaded from environment variables / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "graph-based-patient-analysis"
    log_level: str = "INFO"

    # Similarity weights - should sum to 1.0
    sim_weight_diagnosis: float = 0.5
    sim_weight_medication: float = 0.3
    sim_weight_demographic: float = 0.2

    default_data_path: str = "data/sample_patients.json"

    # Optional Neo4j backend (not wired up by default in this base project)
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "change_me"
    use_neo4j: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
