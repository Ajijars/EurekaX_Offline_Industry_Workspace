"""
Authentication API Router.

Endpoints:
    POST /api/auth/register   – create an account (first user is auto-admin)
    POST /api/auth/login      – returns JWT access + refresh tokens
    POST /api/auth/refresh    – rotate refresh token
    GET  /api/auth/me         – current user profile
    PUT  /api/auth/me         – update profile (password, username)

Admin-only:
    GET    /api/auth/users         – list all users
    PUT    /api/auth/users/{id}/role – change a user's role
    DELETE /api/auth/users/{id}    – deactivate a user
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    require_admin,
    get_current_user,
    verify_password,
)
from app.db.database import get_db
from app.db.models import AuditLog, User

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ── Request / Response Schemas ──

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email or username")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool
    created_at: str


class UpdateProfileRequest(BaseModel):
    username: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UpdateRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(admin|employee)$")


# ── Helpers ──

def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else "",
    }


async def _log_audit(
    db: AsyncSession,
    user_id: str | None,
    action: str,
    details: str = "",
) -> None:
    db.add(AuditLog(
        user_id=user_id,
        action=action,
        resource_type="auth",
        details=details,
        timestamp=datetime.now(timezone.utc),
    ))
    await db.commit()


# ═══════════════════════════════════════════════
# Public Endpoints
# ═══════════════════════════════════════════════


@auth_router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new user account.
    The very first user registered is automatically promoted to admin.
    """
    # Check for existing email/username
    existing = await db.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email or username already registered")

    # First user → admin
    count = await db.execute(select(func.count(User.id)))
    is_first = count.scalar() == 0

    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
        role="admin" if is_first else "employee",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("[Auth] Registered %s (role=%s, first=%s)", user.username, user.role, is_first)
    await _log_audit(db, user.id, "register", f"role={user.role}")

    access = create_access_token({"sub": user.id})
    refresh = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=_user_to_dict(user),
    )


@auth_router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email/username and password."""
    result = await db.execute(
        select(User).where(
            (User.email == body.email) | (User.username == body.email)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    logger.info("[Auth] Login: %s", user.username)
    await _log_audit(db, user.id, "login")

    access = create_access_token({"sub": user.id})
    refresh = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=_user_to_dict(user),
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    access = create_access_token({"sub": user.id})
    refresh = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=_user_to_dict(user),
    )


@auth_router.get("/me", response_model=UserProfile)
async def get_me(user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return UserProfile(**_user_to_dict(user))


@auth_router.put("/me", response_model=UserProfile)
async def update_me(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's username or password."""
    if body.username and body.username != user.username:
        existing = await db.execute(select(User).where(User.username == body.username))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Username already taken")
        user.username = body.username

    if body.password:
        user.hashed_password = hash_password(body.password)

    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    return UserProfile(**_user_to_dict(user))


# ═══════════════════════════════════════════════
# Admin-Only Endpoints
# ═══════════════════════════════════════════════


@auth_router.get("/users", response_model=list[UserProfile])
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    return [UserProfile(**_user_to_dict(u)) for u in users]


@auth_router.put("/users/{user_id}/role", response_model=UserProfile)
async def change_user_role(
    user_id: str,
    body: UpdateRoleRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    old_role = target.role
    target.role = body.role
    target.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(target)

    await _log_audit(
        db, admin.id, "change_role",
        f"user={target.username} old={old_role} new={body.role}",
    )
    return UserProfile(**_user_to_dict(target))


@auth_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user account (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    target_username = target.username
    await db.delete(target)
    await db.commit()

    await _log_audit(db, admin.id, "delete_user", f"user={target_username}")
    return {"status": "deleted", "user_id": user_id}
