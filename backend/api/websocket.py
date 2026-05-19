"""
WebSocket Manager — Real-time event broadcasting to connected frontend clients.

Manages per-session WebSocket connections and provides a broadcast interface
used by the orchestrator to push events (agent messages, file changes,
state transitions, test results) to all connected clients for a session.
"""

from __future__ import annotations
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

from backend.models.state import WebSocketEvent

logger = logging.getLogger("flowstate.websocket")


class WebSocketManager:
    """
    Manages WebSocket connections grouped by session ID.

    Usage:
        ws_manager = WebSocketManager()
        await ws_manager.connect(session_id, websocket)
        await ws_manager.broadcast(session_id, event)
        ws_manager.disconnect(session_id, websocket)
    """

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection for a session."""
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = set()
        self._connections[session_id].add(websocket)
        logger.info(f"WebSocket connected: session={session_id}, total={len(self._connections[session_id])}")

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]
        logger.info(f"WebSocket disconnected: session={session_id}")

    async def broadcast(self, session_id: str, event: WebSocketEvent) -> None:
        """Send an event to all connected clients for a session."""
        connections = self._connections.get(session_id, set())
        if not connections:
            return

        message = json.dumps(event.to_dict())
        dead_connections = set()

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                dead_connections.add(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self._connections[session_id].discard(ws)

    def get_broadcast_fn(self, session_id: str):
        """Return a bound broadcast function for a specific session."""
        async def _broadcast(event: WebSocketEvent):
            await self.broadcast(session_id, event)
        return _broadcast
