"""
AI Guardrails — scan LLM inputs/outputs for security violations.

Output scanning:
    - PII patterns (SSN, credit cards, phone numbers, emails)
    - Internal data patterns (IP addresses, API keys, passwords)
    - Configurable sensitivity per role

Input scanning:
    - Prompt injection detection
    - Jailbreak attempt detection
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of a guardrail scan."""
    is_safe: bool = True
    violations: list[dict] = field(default_factory=list)
    sanitized_text: Optional[str] = None

    def add_violation(self, category: str, pattern: str, match: str) -> None:
        self.is_safe = False
        self.violations.append({
            "category": category,
            "pattern": pattern,
            "match": match[:50],  # Truncate for logging safety
        })


# ── PII / Sensitive Data Patterns ──

PII_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[- ]?){3}\d{4}\b",
    "phone_us": r"\b(?:\+1)?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
    "email_address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "api_key": r"\b(?:sk|pk|api|key|token|secret)[_-]?[A-Za-z0-9]{20,}\b",
    "password_leak": r"(?i)(?:password|passwd|pwd)\s*[:=]\s*\S+",
}

# ── Prompt Injection Patterns ──

INJECTION_PATTERNS = {
    "ignore_instructions": r"(?i)(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions|prompts|rules)",
    "role_override": r"(?i)(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be|switch\s+to)\s+(?:a\s+)?(?:different|new|evil|unrestricted)",
    "system_prompt_extract": r"(?i)(?:show|reveal|print|output|display)\s+(?:your\s+)?(?:system\s+prompt|instructions|rules|initial\s+prompt)",
    "jailbreak_dan": r"(?i)(?:DAN|do\s+anything\s+now|developer\s+mode|unlocked\s+mode)",
    "encoding_bypass": r"(?i)(?:base64|rot13|hex\s+encode|reverse\s+the\s+text)",
}


class Guardrails:
    """Scan text for security violations."""

    def scan_output(self, text: str, role: str = "employee") -> ScanResult:
        """
        Scan LLM output for PII and sensitive data leaks.
        Admin users get lighter scanning (warnings only).
        """
        result = ScanResult(sanitized_text=text)

        for category, pattern in PII_PATTERNS.items():
            matches = re.findall(pattern, text)
            for match in matches:
                result.add_violation("pii", category, match)

        # For employee role, redact violations from output
        if not result.is_safe and role == "employee":
            sanitized = text
            for v in result.violations:
                if v["category"] == "pii":
                    sanitized = re.sub(
                        PII_PATTERNS[v["pattern"]],
                        f"[REDACTED-{v['pattern'].upper()}]",
                        sanitized,
                    )
            result.sanitized_text = sanitized

        if not result.is_safe:
            logger.warning(
                "[Guardrails] Output violations: %d | role=%s",
                len(result.violations), role,
            )

        return result

    def scan_input(self, text: str) -> ScanResult:
        """Scan user input for prompt injection and jailbreak attempts."""
        result = ScanResult()

        for category, pattern in INJECTION_PATTERNS.items():
            matches = re.findall(pattern, text)
            for match in matches:
                result.add_violation("injection", category, match if isinstance(match, str) else match[0])

        if not result.is_safe:
            logger.warning(
                "[Guardrails] Input injection detected: %d violations",
                len(result.violations),
            )

        return result

    def get_policy(self) -> dict:
        """Return current guardrail configuration (for admin UI)."""
        return {
            "pii_patterns": list(PII_PATTERNS.keys()),
            "injection_patterns": list(INJECTION_PATTERNS.keys()),
            "pii_count": len(PII_PATTERNS),
            "injection_count": len(INJECTION_PATTERNS),
        }


guardrails = Guardrails()
