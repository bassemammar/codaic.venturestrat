"""Keycloak client for tenant organization management.

This module provides a client for managing Keycloak organizations
associated with tenants, including creation and deletion operations.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Optional

import aiohttp
import structlog

from registry.config import settings

logger = structlog.get_logger(__name__)


class KeycloakClientError(Exception):
    """Base exception for Keycloak client errors."""

    pass


class KeycloakAuthenticationError(KeycloakClientError):
    """Raised when authentication with Keycloak fails."""

    pass


class KeycloakOrganizationError(KeycloakClientError):
    """Raised when organization operations fail."""

    pass


class KeycloakClient:
    """Async Keycloak client for organization management.

    This client handles:
    - Authentication with admin credentials
    - Creating organizations for new tenants
    - Deleting organizations during tenant purge
    - Token refresh and retry logic
    """

    def __init__(
        self,
        base_url: str = settings.keycloak_base_url,
        admin_username: str = settings.keycloak_admin_username,
        admin_password: str = settings.keycloak_admin_password,
        realm: str = settings.keycloak_realm,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize Keycloak client.

        Args:
            base_url: Keycloak server base URL
            admin_username: Admin username for authentication
            admin_password: Admin password for authentication
            realm: Keycloak realm to operate in
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.realm = realm
        self.timeout = timeout
        self.max_retries = max_retries

        self._session: aiohttp.ClientSession | None = None
        self._access_token: str | None = None
        self._token_expires_at: float | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Start the client and create HTTP session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        logger.info("keycloak_client_started", base_url=self.base_url, realm=self.realm)

    async def close(self) -> None:
        """Close the client and cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None
        self._access_token = None
        self._token_expires_at = None
        logger.info("keycloak_client_closed")

    async def _authenticate(self) -> str:
        """Authenticate with Keycloak and get access token.

        Returns:
            Access token string

        Raises:
            KeycloakAuthenticationError: If authentication fails
        """
        if not self._session:
            raise KeycloakClientError("Client not started. Call start() first.")

        url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        data = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": self.admin_username,
            "password": self.admin_password,
        }

        try:
            async with self._session.post(url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    access_token = token_data["access_token"]
                    expires_in = token_data.get("expires_in", 3600)

                    # Cache token with some buffer time
                    import time

                    self._access_token = access_token
                    self._token_expires_at = time.time() + expires_in - 60  # 1 min buffer

                    logger.info("keycloak_authentication_successful")
                    return access_token
                else:
                    error_text = await response.text()
                    raise KeycloakAuthenticationError(
                        f"Authentication failed: {response.status} - {error_text}"
                    )

        except aiohttp.ClientError as e:
            raise KeycloakAuthenticationError(f"Network error during authentication: {e}")

    async def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers with valid token.

        Returns:
            Dictionary with Authorization header
        """
        import time

        # Check if we need to authenticate or refresh token
        if (
            self._access_token is None
            or self._token_expires_at is None
            or time.time() >= self._token_expires_at
        ):
            await self._authenticate()

        return {"Authorization": f"Bearer {self._access_token}"}

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            url: Request URL
            **kwargs: Additional request arguments

        Returns:
            HTTP response

        Raises:
            KeycloakClientError: If all retries fail
        """
        if not self._session:
            raise KeycloakClientError("Client not started. Call start() first.")

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Get fresh auth headers for each attempt
                headers = await self._get_auth_headers()
                if "headers" in kwargs:
                    kwargs["headers"].update(headers)
                else:
                    kwargs["headers"] = headers

                async with self._session.request(method, url, **kwargs) as response:
                    # Don't retry on client errors (4xx) except 401
                    if 400 <= response.status < 500 and response.status != 401:
                        return response

                    # Retry on server errors (5xx) and 401 (token might be expired)
                    if response.status >= 500 or response.status == 401:
                        if attempt < self.max_retries:
                            # Clear token on 401 to force re-authentication
                            if response.status == 401:
                                self._access_token = None
                                self._token_expires_at = None

                            wait_time = min(2**attempt, 30)  # Exponential backoff, max 30s
                            logger.warning(
                                "keycloak_request_retry",
                                attempt=attempt + 1,
                                status=response.status,
                                wait_time=wait_time,
                            )
                            await asyncio.sleep(wait_time)
                            continue

                    return response

            except aiohttp.ClientError as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = min(2**attempt, 30)
                    logger.warning(
                        "keycloak_request_network_retry",
                        attempt=attempt + 1,
                        error=str(e),
                        wait_time=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue

        # If we get here, all retries failed
        if last_exception:
            raise KeycloakClientError(
                f"Request failed after {self.max_retries} retries: {last_exception}"
            )
        else:
            raise KeycloakClientError(f"Request failed after {self.max_retries} retries")

    async def create_organization(self, slug: str, name: str) -> str:
        """Create a Keycloak organization for a tenant.

        Args:
            slug: Tenant slug (used as organization identifier)
            name: Tenant display name

        Returns:
            Organization ID string

        Raises:
            KeycloakOrganizationError: If organization creation fails
        """
        url = f"{self.base_url}/admin/realms/{self.realm}/organizations"

        org_data = {
            "name": slug,
            "displayName": name,
            "description": f"Organization for tenant {name} ({slug})",
            "enabled": True,
            "attributes": {
                "tenant_slug": [slug],
                "tenant_name": [name],
            },
        }

        try:
            response = await self._request_with_retry(
                "POST", url, json=org_data, headers={"Content-Type": "application/json"}
            )

            if response.status == 201:
                # Extract organization ID from Location header
                location = response.headers.get("Location", "")
                if location:
                    org_id = location.split("/")[-1]
                    logger.info(
                        "keycloak_organization_created", org_id=org_id, slug=slug, name=name
                    )
                    return org_id
                else:
                    # Fallback: try to get org data from response
                    org_data = await response.json()
                    org_id = org_data.get("id", f"org-{slug}")
                    logger.info(
                        "keycloak_organization_created_fallback",
                        org_id=org_id,
                        slug=slug,
                        name=name,
                    )
                    return org_id
            else:
                error_text = await response.text()
                raise KeycloakOrganizationError(
                    f"Failed to create organization: {response.status} - {error_text}"
                )

        except aiohttp.ClientError as e:
            raise KeycloakOrganizationError(f"Network error creating organization: {e}")

    async def delete_organization(self, org_id: str) -> bool:
        """Delete a Keycloak organization.

        Args:
            org_id: Organization ID to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            KeycloakOrganizationError: If deletion fails for reasons other than not found
        """
        url = f"{self.base_url}/admin/realms/{self.realm}/organizations/{org_id}"

        try:
            response = await self._request_with_retry("DELETE", url)

            if response.status == 204:
                logger.info("keycloak_organization_deleted", org_id=org_id)
                return True
            elif response.status == 404:
                logger.info("keycloak_organization_not_found", org_id=org_id)
                return False
            else:
                error_text = await response.text()
                raise KeycloakOrganizationError(
                    f"Failed to delete organization {org_id}: {response.status} - {error_text}"
                )

        except aiohttp.ClientError as e:
            raise KeycloakOrganizationError(f"Network error deleting organization {org_id}: {e}")

    async def invite_user_to_organization(
        self,
        org_id: str,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        roles: list[str] | None = None,
    ) -> str:
        """Invite a user to a Keycloak organization.

        Args:
            org_id: Organization ID
            email: User email address
            first_name: User first name (optional)
            last_name: User last name (optional)
            roles: List of roles to assign (defaults to ['admin'])

        Returns:
            User ID string

        Raises:
            KeycloakClientError: If user invitation fails
        """
        if not roles:
            roles = ["admin"]

        # Step 1: Create user
        user_data = {
            "username": email,
            "email": email,
            "emailVerified": False,
            "enabled": True,
            "firstName": first_name or email.split("@")[0],
            "lastName": last_name or "",
            "requiredActions": ["VERIFY_EMAIL", "UPDATE_PASSWORD"],
            "attributes": {
                "tenant_admin": ["true"],
                "invited_at": [datetime.now(UTC).isoformat()],
            },
        }

        try:
            # Create user
            user_url = f"{self.base_url}/admin/realms/{self.realm}/users"
            response = await self._request_with_retry(
                "POST", user_url, json=user_data, headers={"Content-Type": "application/json"}
            )

            if response.status == 201:
                # Extract user ID from Location header
                location = response.headers.get("Location", "")
                if location:
                    user_id = location.split("/")[-1]
                else:
                    # Fallback: search for user by email
                    search_url = f"{user_url}?email={email}&exact=true"
                    search_response = await self._request_with_retry("GET", search_url)
                    if search_response.status == 200:
                        users = await search_response.json()
                        if users:
                            user_id = users[0]["id"]
                        else:
                            raise KeycloakClientError("User created but not found in search")
                    else:
                        raise KeycloakClientError("User created but unable to retrieve ID")

                logger.info("keycloak_user_created", user_id=user_id, email=email, org_id=org_id)

                # Step 2: Add user to organization
                org_membership_url = (
                    f"{self.base_url}/admin/realms/{self.realm}/organizations/{org_id}/members"
                )
                membership_response = await self._request_with_retry(
                    "POST",
                    org_membership_url,
                    json={"userId": user_id},
                    headers={"Content-Type": "application/json"},
                )

                if membership_response.status in [201, 204]:
                    logger.info(
                        "keycloak_user_added_to_organization",
                        user_id=user_id,
                        email=email,
                        org_id=org_id,
                    )
                else:
                    error_text = await membership_response.text()
                    logger.warning(
                        "keycloak_user_organization_membership_failed",
                        user_id=user_id,
                        email=email,
                        org_id=org_id,
                        error=error_text,
                    )

                # Step 3: Send verification email (execute actions)
                actions_url = f"{user_url}/{user_id}/execute-actions-email"
                actions_data = ["VERIFY_EMAIL"]  # This will send verification email

                actions_response = await self._request_with_retry(
                    "PUT",
                    actions_url,
                    json=actions_data,
                    headers={"Content-Type": "application/json"},
                )

                if actions_response.status in [200, 204]:
                    logger.info(
                        "keycloak_user_invitation_email_sent",
                        user_id=user_id,
                        email=email,
                        org_id=org_id,
                    )
                else:
                    error_text = await actions_response.text()
                    logger.warning(
                        "keycloak_user_invitation_email_failed",
                        user_id=user_id,
                        email=email,
                        org_id=org_id,
                        error=error_text,
                    )

                return user_id

            elif response.status == 409:
                # User already exists - try to find and add to organization
                search_url = f"{user_url}?email={email}&exact=true"
                search_response = await self._request_with_retry("GET", search_url)
                if search_response.status == 200:
                    users = await search_response.json()
                    if users:
                        user_id = users[0]["id"]
                        logger.info("keycloak_user_already_exists", user_id=user_id, email=email)

                        # Try to add to organization
                        org_membership_url = f"{self.base_url}/admin/realms/{self.realm}/organizations/{org_id}/members"
                        membership_response = await self._request_with_retry(
                            "POST",
                            org_membership_url,
                            json={"userId": user_id},
                            headers={"Content-Type": "application/json"},
                        )

                        if membership_response.status in [201, 204, 409]:  # 409 = already member
                            return user_id

                raise KeycloakClientError(
                    f"User {email} exists but could not be added to organization"
                )
            else:
                error_text = await response.text()
                raise KeycloakClientError(
                    f"Failed to create user: {response.status} - {error_text}"
                )

        except aiohttp.ClientError as e:
            raise KeycloakClientError(f"Network error inviting user: {e}")

    async def health_check(self) -> bool:
        """Check if Keycloak is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/health"

            # Use a simple GET request without authentication for health check
            if not self._session:
                return False

            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200

        except Exception as e:
            logger.warning("keycloak_health_check_failed", error=str(e))
            return False


# Global instance for dependency injection
keycloak_client = KeycloakClient()


async def get_keycloak_client() -> KeycloakClient:
    """Dependency function to get Keycloak client.

    Returns:
        Configured Keycloak client instance
    """
    return keycloak_client
