import asyncio
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket


class WSManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        if self._loop is None:
            self._loop = asyncio.get_running_loop()

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        if not self._connections:
            return
        dead: Set[WebSocket] = set()
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws)

    def broadcast_threadsafe(self, payload: Dict[str, Any]) -> None:
        """可从非 async 线程调用的广播方法（例如 simulator 线程）。"""
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)


manager = WSManager()

