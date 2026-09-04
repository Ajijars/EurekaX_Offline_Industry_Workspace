"""
General Agent – plain local LLM answers with no extra tools.

Used when the supervisor classifies the query as general knowledge,
conversation, or anything that does not need RAG / data / files / code / vision.
"""

import logging
from datetime import datetime

from app.agents.state import AgentState
from app.services.llm_service import ollama_service

logger = logging.getLogger(__name__)

_GENERAL_PROMPT = """\
You are a helpful local assistant running fully offline.

User question: {question}

Answer clearly and concisely. If you are unsure, say so.

Answer:"""


async def general_agent_node(state: AgentState) -> AgentState:
    """General agent node: answer with the local LLM only."""
    query = state["user_query"]
    logger.info("[General Agent] Processing: %r", query[:80])

    step = {
        "agent": "general_agent",
        "action": "llm_generate",
        "result": "",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        result = await ollama_service.generate(
            prompt=_GENERAL_PROMPT.format(question=query),
            temperature=0.7,
        )
        answer = result["response"]
        step["result"] = "Generated a general LLM response"
    except Exception as e:
        logger.error("[General Agent] Error: %s", e, exc_info=True)
        answer = f"The local LLM could not answer: {e}"
        step["result"] = f"Error: {e}"

    return {
        **state,
        "final_answer": answer,
        "active_agent": "general_agent",
        "agent_steps": state.get("agent_steps", []) + [step],
    }
