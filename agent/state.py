"""Shared state schema for the Extremo Ambiente AI assistant."""

from __future__ import annotations

from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(dict):
    """Minimal chat state — just messages."""

    messages: Annotated[list[AnyMessage], add_messages]
