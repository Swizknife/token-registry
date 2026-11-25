"""In-process WebSocket broadcaster.

Behind a Broadcaster protocol so a Redis pub/sub implementation can be
substituted later without touching callers -- the in-memory version only
works correctly with a single backend process/worker (see README).
"""
import asyncio
import json
import logging
from typing import Protocol

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class Broadcaster(Protocol):
    async def connect(self, ws: WebSocket) -> None: ...
    def disconnect(self, ws: WebSocket) -> None: ...
    async def broadcast(self, event_type: str, payload: dict) -> None: ...


class InMemoryBroadcaster:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)

    async def broadcast(self, event_type: str, payload: dict) -> None:
        message = json.dumps({"type": event_type, "payload": payload}, default=str)
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:  # noqa: BLE001 - connection may have dropped
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


broadcaster = InMemoryBroadcaster()
