"""
Software Engineer Tools — write_file, patch_file, submit_to_qa.

The SWE agent can create/overwrite files, patch existing code, and signal
readiness for QA review.
"""

from __future__ import annotations
from typing import List
from .registry import ToolDefinition


def _write_file(state: dict, path: str, content: str) -> str:
    """Create or overwrite a file in the virtual file system."""
    state["file_system"][path] = content
    return f"File '{path}' written successfully ({len(content)} chars)."


def _patch_file(state: dict, path: str, search_string: str, replace_string: str) -> str:
    """Apply a targeted string replacement within an existing file."""
    if path not in state["file_system"]:
        return f"Error: File '{path}' does not exist in the workspace."

    current_content = state["file_system"][path]
    if search_string not in current_content:
        return (
            f"Error: Search string not found in '{path}'. "
            f"Please verify the exact content you're trying to replace."
        )

    updated = current_content.replace(search_string, replace_string, 1)
    state["file_system"][path] = updated
    return f"File '{path}' patched successfully."


def _submit_to_qa(state: dict) -> str:
    """Signal that coding is complete and advance to QA."""
    file_count = len(state["file_system"])
    return f"Code submitted for QA review ({file_count} files). Routing to QA Engineer."


def get_swe_tools() -> List[ToolDefinition]:
    """Return the list of tools available to the SWE agent."""
    return [
        ToolDefinition(
            name="write_file",
            description=(
                "Create or overwrite a source file in the virtual workspace. "
                "Use this for writing new files or full rewrites. "
                "The path should be relative (e.g., 'src/main.py')."
            ),
            parameters={
                "path": {
                    "type": "string",
                    "description": "Relative file path (e.g., 'src/main.py').",
                },
                "content": {
                    "type": "string",
                    "description": "The complete source code content of the file.",
                },
            },
            required_params=["path", "content"],
            handler=_write_file,
        ),
        ToolDefinition(
            name="patch_file",
            description=(
                "Apply a targeted string replacement within an existing file. "
                "Use this for bug fixes to minimize regression risk. "
                "Only the first occurrence of search_string will be replaced."
            ),
            parameters={
                "path": {
                    "type": "string",
                    "description": "Path to the existing file to patch.",
                },
                "search_string": {
                    "type": "string",
                    "description": "The exact string to find in the file.",
                },
                "replace_string": {
                    "type": "string",
                    "description": "The replacement string.",
                },
            },
            required_params=["path", "search_string", "replace_string"],
            handler=_patch_file,
        ),
        ToolDefinition(
            name="submit_to_qa",
            description=(
                "Signal that all coding work is complete and ready for QA review. "
                "Call this after writing or patching all necessary files."
            ),
            parameters={},
            required_params=[],
            handler=_submit_to_qa,
        ),
    ]
