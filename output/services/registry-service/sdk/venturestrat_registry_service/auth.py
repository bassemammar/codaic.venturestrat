"""Authentication providers for registry-service service.

This module provides various authentication methods for connecting to
the registry-service service.
"""

import base64
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional


class AuthProvider(ABC):
    """Base authentication provider interface."""

    @abstractmethod
    def get_metadata(self) -> dict[str, str]:
        """Get authentication metadata for gRPC requests.

        Returns:
            Dictionary of metadata headers
        """

    @abstractmethod
    def is_expired(self) -> bool:
        """Check if authentication is expired.

        Returns:
            True if expired, False otherwise
        """

    @abstractmethod
    def refresh(self) -> None:
        """Refresh authentication if possible.

        Raises:
            AuthenticationError: If refresh fails
        """


class NoAuthProvider(AuthProvider):
    """No authentication provider (for local development)."""

    def get_metadata(self) -> dict[str, str]:
        """Get empty metadata."""
        return {}

    def is_expired(self) -> bool:
        """Never expires."""
        return False

    def refresh(self) -> None:
        """No-op refresh."""


class ApiKeyAuthProvider(AuthProvider):
    """API key authentication provider.

    Uses X-API-Key header for authentication.
    """

    def __init__(self, api_key: str) -> None:
        """Initialize with API key.

        Args:
            api_key: The API key
        """
        self.api_key = api_key

    def get_metadata(self) -> dict[str, str]:
        """Get API key metadata."""
        return {"x-api-key": self.api_key}

    def is_expired(self) -> bool:
        """API keys don't expire."""
        return False

    def refresh(self) -> None:
        """API keys can't be refreshed."""


class TokenAuthProvider(AuthProvider):
    """Bearer token authentication provider.

    Uses Authorization header with Bearer token.
    """

    def __init__(
        self,
        token: str,
        expires_at: datetime | None = None,
        refresh_threshold: int = 300,  # 5 minutes
    ) -> None:
        """Initialize with token.

        Args:
            token: The bearer token
            expires_at: When the token expires
            refresh_threshold: Seconds before expiry to refresh
        """
        self.token = token
        self.expires_at = expires_at
        self.refresh_threshold = refresh_threshold

    def get_metadata(self) -> dict[str, str]:
        """Get bearer token metadata."""
        return {"authorization": f"Bearer {self.token}"}

    def is_expired(self) -> bool:
        """Check if token is expired or will expire soon."""
        if not self.expires_at:
            return False

        threshold = datetime.utcnow() + timedelta(seconds=self.refresh_threshold)
        return self.expires_at <= threshold

    def refresh(self) -> None:
        """Refresh token (must be implemented by subclass)."""
        msg = "Token refresh not implemented"
        raise NotImplementedError(msg)


class BasicAuthProvider(AuthProvider):
    """Basic authentication provider.

    Uses Authorization header with base64-encoded credentials.
    """

    def __init__(self, username: str, password: str) -> None:
        """Initialize with credentials.

        Args:
            username: Username
            password: Password
        """
        self.username = username
        self.password = password
        self._auth_string = self._encode_credentials()

    def _encode_credentials(self) -> str:
        """Encode credentials for basic auth."""
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def get_metadata(self) -> dict[str, str]:
        """Get basic auth metadata."""
        return {"authorization": self._auth_string}

    def is_expired(self) -> bool:
        """Basic auth doesn't expire."""
        return False

    def refresh(self) -> None:
        """Basic auth can't be refreshed."""


class JWTAuthProvider(TokenAuthProvider):
    """JWT token authentication provider.

    Extends TokenAuthProvider with JWT-specific functionality.
    """

    def __init__(self, jwt_token: str, auto_refresh: bool = False) -> None:
        """Initialize with JWT token.

        Args:
            jwt_token: The JWT token
            auto_refresh: Whether to auto-refresh the token
        """
        expires_at = self._extract_expiry(jwt_token) if jwt_token else None
        super().__init__(jwt_token, expires_at)
        self.auto_refresh = auto_refresh

    def _extract_expiry(self, token: str) -> datetime | None:
        """Extract expiry from JWT token.

        Args:
            token: JWT token

        Returns:
            Expiry datetime if available
        """
        try:
            import json

            # Split JWT token
            parts = token.split(".")
            if len(parts) != 3:
                return None

            # Decode payload (add padding if needed)
            payload = parts[1]
            padding = 4 - (len(payload) % 4)
            if padding != 4:
                payload += "=" * padding

            decoded = base64.b64decode(payload.encode())
            data = json.loads(decoded)

            # Extract expiry
            exp = data.get("exp")
            if exp:
                return datetime.utcfromtimestamp(exp)

        except Exception:
            # If we can't decode, assume no expiry
            pass

        return None

    def refresh(self) -> None:
        """Refresh JWT token.

        This is a placeholder - actual implementation would depend on
        your authentication service.
        """
        if not self.auto_refresh:
            msg = "JWT refresh not configured"
            raise NotImplementedError(msg)

        # TODO: Implement JWT refresh by calling /auth/refresh with refresh_token
        # Should handle token validation and store the new access_token
        msg = "JWT refresh not implemented"
        raise NotImplementedError(msg)


__all__ = [
    "ApiKeyAuthProvider",
    "AuthProvider",
    "BasicAuthProvider",
    "JWTAuthProvider",
    "NoAuthProvider",
    "TokenAuthProvider",
]
