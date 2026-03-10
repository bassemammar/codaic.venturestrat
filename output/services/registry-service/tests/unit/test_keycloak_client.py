"""Tests for Keycloak client functionality.

This module tests the KeycloakClient for organization management during tenant purge.
"""

from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from registry.keycloak_client import (
    KeycloakAuthenticationError,
    KeycloakClient,
    KeycloakClientError,
    KeycloakOrganizationError,
)


class TestKeycloakClientInitialization:
    """Tests for KeycloakClient initialization."""

    def test_client_initialization_defaults(self):
        """KeycloakClient initializes with default settings."""
        client = KeycloakClient()

        assert "localhost:8080" in client.base_url
        assert client.admin_username == "admin"
        assert client.admin_password == "admin"
        assert client.realm == "master"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client._session is None
        assert client._access_token is None

    def test_client_initialization_custom(self):
        """KeycloakClient initializes with custom settings."""
        client = KeycloakClient(
            base_url="https://keycloak.example.com",
            admin_username="custom-admin",
            admin_password="custom-password",
            realm="custom-realm",
            timeout=60,
            max_retries=5,
        )

        assert client.base_url == "https://keycloak.example.com"
        assert client.admin_username == "custom-admin"
        assert client.admin_password == "custom-password"
        assert client.realm == "custom-realm"
        assert client.timeout == 60
        assert client.max_retries == 5


class TestKeycloakClientLifecycle:
    """Tests for client lifecycle management."""

    @pytest.mark.asyncio
    async def test_start_creates_session(self):
        """start() creates HTTP session."""
        client = KeycloakClient()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            await client.start()

            mock_session_class.assert_called_once()
            assert client._session == mock_session

    @pytest.mark.asyncio
    async def test_close_cleanup_session(self):
        """close() cleans up HTTP session."""
        client = KeycloakClient()
        mock_session = AsyncMock()
        client._session = mock_session
        client._access_token = "test-token"

        await client.close()

        mock_session.close.assert_called_once()
        assert client._session is None
        assert client._access_token is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """KeycloakClient works as async context manager."""
        client = KeycloakClient()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with client as ctx_client:
                assert ctx_client == client
                assert client._session == mock_session

            mock_session.close.assert_called_once()


