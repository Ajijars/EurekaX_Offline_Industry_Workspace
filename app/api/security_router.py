"""
Security API Router — guardrail policies, alerts, anomaly management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import require_admin, get_current_user
from app.db.database import get_db
from app.db.models import User
from app.security.guardrails import guardrails
from app.security.query_sanitizer import query_sanitizer
from app.security.anomaly_detector import anomaly_detector

logger = logging.getLogger(__name__)
security_router = APIRouter(prefix="/api/security", tags=["Security"])


@security_router.get("/policies")
async def get_policies(user: User = Depends(get_current_user)):
    """Get current security policies configuration."""
    return {
        "guardrails": guardrails.get_policy(),
        "query_sanitizer": query_sanitizer.get_policy(),
        "rate_limits": {
            "max_queries_per_minute": anomaly_detector.MAX_QUERIES_PER_MINUTE,
            "max_queries_per_hour": anomaly_detector.MAX_QUERIES_PER_HOUR,
            "bulk_row_threshold": anomaly_detector.BULK_ROW_THRESHOLD,
        },
    }


@security_router.get("/alerts")
async def get_alerts(
    resolved: Optional[bool] = None, limit: int = Query(default=50, le=200),
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db),
):
    """Get security alerts (admin only)."""
    return await anomaly_detector.get_alerts(db, resolved=resolved, limit=limit)


@security_router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db),
):
    """Resolve a security alert (admin only)."""
    resolved = await anomaly_detector.resolve_alert(db, alert_id)
    if not resolved:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "resolved", "alert_id": alert_id}


@security_router.post("/scan/input")
async def scan_input(text: str, user: User = Depends(get_current_user)):
    """Scan text for prompt injection (for testing)."""
    result = guardrails.scan_input(text)
    return {"is_safe": result.is_safe, "violations": result.violations}


@security_router.post("/scan/output")
async def scan_output(text: str, user: User = Depends(get_current_user)):
    """Scan text for PII/sensitive data (for testing)."""
    result = guardrails.scan_output(text, role=user.role)
    return {"is_safe": result.is_safe, "violations": result.violations, "sanitized": result.sanitized_text}
