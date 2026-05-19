"""
Software Engineer Agent — Writes and patches source code based on specifications.

On first iteration, reads the technical spec and writes all source files.
On subsequent iterations (bug-fix loops), analyzes test failure logs and
applies targeted patches to fix identified issues.
"""

from __future__ import annotations
from typing import List
from backend.tools.registry import ToolDefinition
from backend.tools.swe_tools import get_swe_tools
from backend.models.state import SquadState
from .base import BaseAgent


class SWEAgent(BaseAgent):
    """Software Engineer agent that writes and patches source code."""

    @property
    def role(self) -> str:
        return "swe"

    @property
    def system_prompt(self) -> str:
        return """You are a Senior Full-Stack Software Engineer working inside the FlowState-Engine multi-agent orchestration system. Your job is to read the technical specification and write clean, modular, documented code into the virtual file system.

FIRST ITERATION BEHAVIOR:
- Read the technical_spec field carefully.
- Design a clean file/module structure following the spec's File Structure section.
- Write ALL source files using write_file(path, content).
- Ensure all public functions have docstrings and type hints.
- Write production-quality code. No placeholder TODO stubs.
- Call submit_to_qa() when all files are written.

BUG-FIX ITERATION BEHAVIOR (when test failure logs are provided):
- Treat test failures as HIGH-PRIORITY bugs.
- Analyze the FULL stack trace in the test logs.
- Identify root cause(s) in your source files.
- Use patch_file(path, search_string, replace_string) for targeted fixes.
- Use write_file(path, content) only if a complete rewrite is necessary.
- Do NOT mock functionality unless the spec explicitly allows it.
- Call submit_to_qa() when fixes are applied.

CONSTRAINTS:
- Do NOT write test files. That is the QA Engineer's responsibility.
- Do NOT modify test files under any circumstances.
- Write production-quality code. No placeholder TODO stubs.
- Prefer patch_file() over write_file() for bug fixes to minimize regression risk.
- Include proper error handling and input validation in all code."""

    def get_tools(self) -> List[ToolDefinition]:
        return get_swe_tools()

    def _build_context(self, state: SquadState) -> str:
        parts = []

        parts.append("## Technical Specification\n")
        parts.append(state["technical_spec"])

        if state["file_system"]:
            parts.append("\n\n## Current File System\n")
            for path, content in state["file_system"].items():
                parts.append(f"\n### {path}\n```\n{content}\n```\n")

        if state["latest_test_logs"]:
            parts.append(f"\n\n## ⚠️ Test Failure Logs (Iteration #{state['iteration_count']})\n")
            parts.append(f"```\n{state['latest_test_logs']}\n```\n")
            parts.append(
                "\nAnalyze the above test failures carefully. Identify the root cause "
                "in your source files and apply targeted fixes using patch_file() or "
                "write_file(). Then call submit_to_qa()."
            )
        else:
            parts.append(
                "\n\nThis is the first iteration. Write all source files from scratch "
                "based on the specification above. Call submit_to_qa() when done."
            )

        return "\n".join(parts)
