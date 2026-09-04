"""
Vision Agent – Image Understanding & OCR.

Extracts text from images using pytesseract OCR, then uses the LLM
to answer questions about the image content.
"""

import logging
from datetime import datetime
from pathlib import Path

from app.agents.state import AgentState
from app.agents.tools import extract_image_text
from app.services.llm_service import ollama_service

logger = logging.getLogger(__name__)

_VISION_PROMPT = """\
You are a vision assistant helping a user understand an image.

Image metadata:
- File: {path}
- Dimensions: {width} × {height} pixels
- Color mode: {mode}

Extracted text from the image (via OCR):
---
{text}
---

User question: {question}

Based on the extracted text and image metadata, provide a helpful answer. \
If OCR was unable to extract text, explain what might be in the image based on the metadata.

Answer:"""

# Common image extensions
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif", ".webp"}


async def vision_agent_node(state: AgentState) -> AgentState:
    """
    Vision agent node: extract text from image → answer question about it.
    """
    query = state["user_query"]
    file_paths = state.get("file_paths", [])
    logger.info(f"[Vision Agent] Processing: {query[:80]!r}")

    step = {
        "agent": "vision_agent",
        "action": "image_ocr",
        "result": "",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Find an image file
    image_file = None
    for fp in file_paths:
        if any(fp.lower().endswith(ext) for ext in _IMAGE_EXTENSIONS):
            image_file = fp
            break

    if not image_file:
        # Try uploads directory for image files
        uploads = Path("uploads")
        if uploads.exists():
            for f in sorted(uploads.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.suffix.lower() in _IMAGE_EXTENSIONS:
                    image_file = str(f)
                    break

    if not image_file:
        answer = (
            "No image file was found. Please upload an image (PNG, JPG, etc.) "
            "and then ask your question about it."
        )
        step["result"] = "No image file found."
        return {
            **state,
            "final_answer": answer,
            "active_agent": "vision_agent",
            "agent_steps": state.get("agent_steps", []) + [step],
        }

    try:
        # 1. Extract text via OCR
        ocr_result = await extract_image_text(image_file)

        if not ocr_result.get("success"):
            raise RuntimeError(ocr_result.get("error", "OCR failed"))

        step["result"] = (
            f"Processed image {Path(image_file).name} "
            f"({ocr_result['width']}×{ocr_result['height']}px) | "
            f"OCR: {'yes' if ocr_result.get('ocr_used') else 'unavailable'} | "
            f"Text chars: {len(ocr_result.get('text', ''))}"
        )

        # 2. Generate answer
        prompt = _VISION_PROMPT.format(
            path=Path(image_file).name,
            width=ocr_result["width"],
            height=ocr_result["height"],
            mode=ocr_result["mode"],
            text=ocr_result.get("text", "(no text extracted)") or "(no text extracted)",
            question=query,
        )
        llm_result = await ollama_service.generate(prompt=prompt, temperature=0.4)
        answer = llm_result["response"]

    except Exception as e:
        logger.error(f"[Vision Agent] Error: {e}", exc_info=True)
        answer = f"Vision processing failed: {e}"
        step["result"] = f"Error: {e}"

    return {
        **state,
        "final_answer": answer,
        "active_agent": "vision_agent",
        "agent_steps": state.get("agent_steps", []) + [step],
    }
