"""
Data Agent – Tabular Data Analysis + optional Databricks SQL.

Loads CSV, JSON, or Excel files and uses pandas to compute statistics,
or runs SQL against Databricks Delta Lake when configured.
Then has the LLM interpret the results and answer the user's question.
"""

import json
import logging
import re
from datetime import datetime

from app.agents.state import AgentState
from app.agents.tools import analyze_data, query_databricks
from app.config import get_settings
from app.services.llm_service import ollama_service

logger = logging.getLogger(__name__)

_DATA_PROMPT = """\
You are a data analyst assistant. The user asked a question about some data.

Data summary:
- File: {filename}
- Rows: {rows} | Columns: {columns}
- Column types: {dtypes}
- Missing values: {missing}

Descriptive statistics:
{stats}

Sample rows (first 5):
{sample}

User question: {question}

Provide a clear, insightful answer based on the data above. \
Include specific numbers and observations where relevant.

Answer:"""

_SQL_FROM_NL_PROMPT = """\
Convert the user's question into a single Databricks SQL query.
Return ONLY the SQL, no markdown fences or explanation.

User question: {question}

SQL:"""

_SQL_ANSWER_PROMPT = """\
You are a data analyst. The user asked a question that was answered with SQL.

SQL executed:
{sql}

Columns: {columns}
Row count: {row_count}
Rows (JSON):
{rows}

User question: {question}

Explain the results clearly. Include specific numbers.

Answer:"""

_SQL_HINTS = (
    "select ", " from ", "databricks", "delta lake", "delta table",
    "sql warehouse", "unity catalog", "warehouse",
)


def _wants_databricks(query: str) -> bool:
    q = query.lower()
    return any(hint in q for hint in _SQL_HINTS) or q.strip().startswith(("select", "with ", "show ", "describe "))


def _extract_sql(raw: str) -> str:
    fence = re.search(r"```(?:sql)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip().rstrip(";")
    return raw.strip().rstrip(";")


async def data_agent_node(state: AgentState) -> AgentState:
    """
    Data agent node: local file analysis or Databricks SQL, then LLM interpretation.
    """
    query = state["user_query"]
    file_paths = state.get("file_paths", [])
    settings = get_settings()
    logger.info(f"[Data Agent] Processing: {query[:80]!r}")

    step = {
        "agent": "data_agent",
        "action": "data_analysis",
        "result": "",
        "timestamp": datetime.utcnow().isoformat(),
    }

    data_extensions = {".csv", ".json", ".xls", ".xlsx"}
    data_file = None
    for fp in file_paths:
        if any(fp.lower().endswith(ext) for ext in data_extensions):
            data_file = fp
            break

    use_databricks = _wants_databricks(query) or (
        not data_file and bool(settings.DATABRICKS_HOST and settings.DATABRICKS_TOKEN)
    )

    try:
        if use_databricks and (settings.DATABRICKS_HOST or _wants_databricks(query)):
            answer, step = await _run_databricks(query, step)
            if answer is not None:
                return {
                    **state,
                    "final_answer": answer,
                    "active_agent": "data_agent",
                    "agent_steps": state.get("agent_steps", []) + [step],
                }

        if not data_file:
            # Fallback to querying the internal data catalog!
            from app.agents.catalog_tool import get_catalog_context, execute_catalog_query
            
            catalog_context = await get_catalog_context()
            
            # Step 1: Generate SQL for the catalog
            sql_prompt = (
                f"Convert the user's question into a SQLite SQL query against the internal catalog.\n\n"
                f"{catalog_context}\n\n"
                f"User question: {query}\n\n"
                f"SQL:"
            )
            
            sql_res = await ollama_service.generate(prompt=sql_prompt, temperature=0.0)
            sql_query = _extract_sql(sql_res["response"])
            
            step["result"] = f"Generated Catalog SQL: {sql_query}"
            
            # Step 2: Execute SQL
            rows_json = await execute_catalog_query(sql_query)
            
            # Step 3: Interpret
            answer_prompt = (
                f"You are a data analyst. The user asked a question that was answered with SQL.\n\n"
                f"SQL executed: {sql_query}\n\n"
                f"Rows (JSON): {rows_json}\n\n"
                f"User question: {query}\n\n"
                f"Explain the results clearly.\n\n"
                f"Answer:"
            )
            
            final_res = await ollama_service.generate(prompt=answer_prompt, temperature=0.2)
            answer = final_res["response"]
            
            step["result"] += f" | Retrieved {len(json.loads(rows_json)) if rows_json.startswith('[') else 0} rows"
            
            return {
                **state,
                "final_answer": answer,
                "active_agent": "data_agent",
                "agent_steps": state.get("agent_steps", []) + [step],
            }

        data_result = await analyze_data(data_file)

        if not data_result.get("success"):
            raise RuntimeError(data_result.get("error", "Unknown analysis error"))

        step["result"] = (
            f"Analyzed {data_result['filename']}: "
            f"{data_result['rows']} rows × {len(data_result['columns'])} columns"
        )

        prompt = _DATA_PROMPT.format(
            filename=data_result["filename"],
            rows=data_result["rows"],
            columns=", ".join(data_result["columns"]),
            dtypes=json.dumps(data_result["dtypes"], indent=2),
            missing=json.dumps(data_result["missing_values"]),
            stats=json.dumps(data_result["stats"], indent=2)[:3000],
            sample=json.dumps(data_result["sample"], indent=2)[:2000],
            question=query,
        )
        result = await ollama_service.generate(prompt=prompt, temperature=0.2)
        answer = result["response"]

    except Exception as e:
        logger.error(f"[Data Agent] Error: {e}", exc_info=True)
        answer = f"Data analysis failed: {e}"
        step["result"] = f"Error: {e}"

    return {
        **state,
        "final_answer": answer,
        "active_agent": "data_agent",
        "agent_steps": state.get("agent_steps", []) + [step],
    }


async def _run_databricks(query: str, step: dict) -> tuple[str | None, dict]:
    """
    Try Databricks. Returns (answer, step) if a query was attempted,
    or (None, step) to fall through to local files.
    """
    sql_candidate = query.strip()
    if not re.match(r"(?is)^(select|with|show|describe)\b", sql_candidate):
        gen = await ollama_service.generate(
            prompt=_SQL_FROM_NL_PROMPT.format(question=query),
            temperature=0.0,
        )
        sql_candidate = _extract_sql(gen["response"])

    db_result = await query_databricks(sql_candidate)
    if not db_result.get("configured", True) and not db_result.get("success"):
        # Not configured — let caller try local files
        step["result"] = db_result.get("error", "Databricks not configured")
        return None, step

    if not db_result.get("success"):
        step["action"] = "databricks_sql"
        step["result"] = f"Databricks error: {db_result.get('error')}"
        return f"Databricks query failed: {db_result.get('error')}", step

    step["action"] = "databricks_sql"
    step["result"] = (
        f"Ran SQL against Databricks ({db_result.get('row_count', 0)} rows)"
    )

    prompt = _SQL_ANSWER_PROMPT.format(
        sql=sql_candidate,
        columns=", ".join(db_result.get("columns") or []),
        row_count=db_result.get("row_count", 0),
        rows=json.dumps(db_result.get("rows", [])[:50], indent=2, default=str)[:4000],
        question=query,
    )
    llm = await ollama_service.generate(prompt=prompt, temperature=0.2)
    return llm["response"], step
