"""
FlowState-Engine — Main Application Entry Point.

Initializes the FastAPI server with REST routes, WebSocket endpoint,
CORS middleware, and session management. Run with:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.session.manager import SessionManager
from backend.api.websocket import WebSocketManager
from backend.api.routes import create_api_router

# ─── Logging Setup ──────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-28s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("flowstate.main")

# ─── Global Managers ────────────────────────────────────────

session_manager = SessionManager()
ws_manager = WebSocketManager()


# ─── App Lifespan ───────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("╔══════════════════════════════════════════════════╗")
    logger.info("║        FlowState-Engine v0.1.0 Starting         ║")
    logger.info("╠══════════════════════════════════════════════════╣")
    logger.info(f"║  LLM Provider : {settings.llm.provider:<33}║")
    logger.info(f"║  LLM Model    : {settings.llm.model:<33}║")
    logger.info(f"║  Max Iterations: {settings.server.max_iterations:<32}║")
    logger.info(f"║  Sandbox Timeout: {settings.sandbox.timeout_seconds}s{' ' * 28}║")
    logger.info("╚══════════════════════════════════════════════════╝")
    yield
    logger.info("FlowState-Engine shutting down.")


# ─── FastAPI App ────────────────────────────────────────────

app = FastAPI(
    title="FlowState-Engine",
    description="High-Performance Multi-Agent Orchestration Engine",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST routes
api_router = create_api_router(session_manager, ws_manager)
app.include_router(api_router)


# ─── WebSocket Endpoint ────────────────────────────────────

@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time session updates."""
    session = await session_manager.get_session(session_id)
    if session is None:
        await websocket.close(code=4004, reason="Session not found")
        return

    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            # Keep connection alive; listen for client messages (future: intervention)
            data = await websocket.receive_text()
            logger.debug(f"WS received from client: {data[:100]}")
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        ws_manager.disconnect(session_id, websocket)


# ─── Standalone Runner ──────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=True,
    )
