"""Tests for registry client gateway integration.

This module tests the enhanced RegistryClientConfig and RegistryClient
to ensure they properly support API Gateway mode with authentication.
"""

import os
from unittest.mock import patch

import pytest
from venturestrat_registry import RegistryClient, RegistryClientConfig


class TestRegistryClientConfig:
    """Test RegistryClientConfig gateway support."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = RegistryClientConfig()

        assert config.host == "localhost"
        assert config.port == 8080
        assert config.use_grpc is False
        assert config.use_gateway is False
        assert config.api_key is None
        assert config.base_url_override is None
        assert config.base_url == "http://localhost:8080/api/v1"

    def test_gateway_mode_configuration(self):
        """Test configuration with gateway mode enabled."""
        config = RegistryClientConfig(
            use_gateway=True,
            api_key="test-key-123",
            base_url_override="http://gateway:8000/api/v1/registry",
        )

        assert config.use_gateway is True
        assert config.api_key == "test-key-123"
        assert config.base_url == "http://gateway:8000/api/v1/registry"

    def test_from_env_default_mode(self):
        """Test loading configuration from environment - default mode."""
        with patch.dict(os.environ, {}, clear=True):
            config = RegistryClientConfig.from_env()

            assert config.use_gateway is False
            assert config.host == "localhost"
            assert config.port == 8080
            assert config.base_url == "http://localhost:8080/api/v1"

    def test_from_env_gateway_mode(self):
        """Test loading configuration from environment - gateway mode."""
        env_vars = {
            "SERVICE_DISCOVERY_MODE": "gateway",
            "GATEWAY_HOST": "kong-gateway",
            "GATEWAY_PORT": "8000",
            "API_KEY": "gateway-key-456",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = RegistryClientConfig.from_env()

            assert config.use_gateway is True
            assert config.api_key == "gateway-key-456"
            assert config.base_url == "http://kong-gateway:8000/api/v1/registry"

    def test_from_env_explicit_base_url(self):
        """Test loading configuration with explicit REGISTRY_BASE_URL."""
        env_vars = {
            "SERVICE_DISCOVERY_MODE": "gateway",
            "REGISTRY_BASE_URL": "https://api.venturestrat.io/registry",
            "X_API_KEY": "prod-key-789",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = RegistryClientConfig.from_env()

            assert config.use_gateway is True
            assert config.api_key == "prod-key-789"
            assert config.base_url == "https://api.venturestrat.io/registry"

    def test_from_env_fallback_to_registry_host(self):
        """Test gateway mode falls back to REGISTRY_HOST when GATEWAY_HOST not set."""
        env_vars = {
            "SERVICE_DISCOVERY_MODE": "gateway",
            "REGISTRY_HOST": "custom-host",
            "REGISTRY_PORT": "9000",
            "API_KEY": "fallback-key",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = RegistryClientConfig.from_env()

            assert config.use_gateway is True
            assert config.api_key == "fallback-key"
            assert config.base_url == "http://custom-host:8000/api/v1/registry"

    def test_api_key_priority(self):
        """Test API_KEY takes precedence over X_API_KEY."""
        env_vars = {
            "SERVICE_DISCOVERY_MODE": "gateway",
            "API_KEY": "primary-key",
            "X_API_KEY": "secondary-key",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = RegistryClientConfig.from_env()

            assert config.api_key == "primary-key"


class TestRegistryClientGatewayMode:
    """Test RegistryClient with gateway mode enabled."""

    @pytest.fixture
    def gateway_config(self):
        """Configuration for gateway mode testing."""
        return RegistryClientConfig(
            use_gateway=True,
            api_key="test-api-key-12345",
            base_url_override="http://localhost:8000/api/v1/registry",
            timeout=5.0,
        )

    @pytest.fixture
    def direct_config(self):
        """Configuration for direct mode testing."""
        return RegistryClientConfig(
            use_gateway=False,
            timeout=5.0,
        )

    @pytest.mark.asyncio
    async def test_gateway_mode_adds_api_key_header(self, gateway_config):
        """Test that gateway mode adds X-API-Key header to requests."""
        client = RegistryClient(config=gateway_config)

        # Enter context to initialize HTTP client
        await client.__aenter__()

        try:
            # Check that API key was added to default headers
            assert client._http_client.headers["X-API-Key"] == "test-api-key-12345"
            assert client._http_client.base_url == "http://localhost:8000/api/v1/registry"

        finally:
            # Clean up
            await client.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_direct_mode_no_api_key_header(self, direct_config):
        """Test that direct mode does not add API key header."""
        client = RegistryClient(config=direct_config)

        # Enter context to initialize HTTP client
        await client.__aenter__()

        try:
            # Check that no API key header was added
            assert "X-API-Key" not in client._http_client.headers
            assert client._http_client.base_url == "http://localhost:8080/api/v1"

        finally:
            # Clean up
            await client.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_gateway_mode_without_api_key(self):
        """Test gateway mode works without API key (for public endpoints)."""
        config = RegistryClientConfig(
            use_gateway=True,
            api_key=None,  # No API key
            base_url_override="http://localhost:8000/api/v1/registry",
        )

        client = RegistryClient(config=config)

        # Enter context to initialize HTTP client
        await client.__aenter__()

        try:
            # Should not crash, but also should not have API key header
            assert "X-API-Key" not in client._http_client.headers

        finally:
            # Clean up
            await client.__aexit__(None, None, None)


class TestRegistryClientEnvironmentIntegration:
    """Test complete environment-based configuration."""

    @pytest.mark.asyncio
    async def test_client_from_dev_env(self):
        """Test creating client from typical dev environment configuration."""
        dev_env = {
            "SERVICE_DISCOVERY_MODE": "gateway",
            "REGISTRY_HOST": "localhost",
            "REGISTRY_PORT": "8000",
            "API_KEY": "dev-api-key-12345",
            "GATEWAY_HOST": "localhost",
            "GATEWAY_PORT": "8000",
        }

        with patch.dict(os.environ, dev_env, clear=True):
            config = RegistryClientConfig.from_env()
            client = RegistryClient(config=config)

            await client.__aenter__()

            try:
                # Verify configuration
                assert config.use_gateway is True
                assert config.api_key == "dev-api-key-12345"
                assert config.base_url == "http://localhost:8000/api/v1/registry"
                assert client._http_client.headers["X-API-Key"] == "dev-api-key-12345"

            finally:
                await client.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_client_from_production_env(self):
        """Test creating client from production environment configuration."""
        prod_env = {
            "REGISTRY_BASE_URL": "https://api.venturestrat.io/registry",
            "SERVICE_DISCOVERY_MODE": "gateway",
            "API_KEY": "prod-key-secure-token",
        }

        with patch.dict(os.environ, prod_env, clear=True):
            config = RegistryClientConfig.from_env()
            client = RegistryClient(config=config)

            await client.__aenter__()

            try:
                # Verify configuration
                assert config.use_gateway is True
                assert config.api_key == "prod-key-secure-token"
                assert config.base_url == "https://api.venturestrat.io/registry"
                assert client._http_client.headers["X-API-Key"] == "prod-key-secure-token"

            finally:
                await client.__aexit__(None, None, None)


# Integration test requiring actual gateway
@pytest.mark.integration
class TestLiveGatewayIntegration:
    """Live integration tests requiring running gateway infrastructure."""

    @pytest.mark.asyncio
    async def test_registry_client_through_live_gateway(self):
        """Test registry client can connect through live gateway.

        This test requires:
        1. Kong gateway running on localhost:8000
        2. Registry service running and registered with Consul
        3. Valid API key configured in Kong
        """
        # Skip if not in integration test environment
        if not os.getenv("RUN_INTEGRATION_TESTS"):
            pytest.skip("Integration tests disabled - set RUN_INTEGRATION_TESTS=1")

        config = RegistryClientConfig(
            use_gateway=True,
            api_key="dev-api-key-12345",
            base_url_override="http://localhost:8000/api/v1/registry",
            timeout=10.0,
        )

        async with RegistryClient(config=config) as client:
            # Test basic operations
            services = await client.list_services()
            assert isinstance(services, list)

            # If registry service is running, we should get some results
            # If not, we should at least get a valid HTTP response (not connection error)
