"""
File Agent – Local File System Operations.

Handles reading, writing, and listing files within the project workspace.
Provides the LLM with file content to answer questions or instructs it
to compose file content for write operations.
"""

import logging
from datetime import datetime

from app.agents.state import AgentState
from app.agents.tools import read_file, write_file, list_files
from app.services.llm_service import ollama_service
from app.config import get_settings

logger = logging.getLogger(__name__)

_FILE_INTENT_PROMPT = """\
Classify the user's file operation intent into one of: read | write | list

User query: {query}

Respond with JSON only:
{{"operation": "read|write|list", "path": "<file path or directory if mentioned, else null>", \
"content": "<content to write if write operation, else null>"}}
"""

_FILE_ANSWER_PROMPT = """\
The user asked: {question}

File operation result:
{result}

Provide a helpful summary of what was found/done.
Answer:"""


async def file_agent_node(state: AgentState) -> AgentState:
    """
    File agent node: parse operation intent → execute file tool → summarize result.
    """
    import json, re
    query = state["user_query"]
    file_paths = state.get("file_paths", [])
    settings = get_settings()
    workspace = settings.WORKSPACE_DIR

    logger.info(f"[File Agent] Processing: {query[:80]!r}")

    step = {
        "agent": "file_agent",
        "action": "file_operation",
        "result": "",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # 1. Classify file operation
        intent_result = await ollama_service.generate(
            prompt=_FILE_INTENT_PROMPT.format(query=query),
            temperature=0.0,
        )
        raw = intent_result["response"].strip()
        json_match = re.search(r'\{.*?\}', raw, re.DOTALL)

        operation = "list"
        target_path = None
        write_content = None

        if json_match:
            parsed = json.loads(json_match.group())
            operation = parsed.get("operation", "list")
            target_path = parsed.get("path")
            write_content = parsed.get("content")

        # 2. Execute operation
        if operation == "list":
            dir_path = target_path or "."
            tool_result = await list_files(dir_path, workspace_dir=workspace)
            if tool_result.get("success"):
                entries = tool_result.get("entries", [])
                result_text = f"Directory '{dir_path}' contains {len(entries)} items:\n"
                result_text += "\n".join(
                    f"  {'📁' if e['type'] == 'directory' else '📄'} {e['name']}"
                    + (f" ({e.get('size_bytes', 0)} bytes)" if e['type'] == 'file' else "")
                    for e in entries
                )
            else:
                result_text = f"Error: {tool_result.get('error')}"
            step["action"] = f"list_files({dir_path})"

        elif operation == "read":
            # Prefer uploaded files, fall back to workspace
            path = target_path
            if not path and file_paths:
                path = file_paths[0]
            elif not path:
                path = "."

            tool_result = await read_file(path, workspace_dir=workspace)
            if tool_result.get("success"):
                result_text = f"File: {tool_result['path']} ({tool_result['size_bytes']} bytes)\n\n"
                result_text += tool_result["content"]
            else:
                result_text = f"Error: {tool_result.get('error')}"
            step["action"] = f"read_file({path})"

        elif operation == "write":
            path = target_path or "output.txt"
            content = write_content or ""
            tool_result = await write_file(path, content, workspace_dir=workspace)
            if tool_result.get("success"):
                result_text = f"File written successfully: {tool_result['path']} ({tool_result['size_bytes']} bytes)"
            else:
                result_text = f"Error: {tool_result.get('error')}"
            step["action"] = f"write_file({path})"

        else:
            result_text = f"Unknown operation: {operation}"

        step["result"] = result_text[:300]

        # 3. Generate LLM summary
        prompt = _FILE_ANSWER_PROMPT.format(question=query, result=result_text[:3000])
        llm_result = await ollama_service.generate(prompt=prompt, temperature=0.3)
        answer = llm_result["response"]

    except Exception as e:
        logger.error(f"[File Agent] Error: {e}", exc_info=True)
        answer = f"File operation failed: {e}"
        step["result"] = f"Error: {e}"

    return {
        **state,
        "final_answer": answer,
        "active_agent": "file_agent",
        "agent_steps": state.get("agent_steps", []) + [step],
    }
