"""Authentication endpoints: login, logout, refresh, validate, me, change-password."""

import asyncio
import contextvars
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from auth_service.config import settings
from auth_service.core.security import PasswordHandler, TokenHandler
from auth_service.api.auth_schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
    UserInfoResponse,
    ValidateRequest,
    ValidateResponse,
)
from auth_service.api.dependencies import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter()


def _run_sync(fn):
    """Run a synchronous BaseModel ORM call in an executor with context."""
    return asyncio.get_event_loop().run_in_executor(
        None, contextvars.copy_context().run, fn
    )


def _update_record(schema, table, record_id, updates):
    """Direct SQL UPDATE for a record. Bypasses BaseModel write limitations."""
    from sqlalchemy import text
    from venturestrat.models.registry import ModelRegistry

    engine = ModelRegistry.get_engine()
    set_clauses = ", ".join(f"{k} = :{k}" for k in updates.keys())
    sql = text(f"UPDATE {schema}.{table} SET {set_clauses} WHERE id = :_id")
    params = {**updates, "_id": record_id}
    # Convert datetime objects to strings for SQL
    for k, v in params.items():
        if isinstance(v, datetime):
            params[k] = v.isoformat()
    with engine.connect() as conn:
        conn.execute(sql, params)
        conn.commit()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    """Authenticate user and return JWT tokens."""
    from auth_service.infrastructure.orm.user import User
    from auth_service.infrastructure.orm.session import Session as SessionModel
    from auth_service.infrastructure.orm.user_role import UserRole
    from auth_service.infrastructure.orm.role import Role
    from venturestrat.tenancy.context import set_current_tenant, TenantContext

    tenant_id = body.tenant_id
    set_current_tenant(TenantContext(tenant_id=tenant_id))

    # Find user by username
    users = await _run_sync(
        lambda: User.search(
            [("username", "=", body.username), ("tenant_id", "=", tenant_id)],
            limit=1,
        )
    )

    if not users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    user = users[0]

    # Check account lockout
    locked_until = user.locked_until
    if locked_until:
        if isinstance(locked_until, str):
            locked_until = datetime.fromisoformat(locked_until)
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is locked. Try again later.",
            )

    # Check active
    is_active = user.is_active
    if isinstance(is_active, str):
        is_active = is_active.lower() in ("true", "1", "t")
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Verify password
    if not PasswordHandler.verify_password(body.password, user.hashed_password):
        new_count = (user.failed_login_count or 0) + 1
        updates = {"failed_login_count": new_count}
        if new_count >= settings.max_failed_logins:
            updates["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=settings.lockout_duration_minutes)
        try:
            await _run_sync(lambda: _update_record("auth", "aut_user", user.id, updates))
        except Exception as e:
            logger.warning("failed_login_update_error", error=str(e))

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Successful login — reset failed count, update last_login
    try:
        await _run_sync(lambda: _update_record("auth", "aut_user", user.id, {
            "failed_login_count": 0,
            "last_login": datetime.now(timezone.utc),
        }))
    except Exception as e:
        logger.warning("login_update_error", error=str(e))

    # Get user roles
    role_codes = []
    try:
        user_roles = await _run_sync(
            lambda: UserRole.search(
                [("user_id", "=", str(user.id)), ("tenant_id", "=", tenant_id)]
            )
        )
        for ur in user_roles:
            roles = await _run_sync(lambda rid=ur.role_id: Role.search([("id", "=", rid)], limit=1))
            if roles:
                role_codes.append(roles[0].code)
    except Exception as e:
        logger.warning("role_fetch_error", error=str(e))

    # Create tokens
    user_id = str(user.id)
    access_token = TokenHandler.create_access_token(
        user_id=user_id,
        username=user.username,
        email=user.email,
        tenant_id=tenant_id,
        roles=role_codes,
    )
    refresh_token = TokenHandler.create_refresh_token(
        user_id=user_id,
        tenant_id=tenant_id,
    )

    # Create session record
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500]
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)

        session = SessionModel()
        session.user_id = user_id
        session.token_hash = TokenHandler.hash_token(access_token)
        session.refresh_token_hash = TokenHandler.hash_token(refresh_token)
        session.ip_address = ip_address
        session.user_agent = user_agent
        session.is_active = True
        session.expires_at = expires_at
        session.tenant_id = tenant_id
        await _run_sync(lambda: session.save())
    except Exception as e:
        logger.error("session_create_error", error=str(e), error_type=type(e).__name__)

    logger.info("user_logged_in", user_id=user_id, username=user.username)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_me(claims: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    from auth_service.infrastructure.orm.user import User
    from auth_service.infrastructure.orm.user_role import UserRole
    from auth_service.infrastructure.orm.role import Role
    from venturestrat.tenancy.context import set_current_tenant, TenantContext

    tenant_id = claims.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    set_current_tenant(TenantContext(tenant_id=tenant_id))

    users = await _run_sync(
        lambda: User.search([("id", "=", claims["sub"])], limit=1)
    )
    if not users:
        raise HTTPException(status_code=404, detail="User not found")

    user = users[0]

    # Fetch roles
    role_codes = []
    try:
        user_roles = await _run_sync(
            lambda: UserRole.search([("user_id", "=", str(user.id)), ("tenant_id", "=", tenant_id)])
        )
        for ur in user_roles:
            roles = await _run_sync(lambda rid=ur.role_id: Role.search([("id", "=", rid)], limit=1))
            if roles:
                role_codes.append(roles[0].code)
    except Exception:
        pass

    is_active = user.is_active
    if isinstance(is_active, str):
        is_active = is_active.lower() in ("true", "1", "t")

    return UserInfoResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=is_active,
        tenant_id=tenant_id,
        roles=role_codes,
        last_login=user.last_login,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, request: Request):
    """Refresh an access token using a valid refresh token."""
    from auth_service.infrastructure.orm.session import Session as SessionModel
    from auth_service.infrastructure.orm.user import User
    from auth_service.infrastructure.orm.user_role import UserRole
    from auth_service.infrastructure.orm.role import Role
    from venturestrat.tenancy.context import set_current_tenant, TenantContext

    claims = TokenHandler.decode_token(body.refresh_token)
    if claims is None or claims.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = claims["sub"]
    tenant_id = claims.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    set_current_tenant(TenantContext(tenant_id=tenant_id))

    # Verify refresh token session exists
    refresh_hash = TokenHandler.hash_token(body.refresh_token)
    sessions = await _run_sync(
        lambda: SessionModel.search(
            [("refresh_token_hash", "=", refresh_hash), ("is_active", "=", True)],
            limit=1,
        )
    )
    if not sessions:
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    old_session = sessions[0]

    # Deactivate old session via direct SQL
    try:
        await _run_sync(lambda: _update_record("auth", "aut_session", old_session.id, {"is_active": False}))
    except Exception as e:
        logger.warning("session_deactivate_error", error=str(e))

    # Get user
    users = await _run_sync(lambda: User.search([("id", "=", user_id)], limit=1))
    if not users:
        raise HTTPException(status_code=401, detail="User not found")
    user = users[0]

    # Get roles
    role_codes = []
    try:
        user_roles = await _run_sync(
            lambda: UserRole.search([("user_id", "=", user_id), ("tenant_id", "=", tenant_id)])
        )
        for ur in user_roles:
            roles = await _run_sync(lambda rid=ur.role_id: Role.search([("id", "=", rid)], limit=1))
            if roles:
                role_codes.append(roles[0].code)
    except Exception:
        pass

    # Issue new tokens
    access_token = TokenHandler.create_access_token(
        user_id=user_id,
        username=user.username,
        email=user.email,
        tenant_id=tenant_id,
        roles=role_codes,
    )
    refresh_token = TokenHandler.create_refresh_token(user_id=user_id, tenant_id=tenant_id)

    # Create new session
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500]
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)

        new_session = SessionModel()
        new_session.user_id = user_id
        new_session.token_hash = TokenHandler.hash_token(access_token)
        new_session.refresh_token_hash = TokenHandler.hash_token(refresh_token)
        new_session.ip_address = ip_address
        new_session.user_agent = user_agent
        new_session.is_active = True
        new_session.expires_at = expires_at
        new_session.tenant_id = tenant_id
        await _run_sync(lambda: new_session.save())
    except Exception as e:
        logger.error("session_create_error", error=str(e), error_type=type(e).__name__)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate_token(body: ValidateRequest):
    """Validate a token and return its claims. Used by other services."""
    claims = TokenHandler.decode_token(body.token)
    if claims is None:
        return ValidateResponse(valid=False)

    return ValidateResponse(
        valid=True,
        user_id=claims.get("sub"),
        username=claims.get("username"),
        tenant_id=claims.get("tenant_id"),
        roles=claims.get("roles", []),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(claims: dict = Depends(get_current_user), request: Request = None):
    """Logout current user by deactivating all active sessions."""
    from auth_service.infrastructure.orm.session import Session as SessionModel
    from venturestrat.tenancy.context import set_current_tenant, TenantContext

    user_id = claims["sub"]
    tenant_id = claims.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    set_current_tenant(TenantContext(tenant_id=tenant_id))

    try:
        sessions = await _run_sync(
            lambda: SessionModel.search(
                [("user_id", "=", user_id), ("is_active", "=", True)]
            )
        )
        for s in sessions:
            await _run_sync(lambda sid=s.id: _update_record("auth", "aut_session", sid, {"is_active": False}))

        logger.info("user_logged_out", user_id=user_id, sessions_deactivated=len(sessions))
    except Exception as e:
        logger.error("logout_error", error=str(e), error_type=type(e).__name__)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    claims: dict = Depends(get_current_user),
):
    """Change the current user's password."""
    from auth_service.infrastructure.orm.user import User
    from venturestrat.tenancy.context import set_current_tenant, TenantContext

    tenant_id = claims.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    set_current_tenant(TenantContext(tenant_id=tenant_id))

    users = await _run_sync(
        lambda: User.search([("id", "=", claims["sub"])], limit=1)
    )
    if not users:
        raise HTTPException(status_code=404, detail="User not found")

    user = users[0]

    if not PasswordHandler.verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_hash = PasswordHandler.hash_password(body.new_password)
    await _run_sync(lambda: _update_record("auth", "aut_user", user.id, {"hashed_password": new_hash}))

    logger.info("password_changed", user_id=claims["sub"])
    return MessageResponse(message="Password changed successfully")
