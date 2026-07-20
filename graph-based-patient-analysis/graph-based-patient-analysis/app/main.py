"""FastAPI application entrypoint for graph-based-patient-analysis."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings

settings = get_settings()

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(settings.app_name)

app = FastAPI(
    title="Graph-Based Patient Analysis",
    description=(
        "Base project for modeling patients and clinical relationships as a "
        "graph, with similarity search, comorbidity clustering, and "
        "centrality-based analytics."
    ),
    version="0.1.0",
)

app.include_router(router)


@app.get("/", tags=["health"])
def root() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "healthy"}
