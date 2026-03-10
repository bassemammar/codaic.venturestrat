"""Integration tests for registry service access through Kong Gateway.

This test module verifies that the registry-service can be accessed through
the API Gateway with proper authentication, rate limiting, and routing.
"""

import os
from pathlib import Path

import httpx
import pytest

# Add registry SDK to path for testing
import sys

gateway_root = Path(__file__).parent.parent.parent
registry_sdk_path = gateway_root.parent / "services/registry-service/sdk"
sys.path.insert(0, str(registry_sdk_path))

from venturestrat_registry import RegistryClient, RegistryClientConfig


class TestRegistryGatewayIntegration:
    """Test registry service access through Kong Gateway."""

    @pytest.fixture
    def gateway_url(self):
        """Gateway base URL."""
        return "http://localhost:8000"

    @pytest.fixture
    def api_key(self):
        """Valid API key for gateway access."""
        return "dev-api-key-12345"

    @pytest.fixture
    def invalid_api_key(self):
        """Invalid API key for negative testing."""
        return "invalid-key-99999"

    @pytest.fixture
    def registry_gateway_config(self, api_key):
        """Registry client configuration for gateway access."""
        return RegistryClientConfig(
            host="localhost",
            port=8000,
            use_gateway=True,
            api_key=api_key,
            base_url_override="http://localhost:8000/api/v1/registry",
            timeout=10.0,
        )

    @pytest.fixture
    def direct_config(self):
        """Registry client configuration for direct access."""
        return RegistryClientConfig(
            host="localhost",
            port=8080,
            use_gateway=False,
            timeout=10.0,
        )

    @pytest.mark.asyncio
    async def test_gateway_routing_to_registry(self, gateway_url, api_key):
        """Test that /api/v1/registry/* routes to registry service."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gateway_url}/api/v1/registry/services",
                headers={"X-API-Key": api_key},
                timeout=10,
            )

            # Should reach the registry service (even if it returns an error)
            # We're testing routing, not the service itself
            assert response.status_code in [
                200,
                404,
                500,
            ], f"Unexpected status: {response.status_code}"

            # Check that request reached Kong (should have correlation ID)
            assert "X-Correlation-ID" in response.headers

    @pytest.mark.asyncio
    async def test_api_key_authentication_required(self, gateway_url):
        """Test that API key is required for gateway access."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gateway_url}/api/v1/registry/services",
                timeout=10,
            )

            # Should return 401 Unauthorized without API key
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, gateway_url, invalid_api_key):
        """Test that invalid API keys are rejected."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gateway_url}/api/v1/registry/services",
                headers={"X-API-Key": invalid_api_key},
                timeout=10,
            )

            # Should return 403 Forbidden with invalid key
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_registry_client_gateway_mode(self, registry_gateway_config):
        """Test registry client can connect through gateway."""
        async with RegistryClient(config=registry_gateway_config) as client:
            # Test basic connectivity - list services
            try:
                services = await client.list_services()
                # If we get here, routing is working
                assert isinstance(services, list)
            except Exception as e:
                # If registry service is not running, we should at least
                # get a proper HTTP error, not a connection error
                assert "Connection" not in str(e), f"Connection failed: {e}"

    @pytest.mark.asyncio
    async def test_registry_client_config_from_env(self):
        """Test that RegistryClientConfig.from_env() supports gateway mode."""
        # Set environment variables for gateway mode
        original_env = {}
        test_env = {
            "SERVICE_DISCOVERY_MODE": "gateway",
            "GATEWAY_HOST": "localhost",
            "GATEWAY_PORT": "8000",
            "API_KEY": "dev-api-key-12345",
        }

        # Backup and set test environment
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = RegistryClientConfig.from_env()

            # Should be configured for gateway mode
            assert config.use_gateway is True
            assert config.api_key == "dev-api-key-12345"
            assert config.base_url == "http://localhost:8000/api/v1/registry"

        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

    @pytest.mark.asyncio
    async def test_rate_limiting_headers_present(self, gateway_url, api_key):
        """Test that rate limiting headers are included in responses."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gateway_url}/api/v1/registry/services",
                headers={"X-API-Key": api_key},
                timeout=10,
            )

            # Check for rate limiting headers
            assert "X-RateLimit-Limit-Minute" in response.headers
            assert "X-RateLimit-Remaining-Minute" in response.headers

    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self, gateway_url, api_key):
        """Test that correlation IDs are generated and echoed."""
        correlation_id = "test-correlation-12345"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gateway_url}/api/v1/registry/services",
                headers={
                    "X-API-Key": api_key,
                    "X-Correlation-ID": correlation_id,
                },
                timeout=10,
            )

            # Should echo back the correlation ID
            assert response.headers.get("X-Correlation-ID") == correlation_id

    @pytest.mark.asyncio
    async def test_path_stripping_works(self, gateway_url, api_key):
        """Test that /api/v1/registry/* gets stripped to /* for backend."""
        # This test verifies the Kong route configuration is correct
        async with httpx.AsyncClient() as client:
            # Try accessing a specific path that should be stripped
            response = await client.get(
                f"{gateway_url}/api/v1/registry/health/ready",
                headers={"X-API-Key": api_key},
                timeout=10,
            )

            # If path stripping works correctly, this should reach the
            # registry service's /health/ready endpoint
            # The exact response depends on registry service state,
            # but we should not get a 404 from Kong
            assert (
                response.status_code != 404
            ), "Path not found - check Kong routing config"

    @pytest.mark.asyncio
    async def test_upstream_headers_added(self, gateway_url, api_key):
        """Test that Kong adds expected headers to upstream requests."""
        # This test would require the registry service to echo back headers
        # For now, we just verify the request reaches the backend
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gateway_url}/api/v1/registry/services",
                headers={"X-API-Key": api_key},
                timeout=10,
            )

            # Verify Kong added its headers to the response
            assert "X-Kong-Upstream-Latency" in response.headers
            assert "X-Kong-Proxy-Latency" in response.headers


@pytest.mark.integration
class TestGatewayEnvironmentConfiguration:
    """Test environment-based configuration for gateway integration."""

    def test_dev_env_file_configuration(self):
        """Test that dev.env file contains correct gateway configuration."""
        dev_env_path = Path(__file__).parent.parent.parent.parent / "dev.env"

        # Should exist
        assert dev_env_path.exists(), "dev.env file should exist in project root"

        # Read and verify contents
        env_content = dev_env_path.read_text()

        assert "SERVICE_DISCOVERY_MODE=gateway" in env_content
        assert "REGISTRY_HOST=localhost" in env_content
        assert "REGISTRY_PORT=8000" in env_content
        assert "API_KEY=dev-api-key-12345" in env_content
        assert "GATEWAY_BASE_URL=http://localhost:8000" in env_content

    def test_registry_client_config_defaults(self):
        """Test default configuration behavior."""
        config = RegistryClientConfig()

        # Default should be direct mode
        assert config.use_gateway is False
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.base_url == "http://localhost:8080/api/v1"
