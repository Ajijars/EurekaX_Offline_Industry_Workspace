"""
Query Sanitizer — validate and restrict SQL/MongoDB queries by user role.

Rules:
    Employee tier:
        - SQL: block DROP, DELETE, ALTER, TRUNCATE, CREATE, GRANT
        - MongoDB: block $where, $function, db.dropDatabase, db.dropCollection
    Admin tier:
        - All queries allowed (with audit logging)
"""

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SanitizeResult:
    is_safe: bool = True
    blocked_reason: str = ""
    warnings: list[str] = field(default_factory=list)


# ── SQL Dangerous Patterns (blocked for employee) ──

SQL_BLOCKED_EMPLOYEE = [
    (r"(?i)\b(DROP)\s+(TABLE|DATABASE|INDEX|VIEW|SCHEMA)\b", "DROP statement"),
    (r"(?i)\b(DELETE)\s+FROM\b", "DELETE FROM statement"),
    (r"(?i)\b(ALTER)\s+(TABLE|DATABASE)\b", "ALTER statement"),
    (r"(?i)\b(TRUNCATE)\s+(TABLE)?\b", "TRUNCATE statement"),
    (r"(?i)\b(CREATE)\s+(TABLE|DATABASE|INDEX|VIEW|SCHEMA)\b", "CREATE statement"),
    (r"(?i)\b(GRANT|REVOKE)\b", "GRANT/REVOKE statement"),
    (r"(?i)\b(INSERT)\s+INTO\b", "INSERT INTO statement"),
    (r"(?i)\b(UPDATE)\s+\w+\s+SET\b", "UPDATE statement"),
    (r"(?i)\bEXEC(UTE)?\b", "EXECUTE statement"),
    (r"(?i)\bxp_\w+", "Extended stored procedure"),
]

# ── MongoDB Dangerous Patterns (blocked for employee) ──

MONGO_BLOCKED_EMPLOYEE = [
    (r"\$where", "$where operator (JS execution)"),
    (r"\$function", "$function operator"),
    (r"\$accumulator", "$accumulator operator"),
    (r"db\s*\.\s*drop", "db.drop operation"),
    (r"db\s*\.\s*\w+\s*\.\s*drop", "collection.drop operation"),
    (r"db\s*\.\s*\w+\s*\.\s*remove\s*\(\s*\{\s*\}\s*\)", "Remove all documents"),
    (r"db\s*\.\s*\w+\s*\.\s*deleteMany\s*\(\s*\{\s*\}\s*\)", "Delete all documents"),
]

# ── SQL Injection Patterns (blocked for everyone) ──

SQL_INJECTION_PATTERNS = [
    (r";\s*--", "SQL comment injection"),
    (r"'\s*OR\s+'1'\s*=\s*'1", "Classic OR injection"),
    (r"'\s*OR\s+1\s*=\s*1", "Numeric OR injection"),
    (r"UNION\s+SELECT", "UNION SELECT injection"),
    (r";\s*(DROP|DELETE|ALTER|TRUNCATE)", "Chained destructive statement"),
]


class QuerySanitizer:
    """Validate queries based on user role."""

    def sanitize_sql(self, query: str, role: str = "employee") -> SanitizeResult:
        """Check a SQL query for safety violations."""
        result = SanitizeResult()

        # Always block injection patterns
        for pattern, reason in SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                result.is_safe = False
                result.blocked_reason = f"SQL injection detected: {reason}"
                logger.warning("[QuerySanitizer] Blocked SQL injection: %s", reason)
                return result

        # Employee restrictions
        if role == "employee":
            for pattern, reason in SQL_BLOCKED_EMPLOYEE:
                if re.search(pattern, query):
                    result.is_safe = False
                    result.blocked_reason = f"Insufficient permissions: {reason} requires admin access"
                    logger.warning("[QuerySanitizer] Employee blocked: %s", reason)
                    return result

        # Admin: add warnings but don't block
        if role == "admin":
            for pattern, reason in SQL_BLOCKED_EMPLOYEE:
                if re.search(pattern, query):
                    result.warnings.append(f"Destructive operation: {reason}")

        return result

    def sanitize_mongodb(self, query: str, role: str = "employee") -> SanitizeResult:
        """Check a MongoDB query string for safety violations."""
        result = SanitizeResult()

        if role == "employee":
            for pattern, reason in MONGO_BLOCKED_EMPLOYEE:
                if re.search(pattern, query, re.IGNORECASE):
                    result.is_safe = False
                    result.blocked_reason = f"Insufficient permissions: {reason} requires admin access"
                    logger.warning("[QuerySanitizer] Employee blocked MongoDB: %s", reason)
                    return result

        return result

    def get_policy(self) -> dict:
        return {
            "sql_blocked_employee": [r[1] for r in SQL_BLOCKED_EMPLOYEE],
            "mongo_blocked_employee": [r[1] for r in MONGO_BLOCKED_EMPLOYEE],
            "injection_patterns": [r[1] for r in SQL_INJECTION_PATTERNS],
        }


query_sanitizer = QuerySanitizer()