class TestKeycloakClientAuthentication:
    """Tests for authentication functionality."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """_authenticate() successfully gets access token."""
        client = KeycloakClient()
        mock_session = AsyncMock()
        client._session = mock_session

        # Mock successful auth response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"access_token": "test-access-token", "expires_in": 3600}

        mock_session.post.return_value.__aenter__.return_value = mock_response

        token = await client._authenticate()

        assert token == "test-access-token"
        assert client._access_token == "test-access-token"
        assert client._token_expires_at is not None

    @pytest.mark.asyncio
    async def test_authenticate_failure(self):
        """_authenticate() raises on auth failure."""
        client = KeycloakClient()
        mock_session = AsyncMock()
        client._session = mock_session

        # Mock failed auth response
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text.return_value = "Invalid credentials"

        mock_session.post.return_value.__aenter__.return_value = mock_response

        with pytest.raises(KeycloakAuthenticationError, match="Authentication failed"):
            await client._authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_network_error(self):
        """_authenticate() handles network errors."""
        client = KeycloakClient()
        mock_session = AsyncMock()
        client._session = mock_session

        mock_session.post.side_effect = aiohttp.ClientError("Network error")

        with pytest.raises(KeycloakAuthenticationError, match="Network error"):
            await client._authenticate()

    @pytest.mark.asyncio
    async def test_get_auth_headers_cached_token(self):
        """_get_auth_headers() uses cached token when valid."""
        client = KeycloakClient()

        # Mock valid cached token
        import time

        client._access_token = "cached-token"
        client._token_expires_at = time.time() + 1800  # 30 minutes from now

        headers = await client._get_auth_headers()

        assert headers == {"Authorization": "Bearer cached-token"}

    @pytest.mark.asyncio
    async def test_get_auth_headers_expired_token(self):
        """_get_auth_headers() refreshes expired token."""
        client = KeycloakClient()
        mock_session = AsyncMock()
        client._session = mock_session

        # Mock expired token
        import time

        client._access_token = "expired-token"
        client._token_expires_at = time.time() - 100  # Expired

        # Mock fresh token response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"access_token": "fresh-token", "expires_in": 3600}
        mock_session.post.return_value.__aenter__.return_value = mock_response

        headers = await client._get_auth_headers()

        assert headers == {"Authorization": "Bearer fresh-token"}
        assert client._access_token == "fresh-token"


class TestKeycloakClientRequestRetry:
    """Tests for request retry logic."""

    @pytest.mark.asyncio
    async def test_request_with_retry_success(self):
        """_request_with_retry() succeeds on first attempt."""
        client = KeycloakClient()
        mock_session = AsyncMock()
        client._session = mock_session

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200

        # Mock auth headers
        with patch.object(
            client, "_get_auth_headers", return_value={"Authorization": "Bearer token"}
        ):
            mock_session.request.return_value.__aenter__.return_value = mock_response

            response = await client._request_with_retry("GET", "https://example.com")

            assert response == mock_response
            mock_session.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_with_retry_server_error_retries(self):
        """_request_with_retry() retries on server errors."""
        client = KeycloakClient(max_retries=2)
        mock_session = AsyncMock()
        client._session = mock_session

        # Mock server error then success
        mock_error_response = AsyncMock()
        mock_error_response.status = 500

        mock_success_response = AsyncMock()
        mock_success_response.status = 200

        responses = [mock_error_response, mock_success_response]
        mock_session.request.return_value.__aenter__.side_effect = responses

        with patch.object(
            client, "_get_auth_headers", return_value={"Authorization": "Bearer token"}
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):  # Fast retry
                response = await client._request_with_retry("GET", "https://example.com")

                assert response == mock_success_response
                assert mock_session.request.call_count == 2

    @pytest.mark.asyncio
    async def test_request_with_retry_401_clears_token(self):
        """_request_with_retry() clears token on 401 and retries."""
        client = KeycloakClient(max_retries=2)
        mock_session = AsyncMock()
        client._session = mock_session

        # Set initial token
        client._access_token = "old-token"
        client._token_expires_at = 999999999999  # Far future

        # Mock 401 then success
        mock_401_response = AsyncMock()
        mock_401_response.status = 401

        mock_success_response = AsyncMock()
        mock_success_response.status = 200

        responses = [mock_401_response, mock_success_response]
        mock_session.request.return_value.__aenter__.side_effect = responses

        auth_headers_calls = [
            {"Authorization": "Bearer old-token"},  # First call with old token
            {"Authorization": "Bearer new-token"},  # Second call with new token
        ]

        with patch.object(client, "_get_auth_headers", side_effect=auth_headers_calls):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                response = await client._request_with_retry("GET", "https://example.com")

                assert response == mock_success_response
                assert mock_session.request.call_count == 2

    @pytest.mark.asyncio
    async def test_request_with_retry_exhausted_retries(self):
        """_request_with_retry() raises after exhausting retries."""
        client = KeycloakClient(max_retries=1)
        mock_session = AsyncMock()
        client._session = mock_session

        # Mock persistent server error
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch.object(
            client, "_get_auth_headers", return_value={"Authorization": "Bearer token"}
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                response = await client._request_with_retry("GET", "https://example.com")

                # Should return the error response (not raise)
                assert response == mock_response
                assert mock_session.request.call_count == 2  # Initial + 1 retry

    @pytest.mark.asyncio
    async def test_request_with_retry_network_error_retries(self):
        """_request_with_retry() retries on network errors."""
        client = KeycloakClient(max_retries=2)
        mock_session = AsyncMock()
        client._session = mock_session

        # Network error then success
        mock_session.request.side_effect = [
            aiohttp.ClientError("Network error"),
            mock_session.request.return_value,
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch.object(
            client, "_get_auth_headers", return_value={"Authorization": "Bearer token"}
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(KeycloakClientError, match="Network error"):
                    await client._request_with_retry("GET", "https://example.com")


class TestKeycloakClientOrganizationOperations:
    """Tests for organization management operations."""

    @pytest.mark.asyncio
    async def test_create_organization_success(self):
        """create_organization() successfully creates organization."""
        client = KeycloakClient()

        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.headers = {
            "Location": "https://keycloak.com/admin/realms/master/organizations/org-123"
        }

        with patch.object(client, "_request_with_retry", return_value=mock_response):
            org_id = await client.create_organization("test-slug", "Test Organization")

            assert org_id == "org-123"

    @pytest.mark.asyncio
    async def test_create_organization_fallback_id(self):
        """create_organization() handles missing Location header."""
        client = KeycloakClient()

        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.headers = {}  # No Location header
        mock_response.json.return_value = {"id": "org-456"}

        with patch.object(client, "_request_with_retry", return_value=mock_response):
            org_id = await client.create_organization("test-slug", "Test Organization")

            assert org_id == "org-456"

    @pytest.mark.asyncio
    async def test_create_organization_no_id_fallback(self):
        """create_organization() creates fallback ID when no ID available."""
        client = KeycloakClient()

        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.headers = {}
        mock_response.json.return_value = {}  # No ID in response

        with patch.object(client, "_request_with_retry", return_value=mock_response):
            org_id = await client.create_organization("test-slug", "Test Organization")

            assert org_id == "org-test-slug"

    @pytest.mark.asyncio
    async def test_create_organization_failure(self):
        """create_organization() raises on creation failure."""
        client = KeycloakClient()

        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text.return_value = "Invalid organization data"

        with patch.object(client, "_request_with_retry", return_value=mock_response):
            with pytest.raises(KeycloakOrganizationError, match="Failed to create organization"):
                await client.create_organization("test-slug", "Test Organization")

    @pytest.mark.asyncio
    async def test_delete_organization_success(self):
        """delete_organization() successfully deletes organization."""
        client = KeycloakClient()

        mock_response = AsyncMock()
        mock_response.status = 204

        with patch.object(client, "_request_with_retry", return_value=mock_response):
            result = await client.delete_organization("org-123")

            assert result is True

    @pytest.mark.asyncio
    async def test_delete_organization_not_found(self):
        """delete_organization() handles organization not found."""
        client = KeycloakClient()

        mock_response = AsyncMock()
        mock_response.status = 404

        with patch.object(client, "_request_with_retry", return_value=mock_response):
            result = await client.delete_organization("org-123")

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_organization_failure(self):
        """delete_organization() raises on deletion failure."""
        client = KeycloakClient()

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text.return_value = "Internal server error"

        with patch.object(client, "_request_with_retry", return_value=mock_response):
            with pytest.raises(KeycloakOrganizationError, match="Failed to delete organization"):
                await client.delete_organization("org-123")

    @pytest.mark.asyncio
    async def test_delete_organization_network_error(self):
        """delete_organization() handles network errors."""
        client = KeycloakClient()

        with patch.object(
            client, "_request_with_retry", side_effect=aiohttp.ClientError("Network error")
        ):
            with pytest.raises(KeycloakOrganizationError, match="Network error"):
                await client.delete_organization("org-123")


class TestKeycloakClientHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """health_check() returns True when healthy."""
        client = KeycloakClient()
        mock_session = AsyncMock()
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.status = 200

        mock_session.get.return_value.__aenter__.return_value = mock_response

        result = await client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """health_check() returns False on failure."""
        client = KeycloakClient()
        mock_session = AsyncMock()
        client._session = mock_session

        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session.get.return_value.__aenter__.return_value = mock_response

        result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_no_session(self):
        """health_check() returns False when no session."""
        client = KeycloakClient()
        # No session initialized

        result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_network_error(self):
        """health_check() returns False on network error."""
        client = KeycloakClient()
        mock_session = AsyncMock()
        client._session = mock_session

        mock_session.get.side_effect = Exception("Network error")

        result = await client.health_check()

        assert result is False


class TestKeycloakClientIntegration:
    """Integration tests for KeycloakClient."""

    @pytest.mark.asyncio
    async def test_complete_organization_lifecycle(self):
        """Test complete organization creation and deletion."""
        client = KeycloakClient()

        # Mock session
        mock_session = AsyncMock()

        # Mock authentication
        auth_response = AsyncMock()
        auth_response.status = 200
        auth_response.json.return_value = {"access_token": "test-token", "expires_in": 3600}

        # Mock organization creation
        create_response = AsyncMock()
        create_response.status = 201
        create_response.headers = {
            "Location": "https://keycloak.com/admin/realms/master/organizations/org-test"
        }

        # Mock organization deletion
        delete_response = AsyncMock()
        delete_response.status = 204

        responses = [auth_response, create_response, delete_response]
        mock_session.post.return_value.__aenter__.side_effect = responses[:1]  # Auth
        mock_session.request.return_value.__aenter__.side_effect = responses[1:]  # Create, Delete

        with patch("aiohttp.ClientSession", return_value=mock_session):
            async with client:
                # Create organization
                org_id = await client.create_organization("test-org", "Test Organization")
                assert org_id == "org-test"

                # Delete organization
                deleted = await client.delete_organization(org_id)
                assert deleted is True

        # Verify all operations were called
        assert mock_session.post.call_count >= 1  # Auth
        assert mock_session.request.call_count >= 2  # Create + Delete

    @pytest.mark.asyncio
    async def test_organization_operations_with_retry(self):
        """Test organization operations with retry on failures."""
        client = KeycloakClient(max_retries=2)

        # Mock successful auth
        auth_response = AsyncMock()
        auth_response.status = 200
        auth_response.json.return_value = {"access_token": "test-token", "expires_in": 3600}

        # Mock organization creation: fail then succeed
        create_error_response = AsyncMock()
        create_error_response.status = 500

        create_success_response = AsyncMock()
        create_success_response.status = 201
        create_success_response.headers = {
            "Location": "https://keycloak.com/admin/realms/master/organizations/org-test"
        }

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = auth_response
        mock_session.request.return_value.__aenter__.side_effect = [
            create_error_response,
            create_success_response,
        ]

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("asyncio.sleep", new_callable=AsyncMock):  # Fast retry
                async with client:
                    org_id = await client.create_organization("test-org", "Test Organization")
                    assert org_id == "org-test"

        # Verify retry happened
        assert mock_session.request.call_count == 2


class TestKeycloakUserInvitation:
    """Tests for Keycloak user invitation functionality."""

    @pytest.mark.asyncio
    async def test_invite_user_to_organization_success(self):
        """invite_user_to_organization successfully creates and invites user."""
        client = KeycloakClient()

        # Mock successful auth
        auth_response = AsyncMock()
        auth_response.status = 200
        auth_response.json.return_value = {"access_token": "test-token", "expires_in": 3600}

        # Mock successful user creation
        create_user_response = AsyncMock()
        create_user_response.status = 201
        create_user_response.headers = {
            "Location": "https://keycloak.com/admin/realms/master/users/user-12345"
        }

        # Mock successful organization membership
        membership_response = AsyncMock()
        membership_response.status = 201

        # Mock successful email invitation
        email_response = AsyncMock()
        email_response.status = 204

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = auth_response
        mock_session.request.return_value.__aenter__.side_effect = [
            create_user_response,  # POST users
            membership_response,  # POST organization membership
            email_response,  # PUT execute actions
        ]

        with patch("aiohttp.ClientSession", return_value=mock_session):
            async with client:
                user_id = await client.invite_user_to_organization(
                    org_id="org-12345",
                    email="admin@example.com",
                    first_name="John",
                    last_name="Doe",
                )

                assert user_id == "user-12345"

        # Verify all requests were made
        assert mock_session.request.call_count == 3

    @pytest.mark.asyncio
    async def test_invite_user_existing_user(self):
        """invite_user_to_organization handles existing user."""
        client = KeycloakClient()

        # Mock successful auth
        auth_response = AsyncMock()
        auth_response.status = 200
        auth_response.json.return_value = {"access_token": "test-token", "expires_in": 3600}

        # Mock user already exists
        create_user_response = AsyncMock()
        create_user_response.status = 409  # Conflict

        # Mock successful user search
        search_response = AsyncMock()
        search_response.status = 200
        search_response.json.return_value = [{"id": "user-existing", "email": "admin@example.com"}]

        # Mock successful organization membership
        membership_response = AsyncMock()
        membership_response.status = 201

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = auth_response
        mock_session.request.return_value.__aenter__.side_effect = [
            create_user_response,  # POST users (conflict)
            search_response,  # GET users search
            membership_response,  # POST organization membership
        ]

        with patch("aiohttp.ClientSession", return_value=mock_session):
            async with client:
                user_id = await client.invite_user_to_organization(
                    org_id="org-12345", email="admin@example.com"
                )

                assert user_id == "user-existing"

        # Verify requests were made (create, search, membership)
        assert mock_session.request.call_count == 3

    @pytest.mark.asyncio
    async def test_invite_user_create_failure(self):
        """invite_user_to_organization raises error on user creation failure."""
        client = KeycloakClient()

        # Mock successful auth
        auth_response = AsyncMock()
        auth_response.status = 200
        auth_response.json.return_value = {"access_token": "test-token", "expires_in": 3600}

        # Mock user creation failure
        create_user_response = AsyncMock()
        create_user_response.status = 400
        create_user_response.text.return_value = "Invalid email format"

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = auth_response
        mock_session.request.return_value.__aenter__.return_value = create_user_response

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(KeycloakClientError, match="Failed to create user"):
                async with client:
                    await client.invite_user_to_organization(
                        org_id="org-12345", email="invalid-email"
                    )

    @pytest.mark.asyncio
    async def test_invite_user_membership_failure_continues(self):
        """invite_user_to_organization continues even if membership fails."""
        client = KeycloakClient()

        # Mock successful auth
        auth_response = AsyncMock()
        auth_response.status = 200
        auth_response.json.return_value = {"access_token": "test-token", "expires_in": 3600}

        # Mock successful user creation
        create_user_response = AsyncMock()
        create_user_response.status = 201
        create_user_response.headers = {
            "Location": "https://keycloak.com/admin/realms/master/users/user-12345"
        }

        # Mock organization membership failure (non-critical)
        membership_response = AsyncMock()
        membership_response.status = 500
        membership_response.text.return_value = "Organization not found"

        # Mock successful email invitation
        email_response = AsyncMock()
        email_response.status = 204

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = auth_response
        mock_session.request.return_value.__aenter__.side_effect = [
            create_user_response,  # POST users
            membership_response,  # POST organization membership (fails)
            email_response,  # PUT execute actions (continues)
        ]

        with patch("aiohttp.ClientSession", return_value=mock_session):
            async with client:
                user_id = await client.invite_user_to_organization(
                    org_id="org-12345", email="admin@example.com"
                )

                # Should still return user ID even if membership failed
                assert user_id == "user-12345"

        # Verify all requests were attempted
        assert mock_session.request.call_count == 3
