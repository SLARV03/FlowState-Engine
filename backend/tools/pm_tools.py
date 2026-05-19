"""
Product Manager Tools — submit_spec.

The PM agent has exactly one tool: submit_spec, which writes the generated
technical specification into the global state and signals transition to SWE.
"""

from __future__ import annotations
from typing import List
from .registry import ToolDefinition


def _submit_spec(state: dict, markdown_string: str) -> str:
    """Write the technical specification to state and advance to SWE."""
    state["technical_spec"] = markdown_string
    return "Specification submitted successfully. Routing to Software Engineer."


def get_pm_tools() -> List[ToolDefinition]:
    """Return the list of tools available to the PM agent."""
    return [
        ToolDefinition(
            name="submit_spec",
            description=(
                "Submit the completed technical specification as a markdown string. "
                "This will store the spec in the global state and advance the pipeline "
                "to the Software Engineer agent."
            ),
            parameters={
                "markdown_string": {
                    "type": "string",
                    "description": "The full technical specification in markdown format.",
                },
            },
            required_params=["markdown_string"],
            handler=_submit_spec,
        ),
    ]
