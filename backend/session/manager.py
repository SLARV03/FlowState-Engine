"""
Session Manager — Manages orchestration sessions and their lifecycle.

Each session represents one user prompt flowing through the agent pipeline.
Sessions are stored in-memory with thread-safe access.
"""

from __future__ import annotations
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

from backend.models.state import SquadState, create_initial_state

logger = logging.getLogger("flowstate.session")


@dataclass
class Session:
    """Represents a single orchestration session."""
    id: str
    created_at: str
    status: str = "created"   # "created" | "running" | "completed" | "failed" | "cancelled"
    state: Optional[SquadState] = None
    task: Optional[asyncio.Task] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize session metadata (excludes full state for listing)."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "status": self.status,
            "error": self.error,
            "iteration_count": self.state["iteration_count"] if self.state else 0,
            "test_status": self.state["test_status"] if self.state else "PENDING",
            "current_agent": self.state["current_agent"] if self.state else None,
            "file_count": len(self.state["file_system"]) if self.state else 0,
            "test_count": len(self.state["test_suite"]) if self.state else 0,
        }


class SessionManager:
    """
    In-memory session store with lifecycle management.

    Supports creation, retrieval, termination, and cleanup of sessions.
    Thread-safe via asyncio Lock.
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create_session(self) -> Session:
        """Create a new session with a unique UUID."""
        session_id = uuid.uuid4().hex[:12]
        session = Session(
            id=session_id,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        async with self._lock:
            self._sessions[session_id] = session
        logger.info(f"Session created: {session_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)

    async def update_session(
        self,
        session_id: str,
        status: Optional[str] = None,
        state: Optional[SquadState] = None,
        error: Optional[str] = None,
        task: Optional[asyncio.Task] = None,
    ) -> None:
        """Update session fields."""
        session = self._sessions.get(session_id)
        if session is None:
            return
        async with self._lock:
            if status is not None:
                session.status = status
            if state is not None:
                session.state = state
            if error is not None:
                session.error = error
            if task is not None:
                session.task = task

    async def terminate_session(self, session_id: str) -> bool:
        """Cancel a running session and clean up resources."""
        session = self._sessions.get(session_id)
        if session is None:
            return False

        if session.task and not session.task.done():
            session.task.cancel()
            try:
                await session.task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            session.status = "cancelled"

        logger.info(f"Session terminated: {session_id}")
        return True

    async def delete_session(self, session_id: str) -> bool:
        """Remove a session from the store entirely."""
        await self.terminate_session(session_id)
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Session deleted: {session_id}")
                return True
        return False

    async def list_sessions(self) -> list:
        """Return metadata for all sessions."""
        return [s.to_dict() for s in self._sessions.values()]
