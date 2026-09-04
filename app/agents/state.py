"""
LangGraph Agent State Definition.

Defines the shared state TypedDict that flows through every node
in the multi-agent graph. Every agent reads from and writes to this
single state object, enabling clean hand-offs between nodes.
"""

from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Shared state for the LangGraph multi-agent workflow.

    Fields:
        messages:       Conversation history (auto-appended via add_messages reducer).
        user_query:     The original, unmodified user question.
        intent:         Detected intent class (rag/data/file/code/vision/general).
        active_agent:   Name of the currently-executing agent.
        agent_steps:    Ordered list of execution steps for the frontend trace view.
        final_answer:   The compiled final response returned to the user.
        file_paths:     Paths of any files uploaded alongside the query.
        error:          Optional error message if something fails.
        metadata:       Arbitrary key/value bag for agent-specific context.
    """
    messages: Annotated[list, add_messages]
    user_query: str
    intent: str                    # rag | data | file | code | vision | general
    active_agent: str
    agent_steps: list[dict]        # [{agent, action, result, timestamp}]
    final_answer: str
    file_paths: list[str]          # uploaded file paths available to agents
    error: str | None
    metadata: dict[str, Any]
