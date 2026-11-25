from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.realtime import broadcaster

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/queue")
async def queue_socket(ws: WebSocket) -> None:
    await broadcaster.connect(ws)
    try:
        while True:
            # Clients don't need to send anything; just keep the connection open.
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.disconnect(ws)
