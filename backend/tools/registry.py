"""
Tool Registry — Pluggable tool management for FlowState-Engine agents.

Each agent has a restricted set of tools. The registry validates tool calls
and ensures agents cannot invoke tools outside their permitted scope.
"""

from __future__ import annotations
from typing import Callable, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class ToolDefinition:
    """Defines a single tool available to an agent."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    required_params: List[str] = field(default_factory=list)

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required_params,
                },
            },
        }


class ToolRegistry:
    """
    Registry of tools grouped by agent role.

    Usage:
        registry = ToolRegistry()
        registry.register("swe", tool_def)
        tools = registry.get_tools("swe")
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, ToolDefinition]] = {}

    def register(self, agent_role: str, tool: ToolDefinition) -> None:
        """Register a tool for a specific agent role."""
        if agent_role not in self._tools:
            self._tools[agent_role] = {}
        self._tools[agent_role][tool.name] = tool

    def get_tools(self, agent_role: str) -> List[ToolDefinition]:
        """Get all tools for a given agent role."""
        return list(self._tools.get(agent_role, {}).values())

    def get_tool(self, agent_role: str, tool_name: str) -> ToolDefinition | None:
        """Get a specific tool by role and name."""
        return self._tools.get(agent_role, {}).get(tool_name)

    def get_openai_schemas(self, agent_role: str) -> List[dict]:
        """Get OpenAI-compatible tool schemas for an agent role."""
        return [t.to_openai_schema() for t in self.get_tools(agent_role)]

    def execute(self, agent_role: str, tool_name: str, state: dict, **kwargs) -> Any:
        """Execute a tool call with validation."""
        tool = self.get_tool(agent_role, tool_name)
        if tool is None:
            raise PermissionError(
                f"Agent '{agent_role}' does not have access to tool '{tool_name}'. "
                f"Available tools: {[t.name for t in self.get_tools(agent_role)]}"
            )
        return tool.handler(state=state, **kwargs)
