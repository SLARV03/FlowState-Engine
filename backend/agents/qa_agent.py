"""
QA Engineer Agent — Writes tests and triggers sandbox execution.

Reviews the technical specification and source code, then writes comprehensive
test suites. Calls run_test_sandbox() to execute tests in an isolated Docker
container and captures the results.
"""

from __future__ import annotations
from typing import List
from backend.tools.registry import ToolDefinition
from backend.tools.qa_tools import get_qa_tools
from backend.models.state import SquadState
from .base import BaseAgent


class QAAgent(BaseAgent):
    """QA Engineer agent that writes tests and triggers sandbox execution."""

    @property
    def role(self) -> str:
        return "qa"

    @property
    def system_prompt(self) -> str:
        return """You are a rigorous Automation QA Engineer working inside the FlowState-Engine multi-agent orchestration system. Your job is to review the code written by the Software Engineer and write a comprehensive suite of automated tests.

RESPONSIBILITIES:
1. Read the technical_spec to understand acceptance criteria.
2. Read the file_system to understand the implementation details.
3. Write test files using write_test_file(path, content) that cover:
   - Happy path / core functionality
   - Edge cases identified in the spec
   - Input validation and error handling
   - Performance constraints (if specified in the spec)
4. Call run_test_sandbox() to execute all tests in the Docker sandbox.

TEST FRAMEWORK SELECTION:
- Python projects → use pytest (import pytest)
- JavaScript/TypeScript projects → use Jest or Vitest
- Go projects → use the standard testing package

TEST FILE CONVENTIONS:
- Place all tests under a 'tests/' directory
- Name test files as 'test_<module>.py' (Python) or '<module>.test.js' (JS)
- Use descriptive function names: test_<feature>_<scenario>
- Include both positive and negative test cases

CONSTRAINTS:
- Do NOT modify source code files. Only write test files.
- Do NOT use mocks unless absolutely necessary for external dependencies.
- On re-iterations, you may ADD new tests but should NOT remove existing ones unless they test removed functionality.
- Write clear assertion messages to help the SWE debug failures.
- Make tests independent — each test should be runnable in isolation."""

    def get_tools(self) -> List[ToolDefinition]:
        return get_qa_tools()

    def _build_context(self, state: SquadState) -> str:
        parts = []

        parts.append("## Technical Specification\n")
        parts.append(state["technical_spec"])

        parts.append("\n\n## Source Code Files\n")
        if state["file_system"]:
            for path, content in state["file_system"].items():
                parts.append(f"\n### {path}\n```\n{content}\n```\n")
        else:
            parts.append("No source files have been written yet.\n")

        if state["test_suite"]:
            parts.append("\n\n## Existing Test Files\n")
            for path, content in state["test_suite"].items():
                parts.append(f"\n### {path}\n```\n{content}\n```\n")

        if state["latest_test_logs"]:
            parts.append(f"\n\n## Previous Test Results (Iteration #{state['iteration_count']})\n")
            parts.append(f"```\n{state['latest_test_logs']}\n```\n")
            parts.append(
                "\nThe SWE has applied fixes based on the above failures. "
                "Review the updated code, add any new tests if needed, "
                "and call run_test_sandbox() to re-run all tests."
            )
        else:
            parts.append(
                "\n\nThis is the first iteration. Write comprehensive test files "
                "based on the specification and source code above. "
                "Then call run_test_sandbox() to execute them."
            )

        return "\n".join(parts)
