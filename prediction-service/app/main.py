"""Standalone wait-time prediction microservice.

Phase 1-3: a transparent heuristic (queue depth / active counters * mean
service duration), tagged model_version="mock-heuristic-v1".

Phase 4: swap `predict()`'s body for a TimesFM inference call. The request
and response contract defined here is intentionally the only thing the core
backend depends on, so that swap never touches app/services/queue.py or
app/services/tokens.py in the main backend.

This service deliberately has no database of its own -- callers pass the
features it needs in the request body.
"""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Wait-Time Prediction Service")

MODEL_VERSION = "mock-heuristic-v1"
DEFAULT_SERVICE_SECONDS = 180  # used when there's no history yet


class PredictRequest(BaseModel):
    service_category: str
    queue_depth: int
    active_counters: int
    recent_service_times: list[int] = []


class PredictResponse(BaseModel):
    predicted_wait_seconds: int
    model_version: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest) -> PredictResponse:
    if payload.recent_service_times:
        mean_service_seconds = sum(payload.recent_service_times) / len(payload.recent_service_times)
    else:
        mean_service_seconds = DEFAULT_SERVICE_SECONDS

    active_counters = max(payload.active_counters, 1)
    predicted = int((payload.queue_depth / active_counters) * mean_service_seconds)

    return PredictResponse(predicted_wait_seconds=max(predicted, 0), model_version=MODEL_VERSION)
