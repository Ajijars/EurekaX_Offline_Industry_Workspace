"""
Anomaly Detector — track and flag unusual query patterns.

Features:
    - Per-user rate limiting (queries per minute)
    - Bulk data extraction detection
    - Unusual access pattern flagging
    - Alert generation stored in DB
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Base

logger = logging.getLogger(__name__)


# ── Alert DB Model ──

class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), nullable=True)
    alert_type = Column(String(50), nullable=False)   # rate_limit, bulk_extract, unusual_access
    severity = Column(String(20), nullable=False)       # low, medium, high, critical
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


@dataclass
class RateLimitState:
    timestamps: list[float] = field(default_factory=list)
    query_count_1h: int = 0


class AnomalyDetector:
    """Detect and alert on unusual query patterns."""

    # Configurable thresholds
    MAX_QUERIES_PER_MINUTE = 30
    MAX_QUERIES_PER_HOUR = 500
    BULK_ROW_THRESHOLD = 10000

    def __init__(self):
        self._rate_limits: dict[str, RateLimitState] = defaultdict(RateLimitState)

    def check_rate_limit(self, user_id: str) -> tuple[bool, Optional[str]]:
        """Check if user exceeds query rate limits. Returns (allowed, reason)."""
        now = time.time()
        state = self._rate_limits[user_id]

        # Clean old timestamps (keep last 60 seconds)
        state.timestamps = [t for t in state.timestamps if now - t < 60]
        state.timestamps.append(now)

        if len(state.timestamps) > self.MAX_QUERIES_PER_MINUTE:
            reason = f"Rate limit exceeded: {len(state.timestamps)} queries in 60s (max {self.MAX_QUERIES_PER_MINUTE})"
            logger.warning("[Anomaly] %s | user=%s", reason, user_id)
            return False, reason

        return True, None

    def check_bulk_extraction(self, row_count: int, user_id: str) -> Optional[str]:
        """Flag queries returning unusually large result sets."""
        if row_count > self.BULK_ROW_THRESHOLD:
            msg = f"Bulk extraction: {row_count} rows retrieved (threshold: {self.BULK_ROW_THRESHOLD})"
            logger.warning("[Anomaly] %s | user=%s", msg, user_id)
            return msg
        return None

    async def create_alert(
        self, db: AsyncSession, *,
        user_id: Optional[str], alert_type: str,
        severity: str, message: str, details: str = "",
    ) -> dict:
        """Create a security alert in the database."""
        alert = SecurityAlert(
            user_id=user_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        return self._alert_to_dict(alert)

    async def get_alerts(
        self, db: AsyncSession, *, resolved: Optional[bool] = None, limit: int = 50,
    ) -> list[dict]:
        """Fetch security alerts."""
        query = select(SecurityAlert).order_by(desc(SecurityAlert.created_at)).limit(limit)
        if resolved is not None:
            query = query.where(SecurityAlert.resolved == resolved)
        result = await db.execute(query)
        return [self._alert_to_dict(a) for a in result.scalars().all()]

    async def resolve_alert(self, db: AsyncSession, alert_id: int) -> bool:
        result = await db.execute(select(SecurityAlert).where(SecurityAlert.id == alert_id))
        alert = result.scalar_one_or_none()
        if not alert:
            return False
        alert.resolved = True
        await db.commit()
        return True

    @staticmethod
    def _alert_to_dict(alert: SecurityAlert) -> dict:
        return {
            "id": alert.id,
            "user_id": alert.user_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "details": alert.details or "",
            "resolved": alert.resolved,
            "created_at": alert.created_at.isoformat() if alert.created_at else "",
        }


anomaly_detector = AnomalyDetector()
