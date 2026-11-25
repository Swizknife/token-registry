import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, auth, counters, kiosk, public, staff, ws
from app.config import get_settings
from app.services.sms.worker import start_worker, stop_worker

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_worker()
    yield
    stop_worker()


def create_app() -> FastAPI:
    app = FastAPI(title="Smart Token Queue & Booking System", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(kiosk.router)
    app.include_router(staff.router)
    app.include_router(counters.router)
    app.include_router(public.router)
    app.include_router(analytics.router)
    app.include_router(ws.router)

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
