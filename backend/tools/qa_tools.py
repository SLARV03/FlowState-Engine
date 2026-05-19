"""
QA Engineer Tools — write_test_file, run_test_sandbox.

The QA agent writes test files and triggers isolated Docker sandbox execution.
The run_test_sandbox tool is a placeholder that signals the sandbox runner
to execute — the actual Docker logic lives in sandbox/runner.py.
"""

from __future__ import annotations
from typing import List
from .registry import ToolDefinition


def _write_test_file(state: dict, path: str, content: str) -> str:
    """Write a test script into the test suite."""
    state["test_suite"][path] = content
    return f"Test file '{path}' written successfully ({len(content)} chars)."


def _run_test_sandbox(state: dict) -> str:
    """
    Signal that tests should be executed in the Docker sandbox.

    This tool sets a flag that the orchestrator picks up to invoke
    the actual sandbox runner. The result (logs, status) will be
    injected into state by the sandbox runner, not by this tool.
    """
    test_count = len(state["test_suite"])
    if test_count == 0:
        return "Error: No test files have been written. Write at least one test file first."
    return f"SANDBOX_EXECUTE_SIGNAL: {test_count} test files queued for sandbox execution."


def get_qa_tools() -> List[ToolDefinition]:
    """Return the list of tools available to the QA agent."""
    return [
        ToolDefinition(
            name="write_test_file",
            description=(
                "Write a test script into the test suite. "
                "The path should follow convention (e.g., 'tests/test_main.py'). "
                "Use pytest for Python, Jest/Vitest for JavaScript."
            ),
            parameters={
                "path": {
                    "type": "string",
                    "description": "Relative path for the test file (e.g., 'tests/test_cache.py').",
                },
                "content": {
                    "type": "string",
                    "description": "The complete test code content.",
                },
            },
            required_params=["path", "content"],
            handler=_write_test_file,
        ),
        ToolDefinition(
            name="run_test_sandbox",
            description=(
                "Execute all test files inside an isolated Docker sandbox container. "
                "This will spin up an ephemeral container, run the tests, and capture "
                "stdout/stderr. Call this after all test files are written."
            ),
            parameters={},
            required_params=[],
            handler=_run_test_sandbox,
        ),
    ]
