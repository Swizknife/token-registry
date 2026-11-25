"""Client for the standalone prediction microservice.

Must never fail a kiosk registration: any error, timeout or malformed
response results in `None` and the caller proceeds without an estimate.
This is the seam Phase 4 (TimesFM) plugs into -- only this module and the
prediction-service's /predict body change; the request/response shape stays.
"""
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("prediction.client")


async def predict_wait_seconds(
    *,
    service_category: str,
    queue_depth: int,
    active_counters: int,
    recent_service_times: list[int],
) -> int | None:
    settings = get_settings()
    payload = {
        "service_category": service_category,
        "queue_depth": queue_depth,
        "active_counters": active_counters,
        "recent_service_times": recent_service_times,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.prediction_timeout_seconds) as client:
            resp = await client.post(f"{settings.prediction_service_url}/predict", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return int(data["predicted_wait_seconds"])
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        logger.warning("Prediction service unavailable or invalid response: %s", exc)
        return None
