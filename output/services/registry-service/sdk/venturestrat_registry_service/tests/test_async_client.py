"""Tests for registry-service asynchronous client."""

from unittest.mock import AsyncMock, patch

import grpc.aio
import pytest

from venturestrat_registry_service import (
    AsyncRegistryServiceClient,
    RegistryServiceConfig,
)
from venturestrat_registry_service.auth import ApiKeyAuthProvider
from venturestrat_registry_service.exceptions import RegistryServiceConnectionError


class TestAsyncRegistryServiceClient:
    """Test cases for asynchronous registry-service client."""

    def test_init_with_defaults(self) -> None:
        """Test async client initialization with defaults."""
        client = AsyncRegistryServiceClient()

        assert client.host == "localhost"
        assert client.port == 50051
        assert client.timeout == 30.0
        assert client.channel is None  # Not connected yet

    def test_init_with_custom_values(self) -> None:
        """Test async client initialization with custom values."""
        client = AsyncRegistryServiceClient(
            host="api.example.com", port=443, secure=True, timeout=60.0
        )

        assert client.host == "api.example.com"
        assert client.port == 443
        assert client.timeout == 60.0
        assert client._secure is True

    def test_from_config(self) -> None:
        """Test creating async client from configuration."""
        config = RegistryServiceConfig(
            host="config.example.com", port=9090, timeout=45.0
        )

        client = AsyncRegistryServiceClient.from_config(config)

        assert client.host == "config.example.com"
        assert client.port == 9090
        assert client.timeout == 45.0

    def test_from_config_with_auth(self) -> None:
        """Test creating async client from configuration with authentication."""
        config = RegistryServiceConfig(host="api.example.com", auth_api_key="test-key")

        client = AsyncRegistryServiceClient.from_config(config)

        assert isinstance(client.auth, ApiKeyAuthProvider)
        assert client.auth.api_key == "test-key"

    @pytest.mark.asyncio()
    async def test_context_manager(self, mock_async_client) -> None:
    async def test_context_manager(self, mock_async_client):
        """Test async client as context manager."""
        async with mock_async_client as client:
            assert client is not None
            assert client.channel is not None

    @pytest.mark.asyncio()
    async def test_connect(self) -> None:
    async def test_connect(self):
        """Test async connection establishment."""
        mock_channel = AsyncMock(spec=grpc.aio.Channel)

        with patch("grpc.aio.insecure_channel", return_value=mock_channel):
            client = AsyncRegistryServiceClient()
            await client._connect()

            assert client.channel is mock_channel

    @pytest.mark.asyncio()
    async def test_connect_secure(self) -> None:
    async def test_connect_secure(self):
        """Test async secure connection establishment."""
        mock_channel = AsyncMock(spec=grpc.aio.Channel)

        with patch("grpc.aio.secure_channel", return_value=mock_channel):
            client = AsyncRegistryServiceClient(secure=True)
            await client._connect()

            assert client.channel is mock_channel

    @pytest.mark.asyncio()
    async def test_health_check_success(self, mock_async_client) -> None:
    async def test_health_check_success(self, mock_async_client):
        """Test successful async health check."""
        mock_async_client.channel.get_state.return_value = (
            grpc.ChannelConnectivity.READY
        )

        result = await mock_async_client.health_check()
        assert result is True

    @pytest.mark.asyncio()
    async def test_health_check_failure(self, mock_async_client) -> None:
    async def test_health_check_failure(self, mock_async_client):
        """Test failed async health check."""
        mock_async_client.channel.get_state.side_effect = Exception("Connection failed")

        with pytest.raises(RegistryServiceConnectionError):
            await mock_async_client.health_check()

    @pytest.mark.asyncio()
    async def test_health_check_not_connected(self) -> None:
    async def test_health_check_not_connected(self):
        """Test health check when not connected."""
        client = AsyncRegistryServiceClient()

        with pytest.raises(
            RegistryServiceConnectionError, match="Client not connected"
        ):
            await client.health_check()

    def test_get_metadata_no_auth(self, mock_async_client) -> None:
        """Test metadata without authentication."""
        metadata = mock_async_client._get_metadata()
        assert isinstance(metadata, dict)

    def test_get_metadata_with_auth(self, mock_async_client) -> None:
        """Test metadata with authentication."""
        from unittest.mock import Mock

        mock_auth = Mock()
        mock_auth.get_metadata.return_value = {"authorization": "Bearer token"}
        mock_async_client.auth = mock_auth

        metadata = mock_async_client._get_metadata()
        assert "authorization" in metadata
        assert metadata["authorization"] == "Bearer token"

    @pytest.mark.asyncio()
    async def test_close(self, mock_async_client) -> None:
    async def test_close(self, mock_async_client):
        """Test async client close."""
        await mock_async_client.close()
        mock_async_client.channel.close.assert_called_once()

    @pytest.mark.asyncio()
    async def test_setup_stubs(self, mock_async_client) -> None:
    async def test_setup_stubs(self, mock_async_client):
        """Test async stub setup (placeholder test)."""
        # This is a placeholder since actual stubs depend on protobuf generation
        await mock_async_client._setup_stubs()
        # No assertion needed - just verify no exceptions

    def test_grpc_options(self) -> None:
        """Test gRPC options are stored correctly."""
        options = {"grpc.keepalive_time_ms": 30000}

        client = AsyncRegistryServiceClient(**options)
        assert client._grpc_options == options
