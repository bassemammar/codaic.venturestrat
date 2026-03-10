"""Tests for registry-service synchronous client."""

from unittest.mock import Mock, patch

import grpc
import pytest

from venturestrat_registry_service import RegistryServiceClient, RegistryServiceConfig
from venturestrat_registry_service.auth import ApiKeyAuthProvider
from venturestrat_registry_service.exceptions import RegistryServiceConnectionError


class TestRegistryServiceClient:
    """Test cases for synchronous registry-service client."""

    def test_init_with_defaults(self) -> None:
        """Test client initialization with defaults."""
        with patch("grpc.insecure_channel") as mock_channel:
            client = RegistryServiceClient()

            assert client.host == "localhost"
            assert client.port == 50051
            assert client.timeout == 30.0
            mock_channel.assert_called_once_with("localhost:50051", options=[])

    def test_init_with_custom_values(self) -> None:
        """Test client initialization with custom values."""
        with patch("grpc.secure_channel") as mock_channel:
            client = RegistryServiceClient(
                host="api.example.com", port=443, secure=True, timeout=60.0
            )

            assert client.host == "api.example.com"
            assert client.port == 443
            assert client.timeout == 60.0
            mock_channel.assert_called_once()

    def test_from_config(self) -> None:
        """Test creating client from configuration."""
        config = RegistryServiceConfig(
            host="config.example.com", port=9090, timeout=45.0
        )

        with patch("grpc.insecure_channel"):
            client = RegistryServiceClient.from_config(config)

            assert client.host == "config.example.com"
            assert client.port == 9090
            assert client.timeout == 45.0

    def test_from_config_with_auth(self) -> None:
        """Test creating client from configuration with authentication."""
        config = RegistryServiceConfig(host="api.example.com", auth_api_key="test-key")

        with patch("grpc.insecure_channel"):
            client = RegistryServiceClient.from_config(config)

            assert isinstance(client.auth, ApiKeyAuthProvider)
            assert client.auth.api_key == "test-key"

    def test_context_manager(self, mock_client) -> None:
        """Test client as context manager."""
        with mock_client as client:
            assert client is not None

        # Verify close was called
        mock_client.channel.close.assert_called_once()

    def test_health_check_success(self, mock_client) -> None:
        """Test successful health check."""
        mock_client.channel.get_state.return_value = grpc.ChannelConnectivity.READY

        result = mock_client.health_check()
        assert result is True

    def test_health_check_failure(self, mock_client) -> None:
        """Test failed health check."""
        mock_client.channel.get_state.side_effect = Exception("Connection failed")

        with pytest.raises(RegistryServiceConnectionError):
            mock_client.health_check()

    def test_get_metadata_no_auth(self, mock_client) -> None:
        """Test metadata without authentication."""
        metadata = mock_client._get_metadata()
        assert isinstance(metadata, dict)

    def test_get_metadata_with_auth(self, mock_client) -> None:
        """Test metadata with authentication."""
        mock_auth = Mock()
        mock_auth.get_metadata.return_value = {"authorization": "Bearer token"}
        mock_client.auth = mock_auth

        metadata = mock_client._get_metadata()
        assert "authorization" in metadata
        assert metadata["authorization"] == "Bearer token"

    def test_get_metadata_with_custom_metadata(self, mock_client) -> None:
        """Test metadata with custom metadata."""
        custom_metadata = {"x-custom": "value"}
        metadata = mock_client._get_metadata(custom_metadata)

        assert "x-custom" in metadata
        assert metadata["x-custom"] == "value"

    def test_close(self, mock_client) -> None:
        """Test client close."""
        mock_client.close()
        mock_client.channel.close.assert_called_once()

    def test_grpc_options(self) -> None:
        """Test gRPC options are passed correctly."""
        options = {"grpc.keepalive_time_ms": 30000}

        with patch("grpc.insecure_channel") as mock_channel:
            RegistryServiceClient(**options)

            # Verify options were passed
            mock_channel.assert_called_once()
            call_args = mock_channel.call_args
            assert call_args[1]["options"] == list(options.items())

    def test_setup_stubs(self, mock_client) -> None:
        """Test stub setup (placeholder test)."""
        # This is a placeholder since actual stubs depend on protobuf generation
        mock_client._setup_stubs()
        # No assertion needed - just verify no exceptions
