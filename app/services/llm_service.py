"""
Ollama LLM Service – handles all communication with the Ollama HTTP API.

Provides synchronous generation, async streaming, model listing, and health checks.
Uses httpx for async HTTP requests to the Ollama server.
"""

import json
import time
import logging
from typing import AsyncGenerator

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class OllamaService:
    """Service class wrapping the Ollama REST API."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.OLLAMA_BASE_URL
        self.default_model = settings.OLLAMA_MODEL
        self.timeout = httpx.Timeout(
            connect=10.0,     # 10s to establish connection
            read=120.0,       # 120s to wait for response (LLM can be slow)
            write=10.0,
            pool=10.0
        )

    # ──────────────────────────────────────────────
    # Health & Discovery
    # ──────────────────────────────────────────────

    async def check_health(self) -> bool:
        """Check if the Ollama server is running and reachable."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> list[dict]:
        """List all models available in the local Ollama instance."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                models = []
                for model in data.get("models", []):
                    size_bytes = model.get("size", 0)
                    size_gb = round(size_bytes / (1024 ** 3), 2) if size_bytes else None
                    models.append({
                        "name": model.get("name", "unknown"),
                        "size": size_gb,
                        "modified_at": model.get("modified_at")
                    })
                return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    # ──────────────────────────────────────────────
    # Generation (Synchronous)
    # ──────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        conversation_history: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> dict:
        """
        Generate a complete response from Ollama (non-streaming).

        Args:
            prompt: The user's message
            model: Model to use (falls back to default)
            conversation_history: Previous messages for context
            temperature: Sampling temperature
        
        Returns:
            Dict with 'response', 'model', 'total_duration_ms', 'tokens_per_second'
        """
        model = model or self.default_model
        start_time = time.time()

        # Build messages list for chat API
        messages = self._build_messages(prompt, conversation_history)

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

            elapsed_ms = (time.time() - start_time) * 1000

            # Extract timing info from Ollama response
            total_duration = data.get("total_duration", 0)
            eval_count = data.get("eval_count", 0)
            eval_duration = data.get("eval_duration", 0)

            tokens_per_second = None
            if eval_duration > 0:
                tokens_per_second = round(
                    eval_count / (eval_duration / 1e9), 2
                )

            return {
                "response": data.get("message", {}).get("content", ""),
                "model": model,
                "total_duration_ms": round(elapsed_ms, 2),
                "tokens_per_second": tokens_per_second
            }

        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running: 'ollama serve'"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(
                    f"Model '{model}' not found. "
                    f"Pull it first: 'ollama pull {model}'"
                )
            raise RuntimeError(f"Ollama API error: {e.response.text}")
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise RuntimeError(f"Failed to generate response: {str(e)}")

    # ──────────────────────────────────────────────
    # Generation (Streaming via SSE)
    # ──────────────────────────────────────────────

    async def generate_stream(
        self,
        prompt: str,
        model: str | None = None,
        conversation_history: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from Ollama token-by-token.

        Yields JSON strings containing partial response chunks, suitable
        for Server-Sent Events (SSE).
        """
        model = model or self.default_model
        messages = self._build_messages(prompt, conversation_history)

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                content = data.get("message", {}).get("content", "")
                                done = data.get("done", False)
                                chunk = {
                                    "content": content,
                                    "done": done,
                                    "model": model
                                }
                                if done:
                                    # Include final timing stats
                                    eval_count = data.get("eval_count", 0)
                                    eval_duration = data.get("eval_duration", 0)
                                    if eval_duration > 0:
                                        chunk["tokens_per_second"] = round(
                                            eval_count / (eval_duration / 1e9), 2
                                        )
                                yield json.dumps(chunk)
                            except json.JSONDecodeError:
                                continue

        except httpx.ConnectError:
            yield json.dumps({
                "error": f"Cannot connect to Ollama at {self.base_url}. "
                         "Ensure Ollama is running: 'ollama serve'",
                "done": True
            })
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Model '{model}' not found. Pull it: 'ollama pull {model}'"
                if e.response.status_code == 404
                else f"Ollama error: {e.response.text}"
            )
            yield json.dumps({"error": error_msg, "done": True})
        except Exception as e:
            logger.error(f"Stream generation failed: {e}")
            yield json.dumps({
                "error": f"Streaming failed: {str(e)}",
                "done": True
            })

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _build_messages(
        self,
        prompt: str,
        conversation_history: list[dict] | None = None
    ) -> list[dict]:
        """
        Build the messages list for Ollama's chat API.
        
        Includes a system prompt, any conversation history,
        and the current user message.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful, knowledgeable AI assistant. "
                    "Provide clear, accurate, and well-structured answers. "
                    "Use markdown formatting when appropriate for code blocks, "
                    "lists, and emphasis."
                )
            }
        ]

        # Append conversation history
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        # Append current user message
        messages.append({
            "role": "user",
            "content": prompt
        })

        return messages


# Singleton service instance
ollama_service = OllamaService()
