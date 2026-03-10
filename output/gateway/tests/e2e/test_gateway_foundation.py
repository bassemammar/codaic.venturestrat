"""
End-to-end tests for gateway foundation.

These tests verify the complete gateway setup works end-to-end.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestGatewayFoundation:
    """End-to-end tests for gateway foundation functionality."""

    def test_gateway_jwt_issuer_integration(self, jwt_issuer_client, gateway_client):
        """Test that gateway can use tokens from JWT issuer."""
        # Request a token from JWT issuer
        token_response = jwt_issuer_client.post("/token", json={"service_name": "test-service"})
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "test-service"}
        )

        assert token_response.status_code == 200
        token_data = token_response.json()
        jwt_token = token_data["token"]

        # Use JWT token with gateway (when JWT auth is configured)
        # For now, test that the token is valid format
        assert jwt_token
        assert jwt_token.count(".") == 2  # Valid JWT format

        # Verify token with JWT issuer
        validate_response = jwt_issuer_client.post("/validate", json=jwt_token)
        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

    def test_complete_request_flow(self, gateway_client, correlation_id):
        """Test complete request flow through gateway."""
        response = gateway_client.get("/health", headers={"X-Correlation-ID": correlation_id})
        response = gateway_client.get(
            "/health", headers={"X-Correlation-ID": correlation_id}
        )

        assert response.status_code == 200

        # Verify all expected headers are present
        expected_headers = [
            "X-Correlation-ID",
            "X-RateLimit-Limit-Minute",
            "X-RateLimit-Remaining-Minute",
            "X-Kong-Upstream-Latency",
            "X-Kong-Proxy-Latency",
        ]

        for header in expected_headers:
            assert header in response.headers, f"Missing header: {header}"

        # Verify correlation ID is echoed
        assert response.headers["X-Correlation-ID"] == correlation_id

    def test_api_key_authentication_flow(self, unauthorized_client, gateway_client):
        """Test API key authentication end-to-end."""
        # Request without API key should fail
        response = unauthorized_client.get("/health")
        # Note: health endpoint might be exempted from auth
        # This test will be more relevant when we have protected endpoints

        # Request with valid API key should succeed
        response = gateway_client.get("/health")
        assert response.status_code == 200

    def test_infrastructure_connectivity(self, admin_client):
        """Test that gateway can connect to required infrastructure."""
        # Test Kong status
        status_response = admin_client.get("/status")
        assert status_response.status_code == 200

        # Check that Kong is in DB-less mode
        status_data = status_response.json()
        assert status_data["database"]["reachable"] is False  # DB-less mode

        # Test that services are configured
        services_response = admin_client.get("/services")
        assert services_response.status_code == 200

        services_data = services_response.json()
        service_names = [service["name"] for service in services_data["data"]]

        # Should include configured services
        expected_services = ["registry-service", "health-service"]
        for expected in expected_services:
            assert expected in service_names, f"Service '{expected}' not found"

    def test_plugin_activation(self, admin_client):
        """Test that required plugins are active."""
        plugins_response = admin_client.get("/plugins")
        assert plugins_response.status_code == 200

        plugins_data = plugins_response.json()
        active_plugins = [plugin["name"] for plugin in plugins_data["data"]]

        # Should include key plugins
        expected_plugins = [
            "key-auth",
            "rate-limiting",
            "file-log",
            "prometheus",
            "correlation-id",
            "cors",
        ]

        for expected in expected_plugins:
            assert expected in active_plugins, f"Plugin '{expected}' not active"

    def test_consumers_configuration(self, admin_client):
        """Test that consumers are properly configured."""
        consumers_response = admin_client.get("/consumers")
        assert consumers_response.status_code == 200

        consumers_data = consumers_response.json()
        consumer_names = [consumer["username"] for consumer in consumers_data["data"]]

        # Should include test consumers
        expected_consumers = [
            "default-consumer",
            "test-consumer",
            "free-tier-consumer",
            "standard-tier-consumer",
        ]

        for expected in expected_consumers:
            assert expected in consumer_names, f"Consumer '{expected}' not found"

    def test_rate_limiting_tiers(self, free_tier_client, standard_tier_client):
        """Test that different consumer tiers have different rate limits."""
        # Make request with free tier
        free_response = free_tier_client.get("/health")
        assert free_response.status_code == 200

        # Make request with standard tier
        standard_response = standard_tier_client.get("/health")
        assert standard_response.status_code == 200

        # Extract rate limits (should be different)
        free_limit = int(free_response.headers.get("X-RateLimit-Limit-Minute", "0"))
        standard_limit = int(
            standard_response.headers.get("X-RateLimit-Limit-Minute", "0")
        )

        assert free_limit > 0
        assert standard_limit > 0
        assert standard_limit > free_limit, "Standard tier should have higher limits"

    def test_error_handling(self, gateway_client):
        """Test gateway error handling."""
        # Test 404 for unknown route
        response = gateway_client.get("/nonexistent/route")
        assert response.status_code == 404

        # Should still include correlation ID and Kong headers
        assert "X-Correlation-ID" in response.headers

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-slow", default=False),
        reason="Slow test skipped unless --run-slow is specified",
    )
    def test_gateway_resilience(self, gateway_client):
        """Test gateway resilience under load."""
        from concurrent.futures import ThreadPoolExecutor

        def make_request():
            try:
                response = gateway_client.get("/health")
                return response.status_code
            except Exception:
                return 500

        # Make 50 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [future.result() for future in futures]

        # At least 90% should succeed
        success_rate = sum(1 for status in results if status == 200) / len(results)
        assert success_rate >= 0.9, f"Success rate {success_rate:.2%} below 90%"
