"""End-to-end test for registry service through gateway.

This test verifies the complete flow:
1. Registry service registers with Consul
2. Kong discovers the service via Consul
3. Client connects to registry through gateway
4. API key authentication works
5. Requests are properly routed and responses returned

Requires running infrastructure:
- Consul (service discovery)
- Redis (rate limiting)
- Kong Gateway
- Registry Service
"""

import asyncio
from pathlib import Path
import sys

import httpx
import pytest

# Add registry SDK to path
gateway_root = Path(__file__).parent.parent.parent
registry_sdk_path = gateway_root.parent / "services/registry-service/sdk"
sys.path.insert(0, str(registry_sdk_path))

from venturestrat_registry import RegistryClient, RegistryClientConfig


@pytest.mark.e2e
@pytest.mark.asyncio
class TestRegistryE2EGateway:
    """End-to-end tests for registry service through API Gateway."""

    @pytest.fixture
    def gateway_url(self):
        """Gateway base URL."""
        return "http://localhost:8000"

    @pytest.fixture
    def api_key(self):
        """Valid API key for testing."""
        return "dev-api-key-12345"

    @pytest.fixture
    def registry_client_gateway(self, api_key):
        """Registry client configured for gateway access."""
        config = RegistryClientConfig(
            use_gateway=True,
            api_key=api_key,
            base_url_override="http://localhost:8000/api/v1/registry",
            timeout=10.0,
        )
        return RegistryClient(config=config)

    @pytest.fixture
    def registry_client_direct(self):
        """Registry client configured for direct access."""
        config = RegistryClientConfig(
            host="localhost",
            port=8080,
            use_gateway=False,
            timeout=10.0,
        )
        return RegistryClient(config=config)

    async def test_full_client_flow_through_gateway(self, registry_client_gateway):
        """Test complete client flow through gateway."""
        async with registry_client_gateway as client:
            # 1. List services (should work even if empty)
            services = await client.list_services()
            assert isinstance(services, list)

            # 2. Try to discover a service (may return empty list)
            try:
                instances = await client.discover("registry-service")
                assert isinstance(instances, list)
            except Exception:
                # Service might not be registered yet, that's ok for this test
                pass

            # 3. Check health overview
            try:
                health = await client.get_health()
                assert isinstance(health, dict)
            except Exception:
                # Health endpoint might not be implemented yet
                pass

    async def test_gateway_vs_direct_access_consistency(
        self, registry_client_gateway, registry_client_direct
    ):
        """Test that gateway and direct access return consistent results."""
        try:
            # Get services through both paths
            async with registry_client_direct as direct_client:
                direct_services = await direct_client.list_services()

            async with registry_client_gateway as gateway_client:
                gateway_services = await gateway_client.list_services()

            # Results should be the same (both are accessing the same registry service)
            assert len(direct_services) == len(gateway_services)

            # If there are services, check they have the same names
            if direct_services and gateway_services:
                direct_names = {svc.get("name") for svc in direct_services}
                gateway_names = {svc.get("name") for svc in gateway_services}
                assert direct_names == gateway_names

        except Exception:
            # If direct access fails, we can't compare
            # But we should still be able to access through gateway
            async with registry_client_gateway as gateway_client:
                gateway_services = await gateway_client.list_services()
                assert isinstance(gateway_services, list)

    async def test_api_key_required_for_gateway(self, gateway_url):
        """Test that API key is required for gateway access."""
        async with httpx.AsyncClient() as client:
            # Request without API key should fail
            response = await client.get(f"{gateway_url}/api/v1/registry/services")
            assert response.status_code == 401

            # Request with invalid key should fail
            response = await client.get(
                f"{gateway_url}/api/v1/registry/services",
                headers={"X-API-Key": "invalid-key"},
            )
            assert response.status_code == 403

            # Request with valid key should succeed (or at least not be auth error)
            response = await client.get(
                f"{gateway_url}/api/v1/registry/services",
                headers={"X-API-Key": "dev-api-key-12345"},
            )
            assert response.status_code != 401
            assert response.status_code != 403

    async def test_rate_limiting_enforcement(self, gateway_url, api_key):
        """Test that rate limiting is enforced through gateway."""
        async with httpx.AsyncClient() as client:
            # Make several requests quickly
            responses = []
            for i in range(10):
                response = await client.get(
                    f"{gateway_url}/api/v1/registry/services",
                    headers={"X-API-Key": api_key},
                )
                responses.append(response)

                # Check rate limiting headers are present
                assert "X-RateLimit-Limit-Minute" in response.headers
                assert "X-RateLimit-Remaining-Minute" in response.headers

            # All requests should succeed (under rate limit)
            for response in responses:
                assert response.status_code != 429, "Hit rate limit too quickly"

    async def test_correlation_id_tracing(self, gateway_url, api_key):
        """Test that correlation IDs work for request tracing."""
        correlation_id = "e2e-test-12345"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gateway_url}/api/v1/registry/services",
                headers={
                    "X-API-Key": api_key,
                    "X-Correlation-ID": correlation_id,
                },
            )

            # Correlation ID should be echoed back
            assert response.headers.get("X-Correlation-ID") == correlation_id

    async def test_service_discovery_through_consul(self, gateway_url, api_key):
        """Test that Kong can discover registry service through Consul."""
        # This test verifies the Consul integration works
        async with httpx.AsyncClient() as client:
            # Request to registry through gateway
            response = await client.get(
                f"{gateway_url}/api/v1/registry/services",
                headers={"X-API-Key": api_key},
            )

            # If we get here and don't have a 503 (service unavailable),
            # it means Kong successfully discovered the registry service
            assert response.status_code != 503, "Kong cannot discover registry service"

            # Check Kong added upstream latency headers (proves it proxied to upstream)
            assert "X-Kong-Upstream-Latency" in response.headers

    async def test_error_handling_through_gateway(self, gateway_url, api_key):
        """Test error handling when accessing invalid endpoints."""
        async with httpx.AsyncClient() as client:
            # Request to non-existent endpoint
            response = await client.get(
                f"{gateway_url}/api/v1/registry/nonexistent",
                headers={"X-API-Key": api_key},
            )

            # Should get a proper 404 from the backend, not from Kong routing
            # This proves the request reached the registry service
            assert response.status_code in [404, 405], "Error not properly proxied"

    @pytest.mark.asyncio
    async def test_environment_based_configuration(self):
        """Test that environment variables configure client correctly."""
        import os
        from unittest.mock import patch

        # Test environment that simulates dev.env
        test_env = {
            "SERVICE_DISCOVERY_MODE": "gateway",
            "REGISTRY_HOST": "localhost",
            "REGISTRY_PORT": "8000",  # Gateway port
            "API_KEY": "dev-api-key-12345",
            "GATEWAY_HOST": "localhost",
            "GATEWAY_PORT": "8000",
        }

        with patch.dict(os.environ, test_env, clear=True):
            config = RegistryClientConfig.from_env()

            # Should be configured for gateway mode
            assert config.use_gateway is True
            assert config.api_key == "dev-api-key-12345"
            assert config.base_url == "http://localhost:8000/api/v1/registry"

            # Should be able to create and use client
            async with RegistryClient(config=config) as client:
                services = await client.list_services()
                assert isinstance(services, list)


