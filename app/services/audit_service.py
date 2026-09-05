"""
Audit Service — centralized compliance logging for all data operations.

Every significant action (login, query, upload, permission change, etc.)
is recorded with user context, timestamp, and details.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Write and query audit trail entries."""

    async def log(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[str] = None,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Record a single audit event."""
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(entry)
        await db.commit()
        logger.debug("[Audit] %s | user=%s | %s/%s", action, user_id, resource_type, resource_id)

    async def get_trail(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """Query audit logs with optional filters and pagination."""
        query = select(AuditLog).order_by(desc(AuditLog.timestamp))

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)

        # Count total
        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        # Fetch page
        result = await db.execute(query.offset(offset).limit(limit))
        logs = result.scalars().all()

        return {
            "logs": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "details": json.loads(log.details) if log.details else None,
                    "ip_address": log.ip_address,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else "",
                }
                for log in logs
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_actions_summary(self, db: AsyncSession) -> list[dict]:
        """Get count of each action type for dashboard charts."""
        query = (
            select(AuditLog.action, func.count(AuditLog.id).label("count"))
            .group_by(AuditLog.action)
            .order_by(desc("count"))
        )
        result = await db.execute(query)
        return [{"action": row.action, "count": row.count} for row in result.all()]


audit_service = AuditService()
