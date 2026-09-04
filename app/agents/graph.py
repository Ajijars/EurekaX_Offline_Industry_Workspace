"""
LangGraph Agent Workflow Graph – Step 3 Assembly.

Assembles all agent nodes and edges into a compiled LangGraph StateGraph.
The graph follows this flow:

    START
      │
      ▼
  [supervisor]  ← classifies intent
      │
      ▼ (conditional routing on state["intent"])
  ┌───┴──────────────────────────────────────────┐
  │  rag_agent │ data_agent │ file_agent │        │
  │  code_agent │ vision_agent │ general_agent │  │
  └──────────────────┬───────────────────────────┘
                     │
                     ▼
               [final_response]  ← packages the final AgentState
                     │
                     ▼
                    END

Public API:
    agent_graph          – compiled LangGraph object
    run_agent_workflow   – async convenience wrapper
"""

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from app.agents.state import AgentState
from app.agents.supervisor import supervisor_node, route_to_agent
from app.agents.rag_agent import rag_agent_node
from app.agents.data_agent import data_agent_node
from app.agents.file_agent import file_agent_node
from app.agents.code_agent import code_agent_node
from app.agents.vision_agent import vision_agent_node
from app.agents.general_agent import general_agent_node

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Final Response Node
# ──────────────────────────────────────────────

async def final_response_node(state: AgentState) -> AgentState:
    """
    Terminal node: logs completion and passes state through unchanged.

    The final_answer in state is what the API layer returns to the user.
    """
    logger.info(
        f"[Graph] Workflow complete | Agent: {state.get('active_agent')} | "
        f"Steps: {len(state.get('agent_steps', []))}"
    )
    return state


# ──────────────────────────────────────────────
# Build & Compile Graph
# ──────────────────────────────────────────────

def _build_graph() -> Any:
    """Construct and compile the LangGraph StateGraph."""
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("data_agent", data_agent_node)
    graph.add_node("file_agent", file_agent_node)
    graph.add_node("code_agent", code_agent_node)
    graph.add_node("vision_agent", vision_agent_node)
    graph.add_node("general_agent", general_agent_node)
    graph.add_node("final_response", final_response_node)

    # Entry point
    graph.add_edge(START, "supervisor")

    # Conditional routing from supervisor → specialized agent
    graph.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "rag_agent":    "rag_agent",
            "data_agent":   "data_agent",
            "file_agent":   "file_agent",
            "code_agent":   "code_agent",
            "vision_agent": "vision_agent",
            "general_agent": "general_agent",
        },
    )

    # All agents → final_response → END
    for agent in [
        "rag_agent",
        "data_agent",
        "file_agent",
        "code_agent",
        "vision_agent",
        "general_agent",
    ]:
        graph.add_edge(agent, "final_response")

    graph.add_edge("final_response", END)

    return graph.compile()


# Singleton compiled graph (loaded once at import time)
try:
    agent_graph = _build_graph()
    logger.info("[Graph] LangGraph agent workflow compiled successfully")
except Exception as _e:
    logger.error(f"[Graph] Failed to compile agent graph: {_e}")
    agent_graph = None


# ──────────────────────────────────────────────
# Public Workflow Runner
# ──────────────────────────────────────────────

def _initial_state(query: str, file_paths: list[str] | None) -> AgentState:
    return {
        "messages": [],
        "user_query": query,
        "intent": "",
        "active_agent": "",
        "agent_steps": [],
        "final_answer": "",
        "file_paths": file_paths or [],
        "error": None,
        "metadata": {},
    }


def _result_from_state(final_state: dict) -> dict:
    return {
        "answer": final_state.get("final_answer", "No answer generated."),
        "intent": final_state.get("intent", "unknown"),
        "active_agent": final_state.get("active_agent", "unknown"),
        "agent_steps": final_state.get("agent_steps", []),
        "error": final_state.get("error"),
        "metadata": final_state.get("metadata", {}),
    }


async def run_agent_workflow(
    query: str,
    file_paths: list[str] | None = None,
) -> dict:
    """
    Run the full multi-agent workflow for a user query.

    Args:
        query:      The user's natural language question.
        file_paths: Optional list of uploaded file paths agents can access.

    Returns:
        Dict with:
            answer       – Final natural language answer
            intent       – Detected intent class
            active_agent – Name of the agent that generated the answer
            agent_steps  – Ordered list of execution steps (for UI trace)
            error        – Error message if workflow failed
    """
    if agent_graph is None:
        return {
            "answer": "Agent workflow is unavailable (graph compilation failed).",
            "intent": "error",
            "active_agent": "none",
            "agent_steps": [],
            "error": "Graph not compiled",
        }

    initial_state = _initial_state(query, file_paths)

    try:
        logger.info(f"[Workflow] Starting for query: {query[:80]!r}")
        final_state = await agent_graph.ainvoke(initial_state)
        return _result_from_state(final_state)
    except Exception as e:
        logger.error(f"[Workflow] Execution failed: {e}", exc_info=True)
        return {
            "answer": f"Agent workflow encountered an error: {e}",
            "intent": "error",
            "active_agent": "none",
            "agent_steps": [],
            "error": str(e),
        }


async def stream_agent_workflow(
    query: str,
    file_paths: list[str] | None = None,
):
    """
    Stream graph node updates as they complete.

    Yields dicts:
        {"type": "step", "step": {...}}
        {"type": "answer", ...}  (final)
        {"type": "error", ...}
    """
    if agent_graph is None:
        yield {
            "type": "error",
            "error": "Graph not compiled",
            "done": True,
        }
        return

    seen_steps = 0
    last_state: dict = {}

    try:
        async for update in agent_graph.astream(_initial_state(query, file_paths)):
            for _node, node_state in update.items():
                if not isinstance(node_state, dict):
                    continue
                last_state = {**last_state, **node_state}
                steps = node_state.get("agent_steps") or last_state.get("agent_steps") or []
                while seen_steps < len(steps):
                    yield {"type": "step", "step": steps[seen_steps]}
                    seen_steps += 1

        result = _result_from_state(last_state)
        yield {
            "type": "answer",
            "answer": result["answer"],
            "intent": result["intent"],
            "active_agent": result["active_agent"],
            "done": True,
            "error": result.get("error"),
        }
    except Exception as e:
        logger.error("[Workflow] Stream failed: %s", e, exc_info=True)
        yield {"type": "error", "error": str(e), "done": True}
