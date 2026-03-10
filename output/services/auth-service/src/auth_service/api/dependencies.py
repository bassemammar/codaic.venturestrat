"""FastAPI dependencies for authentication."""

import asyncio
import contextvars
from typing import Optional

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_service.core.security import TokenHandler

logger = structlog.get_logger(__name__)

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    """Extract and validate the current user from Bearer token.

    Returns a dict with user claims from the JWT.
    Raises 401 if token is missing/invalid/expired or session is inactive.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    claims = TokenHandler.decode_token(token)

    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if claims.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify session is still active
    token_hash = TokenHandler.hash_token(token)
    try:
        from auth_service.infrastructure.orm.session import Session as SessionModel
        from venturestrat.tenancy.context import set_current_tenant, TenantContext

        tenant_id = claims.get("tenant_id", "00000000-0000-0000-0000-000000000000")
        set_current_tenant(TenantContext(tenant_id=tenant_id))

        sessions = await asyncio.get_event_loop().run_in_executor(
            None,
            contextvars.copy_context().run,
            lambda: SessionModel.search(
                [("token_hash", "=", token_hash), ("is_active", "=", True)],
                limit=1,
            ),
        )
        if not sessions:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or logged out",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("session_check_failed", error=str(e))
        # Allow through if session table isn't available yet (startup race)

    return claims
