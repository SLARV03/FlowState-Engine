"""
FlowState-Engine Global State Schema.

Defines the SquadState TypedDict that flows through every node in the
LangGraph state machine, plus WebSocket event models for real-time UI updates.
"""

from __future__ import annotations
from typing import TypedDict, List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Global State (LangGraph TypedDict) ─────────────────────

class SquadState(TypedDict):
    """Mutable state object passed by reference through the execution graph."""
    user_requirement: str
    technical_spec: str
    file_system: Dict[str, str]
    test_suite: Dict[str, str]
    latest_test_logs: str
    test_status: str              # "PENDING" | "PASSED" | "FAILED"
    iteration_count: int
    current_agent: str
    chat_history: List[Dict[str, str]]
    session_id: str
    detected_language: str        # "python" | "javascript" | "go"
    error: Optional[str]


def create_initial_state(session_id: str, user_requirement: str) -> SquadState:
    """Factory function to create a properly initialized SquadState."""
    return SquadState(
        user_requirement=user_requirement,
        technical_spec="",
        file_system={},
        test_suite={},
        latest_test_logs="",
        test_status="PENDING",
        iteration_count=0,
        current_agent="pm",
        chat_history=[],
        session_id=session_id,
        detected_language="python",
        error=None,
    )


# ─── WebSocket Event Models ─────────────────────────────────

class EventType(str, Enum):
    """WebSocket event type enumeration."""
    AGENT_MESSAGE = "agent_message"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    STATE_TRANSITION = "state_transition"
    TEST_RESULT = "test_result"
    ERROR = "error"
    SESSION_COMPLETE = "session_complete"
    ITERATION_UPDATE = "iteration_update"


class WebSocketEvent(BaseModel):
    """Schema for all WebSocket events sent to the frontend."""
    event_type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    payload: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


# ─── Agent Communication Log Entry ──────────────────────────

class ChatEntry(BaseModel):
    """Single entry in the inter-agent communication log."""
    sender: str       # "pm" | "swe" | "qa" | "runtime" | "system"
    target: str       # "swe" | "qa" | "runtime" | "user" | "system"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    entry_type: str = "message"  # "message" | "tool_call" | "tool_result"

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "target": self.target,
            "content": self.content,
            "timestamp": self.timestamp,
            "entry_type": self.entry_type,
        }
