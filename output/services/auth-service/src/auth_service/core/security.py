"""Token and password handling for auth-service.

Provides HS256 JWT token creation/validation and bcrypt password hashing.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import structlog
from jose import JWTError, jwt

from auth_service.config import settings

logger = structlog.get_logger(__name__)


class PasswordHandler:
    """Bcrypt password hashing and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password with bcrypt."""
        salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a bcrypt hash."""
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except Exception:
            return False


class TokenHandler:
    """HS256 JWT token creation and validation."""

    @staticmethod
    def create_access_token(
        user_id: str,
        username: str,
        email: str,
        tenant_id: str,
        roles: list[str] | None = None,
        extra_claims: dict | None = None,
    ) -> str:
        """Create an access token (short-lived)."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "username": username,
            "email": email,
            "tenant_id": tenant_id,
            "roles": roles or [],
            "type": "access",
            "iat": now,
            "exp": expire,
        }
        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def create_refresh_token(user_id: str, tenant_id: str) -> str:
        """Create a refresh token (long-lived)."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=settings.jwt_refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "type": "refresh",
            "iat": now,
            "exp": expire,
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and validate a JWT token. Returns claims or None."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return payload
        except JWTError as e:
            logger.debug("token_decode_failed", error=str(e))
            return None

    @staticmethod
    def hash_token(token: str) -> str:
        """SHA256 hash a token for storage (never store raw tokens)."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
