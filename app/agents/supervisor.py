"""
Supervisor Agent – Intent Detection & Routing.

Analyzes the user's query and file context to determine which
specialized agent should handle it, then returns the routing decision.

Intent Classes:
    rag     – Question answerable from indexed documents
    data    – Tabular/CSV/JSON data analysis
    file    – File system operations (read/write/list)
    code    – Write & execute Python code
    vision  – Image/OCR understanding
    general – General LLM answer (no specialized tool needed)
"""

import json
import logging
import re
from datetime import datetime

from app.agents.state import AgentState
from app.services.llm_service import ollama_service

logger = logging.getLogger(__name__)

# ── Intent classification prompt ──────────────────────────────────────────────

_INTENT_PROMPT = """\
You are an intent classifier for a multi-agent AI system. Classify the user's \
query into exactly ONE of these intents:

- rag     : The user wants to search or query uploaded/indexed documents (PDF, DOCX, etc.)
- data    : The user wants to analyze tabular data (CSV, JSON, Excel) with statistics
- file    : The user wants to read, write, or list files on the local file system
- code    : The user wants to write and/or execute Python code
- vision  : The user wants to extract text or understand an image/photo
- general : Everything else (general knowledge, conversation, math, etc.)

Uploaded file types hint: {file_hints}

User query: {query}

Respond with a single JSON object, nothing else:
{{"intent": "<one of: rag|data|file|code|vision|general>", "reason": "<one sentence>"}}
"""


async def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor node: classify the query intent and set routing.

    Reads the user_query and file_paths from state, calls the LLM
    to classify intent, and writes the 'intent' field back to state.
    """
    query = state["user_query"]
    file_paths = state.get("file_paths", [])

    # Build file hint string for the classifier
    file_hints = "none"
    if file_paths:
        exts = [p.rsplit(".", 1)[-1].lower() for p in file_paths if "." in p]
        file_hints = ", ".join(set(exts)) if exts else "unknown"

    logger.info(f"[Supervisor] Classifying intent for query: {query[:80]!r}")

    step = {
        "agent": "supervisor",
        "action": "intent_classification",
        "result": "classifying…",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        prompt = _INTENT_PROMPT.format(query=query, file_hints=file_hints)
        result = await ollama_service.generate(
            prompt=prompt,
            temperature=0.0,
        )
        raw = result["response"].strip()

        # Extract JSON (handle markdown fences)
        json_match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            intent = parsed.get("intent", "general").lower()
            reason = parsed.get("reason", "")
        else:
            intent = "general"
            reason = "Could not parse intent — defaulting to general"

        # Validate intent
        valid_intents = {"rag", "data", "file", "code", "vision", "general"}
        if intent not in valid_intents:
            intent = "general"

        step["result"] = f"Intent: {intent} — {reason}"
        logger.info(f"[Supervisor] Intent = {intent!r} | Reason: {reason}")

    except Exception as e:
        logger.error(f"[Supervisor] Classification failed: {e}")
        intent = "general"
        step["result"] = f"Classification error, defaulting to general: {e}"

    return {
        **state,
        "intent": intent,
        "active_agent": "supervisor",
        "agent_steps": state.get("agent_steps", []) + [step],
    }


def route_to_agent(state: AgentState) -> str:
    """
    Conditional edge: maps intent → node name in the graph.

    Returns the name of the next node to execute.
    """
    intent_map = {
        "rag":     "rag_agent",
        "data":    "data_agent",
        "file":    "file_agent",
        "code":    "code_agent",
        "vision":  "vision_agent",
        "general": "general_agent",
    }
    intent = state.get("intent", "general")
    return intent_map.get(intent, "general_agent")
