"""
Code Agent – Python Code Generation & Execution.

Uses the LLM to write Python code that solves the user's problem,
then executes it in an isolated subprocess sandbox and returns
both the code and its output.
"""

import logging
import re
from datetime import datetime

from app.agents.state import AgentState
from app.agents.tools import execute_python
from app.services.llm_service import ollama_service
from app.config import get_settings

logger = logging.getLogger(__name__)

_CODE_GEN_PROMPT = """\
You are an expert Python developer. Write clean, working Python code to solve \
the user's request. The code will be executed in a sandbox.

Rules:
- Use only standard library modules unless pandas or numpy are needed
- Do NOT use input() or any interactive functions
- Print the result(s) clearly using print()
- Keep the code concise and focused

User request: {query}

Write ONLY the Python code, no explanations before or after:
```python
"""

_CODE_EXPLAIN_PROMPT = """\
The user asked: {question}

Python code that was executed:
```python
{code}
```

Execution result:
- Exit code: {exit_code}
- Output: {stdout}
- Errors: {stderr}

Explain what the code does and what the output means in plain English.
Answer:"""


async def code_agent_node(state: AgentState) -> AgentState:
    """
    Code agent node: generate Python code → execute in sandbox → explain result.
    """
    query = state["user_query"]
    settings = get_settings()
    logger.info(f"[Code Agent] Processing: {query[:80]!r}")

    step = {
        "agent": "code_agent",
        "action": "code_generation",
        "result": "",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # 1. Generate code with LLM
        gen_result = await ollama_service.generate(
            prompt=_CODE_GEN_PROMPT.format(query=query),
            temperature=0.1,
        )
        raw_code = gen_result["response"].strip()

        # Extract code from markdown fences
        code_match = re.search(r'```(?:python)?\s*(.*?)```', raw_code, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
        else:
            code = raw_code.strip()
            # Remove any trailing ``` if generation was cut off
            code = re.sub(r'```$', '', code).strip()

        step["action"] = "code_generation + execution"
        step["result"] = f"Generated {len(code.splitlines())} lines of Python code"

        # 2. Execute in sandbox
        exec_result = await execute_python(
            code=code,
            timeout=30,
            sandbox_dir=settings.SANDBOX_DIR,
        )

        step["result"] += (
            f" | Exit: {exec_result['exit_code']} | "
            f"Time: {exec_result.get('execution_time_ms', 0)}ms"
        )

        # 3. Explain result
        prompt = _CODE_EXPLAIN_PROMPT.format(
            question=query,
            code=code,
            exit_code=exec_result["exit_code"],
            stdout=exec_result.get("stdout", "")[:2000],
            stderr=exec_result.get("stderr", "")[:500],
        )
        explain_result = await ollama_service.generate(prompt=prompt, temperature=0.3)
        answer_text = explain_result["response"]

        # Prepend code block and output to the answer
        answer = (
            f"**Generated Code:**\n```python\n{code}\n```\n\n"
            f"**Output:**\n```\n{exec_result.get('stdout', '(no output)')}\n```\n\n"
            f"**Explanation:**\n{answer_text}"
        )
        if exec_result.get("stderr"):
            answer += f"\n\n**Errors:**\n```\n{exec_result['stderr']}\n```"

    except Exception as e:
        logger.error(f"[Code Agent] Error: {e}", exc_info=True)
        answer = f"Code execution failed: {e}"
        step["result"] = f"Error: {e}"

    return {
        **state,
        "final_answer": answer,
        "active_agent": "code_agent",
        "agent_steps": state.get("agent_steps", []) + [step],
    }
