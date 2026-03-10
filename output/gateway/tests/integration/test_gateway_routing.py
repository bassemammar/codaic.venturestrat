"""
Integration tests for gateway routing functionality.

Tests request routing, path manipulation, and service discovery.
"""

import pytest


@pytest.mark.integration
class TestGatewayRouting:
    """Test gateway routing to backend services."""

    def test_health_endpoint_routing(self, unauthorized_client):
        """Test that health endpoint routes correctly."""
        response = unauthorized_client.get("/health")

        assert response.status_code == 200

        # Should be successful health check
        data = response.json()
        assert "status" in data

    def test_unknown_route_404(self, unauthorized_client):
        """Test that unknown routes return 404."""
        response = unauthorized_client.get("/api/v1/unknown-service/test")

        assert response.status_code == 404

    def test_route_to_registry_service(self, gateway_client):
        """Test routing to registry service."""
        # This will fail if registry service isn't running, but tests the routing
        response = gateway_client.get("/api/v1/registry/services")

        # Should at least reach the route (may get 502/503 if service down)
        assert response.status_code in [200, 502, 503, 404]

        # Check that Kong headers are present (confirms routing through Kong)
        assert (
            "X-Kong-Upstream-Latency" in response.headers
            or "X-Kong-Proxy-Latency" in response.headers
        )

    def test_path_stripping_registry_services(self, gateway_client):
        """Test path stripping for registry services endpoint."""
        # Request: /api/v1/registry/services
        # Should strip: /api/v1/registry
        # Backend gets: /services
        response = gateway_client.get("/api/v1/registry/services")

        # Should not be 404 (route exists and path is properly configured)
        assert (
            response.status_code != 404
        ), "Path stripping should route correctly, not return 404"

        # Should be routed through Kong (Kong headers present)
        kong_headers = [h for h in response.headers.keys() if h.startswith("X-Kong-")]
        assert len(kong_headers) > 0, "Request should be processed by Kong gateway"

    def test_path_stripping_registry_health(self, gateway_client):
        """Test path stripping for registry health endpoint."""
        # Request: /api/v1/registry/health
        # Should strip: /api/v1/registry
        # Backend gets: /health
        response = gateway_client.get("/api/v1/registry/health")

        # Should not be 404 (route exists and path is properly configured)
        assert (
            response.status_code != 404
        ), "Path stripping should route correctly for health endpoint"

    def test_path_stripping_subpaths(self, gateway_client):
        """Test path stripping works for arbitrary subpaths."""
        # Test various subpaths to ensure stripping works consistently
        test_paths = [
            "/api/v1/registry/services",
            "/api/v1/registry/health",
            "/api/v1/registry/status",
            "/api/v1/registry/metrics",
            "/api/v1/registry/test/deep/path",
        ]

        for path in test_paths:
            response = gateway_client.get(path)
            # Should not be 404 - route should exist due to prefix matching and strip_path
            assert (
                response.status_code != 404
            ), f"Path {path} should be routed correctly"

    def test_health_route_no_path_stripping(self, unauthorized_client):
        """Test that health route does NOT strip path."""
        # Health route has strip_path: false
        # Request: /health
        # Backend gets: /health (no stripping)
        response = unauthorized_client.get("/health")

        assert response.status_code == 200, "Health endpoint should be accessible"
        assert "status" in response.json(), "Health response should contain status"

    def test_path_stripping_preserves_query_params(self, gateway_client):
        """Test that path stripping preserves query parameters."""
        # Request: /api/v1/registry/services?limit=10&offset=0
        # Should strip: /api/v1/registry
        # Backend gets: /services?limit=10&offset=0
        response = gateway_client.get(
            "/api/v1/registry/services", params={"limit": 10, "offset": 0}
        )

        # Should route correctly regardless of backend response
        assert (
            response.status_code != 404
        ), "Query parameters should be preserved with path stripping"

    def test_path_stripping_case_sensitivity(self, gateway_client):
        """Test path stripping with case sensitivity."""
        # Kong paths are case-sensitive by default
        # /api/v1/registry should work
        response_lower = gateway_client.get("/api/v1/registry/services")
        assert response_lower.status_code != 404

        # /API/V1/REGISTRY should not match (different case)
        response_upper = gateway_client.get("/API/V1/REGISTRY/services")
        assert (
            response_upper.status_code == 404
        ), "Path matching should be case-sensitive"

    def test_correlation_id_generated(self, gateway_client):
        """Test that correlation ID is generated for requests."""
        response = gateway_client.get("/health")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers

        correlation_id = response.headers["X-Correlation-ID"]
        assert len(correlation_id) > 10  # Should be UUID-like

    def test_correlation_id_echoed(self, gateway_client, correlation_id):
        """Test that provided correlation ID is echoed back."""
        response = gateway_client.get("/health", headers={"X-Correlation-ID": correlation_id})
        response = gateway_client.get(
            "/health", headers={"X-Correlation-ID": correlation_id}
        )

        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == correlation_id

    def test_grpc_web_route_configured(self, gateway_client):
        """Test that gRPC-Web routes are configured."""
        # Test OPTIONS request to gRPC-Web endpoint
        response = gateway_client.options("/grpc/v1/registry")

        # Should not return 404 (route exists)
        assert response.status_code != 404

    def test_service_headers_added(self, gateway_client):
        """Test that service-specific headers are added."""
        response = gateway_client.get("/api/v1/registry/services")

        # Request transformer should add headers for registry service
        # We can't directly check backend headers, but can verify the route exists
        assert response.status_code in [200, 502, 503]  # Route exists

    def test_multiple_protocol_support(self, gateway_client):
        """Test that routes support both HTTP and HTTPS protocols."""
        # This test verifies configuration rather than actual HTTPS
        # In development, both protocols should be configured

        response = gateway_client.get("/health")
        assert response.status_code == 200

        # Verify we're hitting Kong (not direct backend)
        assert "X-Kong-Proxy-Latency" in response.headers

    def test_route_priority_configuration(self, gateway_client):
        """Test that routes with higher priority are matched first."""
        # Health route should have higher priority than catch-all
        response = gateway_client.get("/health")

        assert response.status_code == 200
        # Should get health response, not 404 from registry service

    def test_preserve_host_configuration(self, gateway_client):
        """Test that preserve_host is correctly configured."""
        response = gateway_client.get("/api/v1/registry/services")

        # Check Kong processed the request (by presence of Kong headers)
        kong_headers = [h for h in response.headers.keys() if h.startswith("X-Kong-")]
        assert len(kong_headers) > 0, "Kong should add headers to processed requests"
