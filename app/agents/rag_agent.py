"""
RAG Agent – Document Search & Answer Generation.

Uses the existing RAG pipeline (Qdrant + BGE embeddings + Ollama) to
retrieve relevant document chunks and generate a grounded answer.
"""

import logging
from datetime import datetime

from app.agents.state import AgentState
from app.agents.tools import search_documents
from app.services.llm_service import ollama_service

logger = logging.getLogger(__name__)

_RAG_ANSWER_PROMPT = """\
You are a helpful assistant that answers questions based on retrieved document context.

Retrieved context:
{context}

User question: {question}

Provide a clear, accurate answer based on the context above. \
Cite sources by mentioning the filename when relevant. \
If the context doesn't contain the answer, say so honestly.

Answer:"""


async def rag_agent_node(state: AgentState) -> AgentState:
    """
    RAG agent node: search documents → build context → generate answer.
    """
    query = state["user_query"]
    logger.info(f"[RAG Agent] Processing: {query[:80]!r}")

    step = {
        "agent": "rag_agent",
        "action": "document_search",
        "result": "",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # 1. Search Qdrant
        search_result = await search_documents(query, top_k=5)
        chunks = search_result.get("results", [])
        count = search_result.get("count", 0)

        if not chunks:
            answer = (
                "I couldn't find relevant information in the indexed documents. "
                "Please upload relevant documents first, or try rephrasing your question."
            )
            step["result"] = f"No documents found for query. Returning fallback answer."
            step["action"] = "document_search (no results)"
        else:
            # 2. Build context block
            context_parts = []
            for i, chunk in enumerate(chunks, 1):
                filename = chunk.get("filename", "unknown")
                score = round(chunk.get("score", 0), 3)
                text = chunk.get("chunk_text", "")
                context_parts.append(f"[Doc {i} – {filename} (score: {score})]:\n{text}")
            context = "\n\n".join(context_parts)

            # 3. Generate answer
            prompt = _RAG_ANSWER_PROMPT.format(context=context, question=query)
            result = await ollama_service.generate(prompt=prompt, temperature=0.3)
            answer = result["response"]

            step["result"] = (
                f"Found {count} relevant chunks from documents. "
                f"Sources: {list({c.get('filename') for c in chunks})}"
            )
            step["action"] = f"document_search ({count} chunks retrieved)"

    except Exception as e:
        logger.error(f"[RAG Agent] Error: {e}", exc_info=True)
        answer = f"RAG search encountered an error: {e}"
        step["result"] = f"Error: {e}"

    return {
        **state,
        "final_answer": answer,
        "active_agent": "rag_agent",
        "agent_steps": state.get("agent_steps", []) + [step],
        "metadata": {**state.get("metadata", {}), "rag_chunks": len(chunks) if "chunks" in dir() else 0},
    }
