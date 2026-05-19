"""
REST API Routes — Session management and state inspection endpoints.

Provides the HTTP interface for creating sessions, starting orchestration,
querying state, downloading files, and human intervention.
"""

from __future__ import annotations
import io
import zipfile
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.session.manager import SessionManager
from backend.api.websocket import WebSocketManager
from backend.graph.orchestrator import FlowStateOrchestrator

logger = logging.getLogger("flowstate.api")


# ─── Request/Response Models ────────────────────────────────

class StartRequest(BaseModel):
    """Request body for starting a session."""
    user_requirement: str = Field(..., min_length=10, description="The user's natural language prompt.")


class InterventionRequest(BaseModel):
    """Request body for human intervention."""
    action: str = Field(..., description="Action: 'modify_prompt' | 'edit_files' | 'abort'")
    updated_prompt: Optional[str] = Field(None, description="Updated prompt if action is modify_prompt")
    file_edits: Optional[dict] = Field(None, description="Dict of path->content if action is edit_files")


class SessionResponse(BaseModel):
    """Standard session response."""
    id: str
    status: str
    message: str = ""


# ─── Router Factory ─────────────────────────────────────────

def create_api_router(
    session_manager: SessionManager,
    ws_manager: WebSocketManager,
) -> APIRouter:
    """Create and return the API router with all endpoints."""

    router = APIRouter(prefix="/api", tags=["FlowState API"])

    # ── Health Check ─────────────────────────────────────
    @router.get("/health")
    async def health_check():
        return {"status": "healthy", "engine": "FlowState-Engine", "version": "0.1.0"}

    # ── Session CRUD ─────────────────────────────────────
    @router.post("/session/create", response_model=SessionResponse)
    async def create_session():
        session = await session_manager.create_session()
        return SessionResponse(id=session.id, status=session.status, message="Session created.")

    @router.get("/sessions")
    async def list_sessions():
        sessions = await session_manager.list_sessions()
        return {"sessions": sessions}

    @router.post("/session/{session_id}/start", response_model=SessionResponse)
    async def start_session(session_id: str, body: StartRequest):
        session = await session_manager.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        if session.status == "running":
            raise HTTPException(status_code=409, detail="Session is already running.")

        # Create orchestrator with WebSocket broadcast for this session
        broadcast_fn = ws_manager.get_broadcast_fn(session_id)
        orchestrator = FlowStateOrchestrator(broadcast_fn=broadcast_fn)

        # Run orchestration in background
        import asyncio

        async def _run():
            try:
                await session_manager.update_session(session_id, status="running")
                final_state = await orchestrator.run(session_id, body.user_requirement)
                status = "completed" if final_state.get("test_status") == "PASSED" else "failed"
                await session_manager.update_session(
                    session_id, status=status, state=final_state
                )
            except asyncio.CancelledError:
                await session_manager.update_session(session_id, status="cancelled")
            except Exception as e:
                logger.error(f"Session {session_id} failed: {e}")
                await session_manager.update_session(
                    session_id, status="failed", error=str(e)
                )

        task = asyncio.create_task(_run())
        await session_manager.update_session(session_id, task=task)

        return SessionResponse(
            id=session_id, status="running",
            message="Orchestration started. Connect via WebSocket for real-time updates."
        )

    # ── State Inspection ─────────────────────────────────
    @router.get("/session/{session_id}/state")
    async def get_session_state(session_id: str):
        session = await session_manager.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        return {
            "session": session.to_dict(),
            "state": dict(session.state) if session.state else None,
        }

    @router.get("/session/{session_id}/files")
    async def list_files(session_id: str):
        session = await session_manager.get_session(session_id)
        if session is None or session.state is None:
            raise HTTPException(status_code=404, detail="Session not found or not started.")
        files = {
            "source_files": list(session.state["file_system"].keys()),
            "test_files": list(session.state["test_suite"].keys()),
        }
        return files

    @router.get("/session/{session_id}/files/{file_path:path}")
    async def get_file_content(session_id: str, file_path: str):
        session = await session_manager.get_session(session_id)
        if session is None or session.state is None:
            raise HTTPException(status_code=404, detail="Session not found or not started.")

        all_files = {**session.state["file_system"], **session.state["test_suite"]}
        if file_path not in all_files:
            raise HTTPException(status_code=404, detail=f"File '{file_path}' not found.")
        return {"path": file_path, "content": all_files[file_path]}

    # ── Download ─────────────────────────────────────────
    @router.get("/session/{session_id}/download")
    async def download_files(session_id: str):
        session = await session_manager.get_session(session_id)
        if session is None or session.state is None:
            raise HTTPException(status_code=404, detail="Session not found or not started.")

        # Create in-memory ZIP
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, content in session.state["file_system"].items():
                zf.writestr(path, content)
            for path, content in session.state["test_suite"].items():
                zf.writestr(path, content)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=flowstate_{session_id}.zip"},
        )

    # ── Human Intervention ───────────────────────────────
    @router.post("/session/{session_id}/intervene")
    async def intervene(session_id: str, body: InterventionRequest):
        session = await session_manager.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")

        if body.action == "abort":
            await session_manager.terminate_session(session_id)
            return {"message": "Session aborted.", "status": "cancelled"}

        elif body.action == "modify_prompt" and body.updated_prompt:
            if session.state:
                session.state["user_requirement"] = body.updated_prompt
                session.state["iteration_count"] = 0
                session.state["test_status"] = "PENDING"
            return {"message": "Prompt updated. Restart the session to continue.", "status": "modified"}

        elif body.action == "edit_files" and body.file_edits:
            if session.state:
                for path, content in body.file_edits.items():
                    session.state["file_system"][path] = content
            return {"message": "Files updated. Restart the session to continue.", "status": "modified"}

        raise HTTPException(status_code=400, detail="Invalid intervention action.")

    # ── Session Cleanup ──────────────────────────────────
    @router.delete("/session/{session_id}")
    async def delete_session(session_id: str):
        deleted = await session_manager.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found.")
        return {"message": "Session deleted.", "status": "deleted"}

    return router
