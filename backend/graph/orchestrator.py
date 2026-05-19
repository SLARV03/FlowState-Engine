"""
FlowState Orchestrator — LangGraph-based state machine.

Defines the directed graph that routes execution between agents:
  START → PM → SWE → QA → [Conditional Branch]
                ↑                    │
                └── FAILED (retry) ──┤
                                     ├── PASSED → DEPLOY → END
                                     └── MAX_ITER → HUMAN → END
"""

from __future__ import annotations
import logging
from typing import Callable, Awaitable, Optional

from langgraph.graph import StateGraph, END

from backend.config import get_settings
from backend.models.state import SquadState, WebSocketEvent, EventType, create_initial_state
from backend.agents.pm_agent import PMAgent
from backend.agents.swe_agent import SWEAgent
from backend.agents.qa_agent import QAAgent
from backend.sandbox.runner import SandboxRunner

logger = logging.getLogger("flowstate.orchestrator")


class FlowStateOrchestrator:
    """
    Compiles and executes the LangGraph state machine for a session.

    The orchestrator wires up all agent nodes, the sandbox runner,
    conditional routing, and safety breakers into a single executable graph.
    """

    def __init__(self, broadcast_fn: Optional[Callable] = None):
        """
        Args:
            broadcast_fn: Async callable to push WebSocket events to the frontend.
        """
        self._settings = get_settings()
        self._broadcast = broadcast_fn
        self._sandbox = SandboxRunner()

        # Initialize agents with WebSocket broadcast capability
        self._pm = PMAgent(broadcast_fn=broadcast_fn)
        self._swe = SWEAgent(broadcast_fn=broadcast_fn)
        self._qa = QAAgent(broadcast_fn=broadcast_fn)

        # Compile the graph
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Construct the LangGraph state machine."""
        graph = StateGraph(SquadState)

        # ── Add nodes ────────────────────────────────────────
        graph.add_node("pm_agent", self._pm_node)
        graph.add_node("swe_agent", self._swe_node)
        graph.add_node("qa_agent", self._qa_node)
        graph.add_node("sandbox_runner", self._sandbox_node)
        graph.add_node("deployment_node", self._deployment_node)
        graph.add_node("human_intervention_node", self._human_intervention_node)

        # ── Define edges ─────────────────────────────────────
        graph.set_entry_point("pm_agent")
        graph.add_edge("pm_agent", "swe_agent")
        graph.add_edge("swe_agent", "qa_agent")
        graph.add_edge("qa_agent", "sandbox_runner")

        # Conditional routing after sandbox execution
        graph.add_conditional_edges(
            "sandbox_runner",
            self._route_after_sandbox,
            {
                "deployment_node": "deployment_node",
                "swe_agent": "swe_agent",
                "human_intervention_node": "human_intervention_node",
            },
        )

        graph.add_edge("deployment_node", END)
        graph.add_edge("human_intervention_node", END)

        return graph.compile()

    # ── Node Functions ───────────────────────────────────────

    async def _pm_node(self, state: SquadState) -> SquadState:
        """Product Manager node — generates technical specification."""
        logger.info("═══ PM Agent: Generating specification ═══")
        await self._emit(EventType.STATE_TRANSITION, {"to_node": "pm", "label": "Product Manager"})
        return await self._pm.invoke(state)

    async def _swe_node(self, state: SquadState) -> SquadState:
        """Software Engineer node — writes/patches source code."""
        iteration = state["iteration_count"]
        mode = "Bug Fix" if state["latest_test_logs"] else "Initial Build"
        logger.info(f"═══ SWE Agent: {mode} (iteration {iteration}) ═══")
        await self._emit(EventType.STATE_TRANSITION, {
            "to_node": "swe",
            "label": "Software Engineer",
            "iteration": iteration,
            "mode": mode,
        })
        return await self._swe.invoke(state)

    async def _qa_node(self, state: SquadState) -> SquadState:
        """QA Engineer node — writes tests and prepares for sandbox execution."""
        logger.info("═══ QA Agent: Writing tests ═══")
        await self._emit(EventType.STATE_TRANSITION, {"to_node": "qa", "label": "QA Engineer"})
        return await self._qa.invoke(state)

    async def _sandbox_node(self, state: SquadState) -> SquadState:
        """Sandbox node — executes tests in an isolated Docker container."""
        logger.info("═══ Sandbox Runner: Executing tests ═══")
        await self._emit(EventType.STATE_TRANSITION, {"to_node": "sandbox", "label": "Sandbox Execution"})

        result = await self._sandbox.execute(state)

        # Update state with sandbox results
        state["latest_test_logs"] = result.combined_output
        state["test_status"] = "PASSED" if result.passed else "FAILED"
        state["iteration_count"] += 1

        logger.info(
            f"Sandbox result: status={state['test_status']}, "
            f"iteration={state['iteration_count']}, "
            f"exit_code={result.exit_code}"
        )

        # Emit test result event
        await self._emit(EventType.TEST_RESULT, {
            "status": state["test_status"],
            "iteration": state["iteration_count"],
            "logs": state["latest_test_logs"][:2000],  # Truncate for WebSocket
            "timed_out": result.timed_out,
        })

        # Emit iteration update
        await self._emit(EventType.ITERATION_UPDATE, {
            "iteration_count": state["iteration_count"],
            "test_status": state["test_status"],
            "max_iterations": self._settings.server.max_iterations,
        })

        return state

    async def _deployment_node(self, state: SquadState) -> SquadState:
        """Deployment node — all tests passed, prepare final output."""
        logger.info("═══ DEPLOYMENT: All tests passed! ═══")
        await self._emit(EventType.SESSION_COMPLETE, {
            "status": "success",
            "iterations": state["iteration_count"],
            "file_count": len(state["file_system"]),
            "test_count": len(state["test_suite"]),
        })
        return state

    async def _human_intervention_node(self, state: SquadState) -> SquadState:
        """Human intervention node — max iterations reached, request human input."""
        logger.warning(
            f"═══ HUMAN INTERVENTION: Max iterations ({state['iteration_count']}) reached ═══"
        )
        await self._emit(EventType.ERROR, {
            "error_type": "max_iterations_reached",
            "message": (
                f"The system has exhausted {state['iteration_count']} iterations without "
                f"achieving passing tests. Human intervention is required."
            ),
            "latest_logs": state["latest_test_logs"][:2000],
            "iteration_count": state["iteration_count"],
        })
        return state

    # ── Conditional Routing ──────────────────────────────────

    def _route_after_sandbox(self, state: SquadState) -> str:
        """Determine the next node based on test results and iteration count."""
        max_iter = self._settings.server.max_iterations

        if state["test_status"] == "PASSED":
            logger.info("Routing → Deployment (tests passed)")
            return "deployment_node"
        elif state["test_status"] == "FAILED" and state["iteration_count"] < max_iter:
            logger.info(
                f"Routing → SWE (tests failed, iteration {state['iteration_count']}/{max_iter})"
            )
            return "swe_agent"
        else:
            logger.info("Routing → Human Intervention (max iterations reached)")
            return "human_intervention_node"

    # ── Execution ────────────────────────────────────────────

    async def run(self, session_id: str, user_requirement: str) -> SquadState:
        """
        Execute the full orchestration pipeline for a user prompt.

        Args:
            session_id: Unique session identifier.
            user_requirement: The user's natural language prompt.

        Returns:
            The final SquadState after execution completes.
        """
        initial_state = create_initial_state(session_id, user_requirement)

        logger.info(f"Starting orchestration for session {session_id}")
        logger.info(f"User requirement: {user_requirement[:100]}...")

        try:
            final_state = await self._graph.ainvoke(initial_state)
            logger.info(f"Orchestration complete for session {session_id}")
            return final_state
        except Exception as e:
            logger.error(f"Orchestration failed for session {session_id}: {e}")
            initial_state["error"] = str(e)
            await self._emit(EventType.ERROR, {
                "error_type": "orchestration_failure",
                "message": str(e),
            })
            return initial_state

    # ── Helpers ──────────────────────────────────────────────

    async def _emit(self, event_type: EventType, payload: dict) -> None:
        """Emit a WebSocket event if broadcast function is available."""
        if self._broadcast:
            event = WebSocketEvent(event_type=event_type, payload=payload)
            await self._broadcast(event)
