"""
Base Agent — Abstract foundation for all FlowState-Engine agents.

Provides LLM initialization, tool-calling loop, and state mutation interface.
Each concrete agent overrides `system_prompt`, `role`, and `get_tools()`.
"""

from __future__ import annotations
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from backend.config import get_settings
from backend.tools.registry import ToolDefinition
from backend.models.state import SquadState, ChatEntry, WebSocketEvent, EventType

logger = logging.getLogger("flowstate.agents")


class BaseAgent(ABC):
    """
    Abstract base class for all orchestration agents.

    Each agent wraps an independent LLM instantiation with a specific
    system prompt and restricted tool access. The `invoke` method runs
    the full tool-calling loop until the agent signals completion.
    """

    def __init__(self, broadcast_fn=None):
        """
        Args:
            broadcast_fn: Optional async callable to push WebSocket events.
        """
        self._settings = get_settings()
        self._llm = self._create_llm()
        self._broadcast = broadcast_fn

    @property
    @abstractmethod
    def role(self) -> str:
        """Agent role identifier (e.g., 'pm', 'swe', 'qa')."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The system prompt for this agent."""
        ...

    @abstractmethod
    def get_tools(self) -> List[ToolDefinition]:
        """Return the list of tools this agent is permitted to use."""
        ...

    @property
    def temperature(self) -> float:
        """Get the configured temperature for this agent role."""
        temps = {
            "pm": self._settings.llm.temperature_pm,
            "swe": self._settings.llm.temperature_swe,
            "qa": self._settings.llm.temperature_qa,
        }
        return temps.get(self.role, 0.3)

    def _create_llm(self):
        """Initialize the LLM client based on provider configuration."""
        settings = self._settings.llm
        if settings.provider == "anthropic":
            return ChatAnthropic(
                model=settings.model,
                api_key=settings.api_key,
                temperature=self.temperature,
                max_tokens=8192,
            )
        elif settings.provider == "google":
            return ChatGoogleGenerativeAI(
                model=settings.model,
                google_api_key=settings.api_key,
                temperature=self.temperature,
                max_output_tokens=8192,
            )
        else:
            return ChatOpenAI(
                model=settings.model,
                api_key=settings.api_key,
                temperature=self.temperature,
                max_tokens=8192,
            )

    def _build_messages(self, state: SquadState) -> List:
        """Construct the message list for the LLM call."""
        messages = [SystemMessage(content=self.system_prompt)]

        # Add relevant state context as a user message
        context = self._build_context(state)
        messages.append(HumanMessage(content=context))

        return messages

    @abstractmethod
    def _build_context(self, state: SquadState) -> str:
        """Build the user-facing context message from the current state."""
        ...

    async def _emit_event(self, event: WebSocketEvent) -> None:
        """Broadcast a WebSocket event if a broadcast function is available."""
        if self._broadcast:
            await self._broadcast(event)

    async def _log_chat(
        self,
        state: SquadState,
        sender: str,
        target: str,
        content: str,
        entry_type: str = "message",
    ) -> None:
        """Append a chat entry to state and emit it via WebSocket."""
        entry = ChatEntry(
            sender=sender,
            target=target,
            content=content,
            entry_type=entry_type,
        )
        state["chat_history"].append(entry.to_dict())

        await self._emit_event(WebSocketEvent(
            event_type=EventType.AGENT_MESSAGE,
            payload=entry.to_dict(),
        ))

    async def invoke(self, state: SquadState) -> SquadState:
        """
        Run the agent's full tool-calling loop.

        1. Build messages from state context
        2. Call LLM with bound tools
        3. Process tool calls, mutate state
        4. Repeat until no more tool calls
        5. Return mutated state
        """
        state["current_agent"] = self.role

        await self._emit_event(WebSocketEvent(
            event_type=EventType.STATE_TRANSITION,
            payload={
                "to_node": self.role,
                "agent_name": self.__class__.__name__,
            },
        ))

        tools = self.get_tools()
        tool_schemas = [t.to_openai_schema() for t in tools]
        tool_map = {t.name: t for t in tools}

        messages = self._build_messages(state)
        llm_with_tools = self._llm.bind_tools(tool_schemas) if tool_schemas else self._llm

        max_rounds = 10  # Safety: prevent infinite tool-call loops
        for round_num in range(max_rounds):
            logger.info(f"[{self.role.upper()}] LLM call round {round_num + 1}")

            try:
                response = await llm_with_tools.ainvoke(messages)
            except Exception as e:
                logger.error(f"[{self.role.upper()}] LLM call failed: {e}")
                await self._log_chat(
                    state, "system", self.role,
                    f"LLM call failed: {str(e)}", "error"
                )
                state["error"] = str(e)
                break

            messages.append(response)

            # If the LLM produced text content, log it
            if response.content and isinstance(response.content, str):
                await self._log_chat(
                    state, self.role, self._get_target(),
                    response.content[:500]  # Truncate for chat rail
                )

            # If no tool calls, the agent is done
            if not response.tool_calls:
                logger.info(f"[{self.role.upper()}] No more tool calls, agent complete.")
                break

            # Process each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                logger.info(f"[{self.role.upper()}] Tool call: {tool_name}({list(tool_args.keys())})")

                await self._log_chat(
                    state, self.role, "system",
                    f"Calling tool: {tool_name}", "tool_call"
                )

                tool_def = tool_map.get(tool_name)
                if tool_def is None:
                    result = f"Error: Tool '{tool_name}' is not available to agent '{self.role}'."
                else:
                    try:
                        result = tool_def.handler(state=state, **tool_args)
                    except Exception as e:
                        result = f"Tool execution error: {str(e)}"
                        logger.error(f"[{self.role.upper()}] Tool error: {e}")

                # Emit file events for write operations
                await self._emit_file_events(tool_name, tool_args, state)

                await self._log_chat(
                    state, "system", self.role,
                    result[:300], "tool_result"
                )

                messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tool_call["id"],
                ))

        return state

    async def _emit_file_events(self, tool_name: str, tool_args: dict, state: SquadState) -> None:
        """Emit WebSocket events for file creation/modification."""
        if tool_name in ("write_file", "write_test_file"):
            await self._emit_event(WebSocketEvent(
                event_type=EventType.FILE_CREATED,
                payload={
                    "path": tool_args.get("path", ""),
                    "agent": self.role,
                    "content": tool_args.get("content", "")[:200] + "...",
                },
            ))
        elif tool_name == "patch_file":
            await self._emit_event(WebSocketEvent(
                event_type=EventType.FILE_MODIFIED,
                payload={
                    "path": tool_args.get("path", ""),
                    "agent": self.role,
                },
            ))

    def _get_target(self) -> str:
        """Get the default message target for this agent."""
        targets = {"pm": "swe", "swe": "qa", "qa": "runtime"}
        return targets.get(self.role, "system")
