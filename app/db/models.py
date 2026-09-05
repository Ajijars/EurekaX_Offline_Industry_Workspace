"""
ORM Models — Users, Permissions, Audit Logs.

Role hierarchy:
    admin    → full access (manage users, data sources, security policies)
    employee → scoped access (query permitted datasets, use approved models)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


# ── Helpers ──

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


# ── User ──

class User(Base):
    __tablename__ = "users"

    id = Column(String(32), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        Enum("admin", "employee", name="user_role"),
        nullable=False,
        default="employee",
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    permissions = relationship("Permission", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.username} role={self.role}>"


# ── Permission ──

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resource_type = Column(String(50), nullable=False)   # "datasource", "model", "notebook", etc.
    resource_id = Column(String(255), nullable=False)     # specific resource identifier
    access_level = Column(
        Enum("read", "write", "admin", name="access_level"),
        nullable=False,
        default="read",
    )
    granted_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    granted_by = Column(String(32), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "resource_type", "resource_id", name="uq_user_resource"),
    )

    # Relationships
    user = relationship("User", back_populates="permissions")


# ── Audit Log ──

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True)  # "login", "query", "upload", etc.
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)      # JSON string for extra context
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