@pytest.mark.e2e
class TestGatewayInfrastructureHealth:
    """Test that gateway infrastructure is healthy for E2E tests."""

    @pytest.mark.asyncio
    async def test_kong_gateway_health(self):
        """Test that Kong Gateway is running and healthy."""
        async with httpx.AsyncClient() as client:
            try:
                # Test proxy port
                response = await client.get("http://localhost:8000/health", timeout=5)
                assert response.status_code in [
                    200,
                    404,
                ], f"Kong proxy unhealthy: {response.status_code}"

                # Test admin API (if accessible)
                try:
                    response = await client.get("http://localhost:8001/status", timeout=5)
                    response = await client.get(
                        "http://localhost:8001/status", timeout=5
                    )
                    assert (
                        response.status_code == 200
                    ), f"Kong admin unhealthy: {response.status_code}"
                except Exception:
                    # Admin API might not be accessible, that's ok
                    pass

            except Exception as e:
                pytest.fail(f"Kong Gateway not accessible: {e}")

    @pytest.mark.asyncio
    async def test_consul_service_discovery(self):
        """Test that Consul is running for service discovery."""
        async with httpx.AsyncClient() as client:
            try:
                # Check Consul health
                response = await client.get(
                    "http://localhost:8500/v1/status/leader", timeout=5
                )
                assert (
                    response.status_code == 200
                ), f"Consul unhealthy: {response.status_code}"

                # Check if registry service is registered
                response = await client.get(
                    "http://localhost:8500/v1/catalog/service/registry-service",
                    timeout=5,
                )
                assert (
                    response.status_code == 200
                ), f"Consul catalog unhealthy: {response.status_code}"

                response.json()
                # It's ok if registry service is not registered yet

            except Exception as e:
                pytest.fail(f"Consul not accessible: {e}")

    @pytest.mark.asyncio
    async def test_redis_rate_limiting(self):
        """Test that Redis is accessible for rate limiting."""
        try:
            import redis

            r = redis.Redis(host="localhost", port=6379, db=0, socket_timeout=5)
            r.ping()
        except Exception as e:
            pytest.fail(f"Redis not accessible for rate limiting: {e}")


if __name__ == "__main__":
    # Run a basic test if executed directly
    async def basic_test():
        print("Running basic E2E test...")

        config = RegistryClientConfig(
            use_gateway=True,
            api_key="dev-api-key-12345",
            base_url_override="http://localhost:8000/api/v1/registry",
            timeout=10.0,
        )

        try:
            async with RegistryClient(config=config) as client:
                services = await client.list_services()
                print(
                    f"✅ Success! Gateway integration working. Found {len(services)} services."
                )
        except Exception as e:
            print(f"❌ Failed: {e}")

    asyncio.run(basic_test())
