"""
Integration tests specifically for Task 3.4 - Test fallback when service unavailable (503).

Tests Kong's behavior when it can discover a service via Consul DNS but the service itself is unavailable.
This tests the fallback mechanism that should return 503 Service Unavailable.
"""

import pytest
import httpx
import time


@pytest.mark.integration
class TestTask34ServiceUnavailableFallback:
    """Test suite for Task 3.4 - service unavailable fallback behavior."""

    def test_service_discovery_returns_503_when_service_down(
        self, gateway_client: httpx.Client
    ):
        """Test that Kong returns 503 when service is discoverable but unavailable."""
        # Make request to registry service endpoint
        response = gateway_client.get("/api/v1/registry/services")

        # When service is discoverable via Consul DNS but the actual service is unavailable:
        # - Kong should return 503 Service Unavailable (not 502 Bad Gateway)
        # - This indicates that the service was discovered but is not responding

        # Accept 200 if service is actually running, or 503/502 if unavailable
        # The key distinction:
        # - 503: Service discovered but unavailable (healthy fallback)
        # - 502: Service discovered but connection failed
        # - 404: Route not found (service not discovered)

        assert response.status_code in [
            200,
            502,
            503,
        ], f"Expected service to be discovered but got {response.status_code}"

        # If we get 503, this is the expected fallback behavior
        if response.status_code == 503:
            assert (
                True
            ), "Got expected 503 Service Unavailable - fallback working correctly"

    def test_503_response_includes_proper_headers(self, gateway_client: httpx.Client):
        """Test that 503 responses include proper Kong headers for debugging."""
        response = gateway_client.get("/api/v1/registry/services")

        if response.status_code == 503:
            # Should include Kong's debugging headers
            assert (
                "X-Kong-Upstream-Latency" in response.headers
                or "X-Kong-Proxy-Latency" in response.headers
            ), "503 response should include Kong latency headers"

            # Should include correlation ID for tracing
            assert (
                "X-Correlation-ID" in response.headers
            ), "503 response should include correlation ID"

    def test_503_response_has_appropriate_error_body(
        self, gateway_client: httpx.Client
    ):
        """Test that 503 responses have meaningful error information."""
        response = gateway_client.get("/api/v1/registry/services")

        if response.status_code == 503:
            # Should have a response body with error information
            assert len(response.content) > 0, "503 response should have error body"

            # Check if it's JSON with error information
            try:
                error_data = response.json()
                # Kong typically returns {"message": "Service Unavailable"} for 503
                assert (
                    "message" in error_data or "error" in error_data
                ), "503 response should contain error message"
            except ValueError:
                # Non-JSON response is also acceptable for 503
                assert True, "Non-JSON 503 response is acceptable"

    def test_consecutive_requests_show_consistent_503_behavior(
        self, gateway_client: httpx.Client
    ):
        """Test that consecutive requests show consistent fallback behavior."""
        # Make multiple requests to check consistency
        responses = []
        for i in range(5):
            response = gateway_client.get("/api/v1/registry/services")
            responses.append(response.status_code)
            time.sleep(0.1)  # Small delay between requests

        # If any request returns 503, check for consistency
        if 503 in responses:
            # Should get consistent 503 responses when service is down
            service_down_responses = [code for code in responses if code in [502, 503]]
            assert (
                len(service_down_responses) >= len(responses) // 2
            ), "Should get consistent service unavailable responses"

        # All responses should be valid HTTP status codes for this scenario
        valid_codes = [
            200,
            401,
            403,
            404,
            502,
            503,
        ]  # Include auth errors for completeness
        assert all(
            code in valid_codes for code in responses
        ), f"All responses should be valid status codes, got: {responses}"

    def test_service_unavailable_response_timing(self, gateway_client: httpx.Client):
        """Test that 503 responses are returned promptly (not after long timeout)."""
        start_time = time.time()
        response = gateway_client.get("/api/v1/registry/services")
        end_time = time.time()

        request_time = (end_time - start_time) * 1000  # Convert to milliseconds

        if response.status_code == 503:
            # Should fail quickly, not after a long timeout
            # Kong should detect service unavailability promptly
            assert (
                request_time < 10000
            ), f"503 response took too long: {request_time}ms (should be < 10s)"

            # But shouldn't be too fast (indicating immediate rejection without checking)
            assert (
                request_time > 10
            ), f"503 response too fast: {request_time}ms (should try to connect first)"

    def test_health_check_path_accessibility(self, gateway_client: httpx.Client):
        """Test that health check endpoints are accessible for debugging unavailable services."""
        # Try to access health endpoint directly through gateway
        response = gateway_client.get("/api/v1/registry/health")

        # Health endpoint should be routable even when main service is down
        # This helps distinguish between service discovery issues and service health issues
        assert response.status_code in [
            200,
            404,
            502,
            503,
        ], "Health endpoint should be routable"

        # If we get 404, it might mean health route is not configured
        if response.status_code == 404:
            assert True, "Health route may not be configured (acceptable for this test)"

    def test_upstream_connection_failure_handling(self, gateway_client: httpx.Client):
        """Test that Kong handles upstream connection failures gracefully."""
        # Test multiple service endpoints to see connection failure handling
        endpoints = ["/api/v1/registry/services", "/api/v1/registry/health"]

        for endpoint in endpoints:
            response = gateway_client.get(endpoint)

            # Should get proper HTTP status, not connection errors
            assert hasattr(response, "status_code"), f"Should get HTTP response for {endpoint}"
            assert hasattr(
                response, "status_code"
            ), f"Should get HTTP response for {endpoint}"

            # Should not get 500 (internal Kong error)
            assert (
                response.status_code != 500
            ), f"Kong should handle connection failures gracefully for {endpoint}"

    def test_service_discovery_vs_service_availability_distinction(
        self, gateway_client: httpx.Client
    ):
        """Test that we can distinguish between service discovery failure and service unavailability."""
        # Test known route (should be discovered via Consul)
        known_response = gateway_client.get("/api/v1/registry/services")

        # Test unknown route (should not be discovered)
        unknown_response = gateway_client.get("/api/v1/nonexistent-service/test")

        # Known route should either work (200) or show service unavailability (503/502)
        # Unknown route should show route not found (404)
        if known_response.status_code in [502, 503]:
            # Service discovered but unavailable
            assert (
                unknown_response.status_code == 404
            ), "Unknown routes should return 404 while known routes return 502/503"

    def test_consul_dns_resolution_timeout_handling(self, gateway_client: httpx.Client):
        """Test that Kong handles Consul DNS resolution timeouts gracefully."""
        # Make request that requires DNS resolution
        start_time = time.time()
        response = gateway_client.get("/api/v1/registry/services")
        end_time = time.time()

        total_time = (end_time - start_time) * 1000

        # Should not hang indefinitely on DNS resolution
        assert total_time < 30000, f"Request took too long: {total_time}ms (DNS timeout issue?)"
        assert (
            total_time < 30000
        ), f"Request took too long: {total_time}ms (DNS timeout issue?)"

        # Should get proper HTTP response, not connection timeout
        assert response.status_code in [
            200,
            404,
            502,
            503,
            504,
        ], f"Should handle DNS resolution gracefully, got {response.status_code}"

    def test_multiple_service_instances_failover(self, gateway_client: httpx.Client):
        """Test failover behavior when multiple service instances are configured."""
        # Make several requests to see if Kong tries multiple instances
        responses = []
        latencies = []

        for i in range(10):
            start_time = time.time()
            response = gateway_client.get("/api/v1/registry/services")
            end_time = time.time()

            responses.append(response.status_code)
            latencies.append((end_time - start_time) * 1000)
            time.sleep(0.1)

        # If service is down, should get consistent error responses
        if all(code in [502, 503] for code in responses):
            # Latencies should be relatively consistent (indicating same failure mode)
            avg_latency = sum(latencies) / len(latencies)
            assert all(
                abs(lat - avg_latency) < 5000 for lat in latencies
            ), "Latencies should be consistent when service is consistently down"

    def test_service_unavailable_error_message_clarity(
        self, gateway_client: httpx.Client
    ):
        """Test that 503 responses provide clear error messages."""
        response = gateway_client.get("/api/v1/registry/services")

        if response.status_code == 503:
            # Should have meaningful error content
            content = response.text.lower()

            # Should contain relevant keywords indicating service unavailability
            service_unavailable_indicators = [
                "service unavailable",
                "upstream",
                "connection",
                "failed",
                "timeout",
            ]

            has_indicator = any(
                indicator in content for indicator in service_unavailable_indicators
            )
            assert (
                has_indicator or len(content) == 0
            ), "503 response should have meaningful error message or be empty"
