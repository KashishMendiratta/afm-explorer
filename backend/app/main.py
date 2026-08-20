import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_curves, routes_health, routes_labels, routes_scans, routes_train
from app.core.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="AFM Explorer API",
    description=(
        "Backend for the AFM Explorer project: parses AFM force-curve scans, "
        "estimates contact-point stiffness via a classical heuristic or a "
        "trained ML model, and manages the human-labeling + training loop."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router, prefix="/api")
app.include_router(routes_scans.router)
app.include_router(routes_curves.router)
app.include_router(routes_labels.router)
app.include_router(routes_train.router)
