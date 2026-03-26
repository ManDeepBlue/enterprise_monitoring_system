
import asyncio
from typing import Dict, Set
from fastapi import WebSocket

class WSManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._sockets: Dict[str, Set[WebSocket]] = {}  # channel -> sockets

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._sockets.setdefault(channel, set()).add(ws)

    async def disconnect(self, channel: str, ws: WebSocket):
        async with self._lock:
            if channel in self._sockets and ws in self._sockets[channel]:
                self._sockets[channel].remove(ws)

    async def broadcast(self, channel: str, message: dict):
        async with self._lock:
            sockets = list(self._sockets.get(channel, set()))
        dead = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._sockets.get(channel, set()).discard(ws)

ws_manager = WSManager()
