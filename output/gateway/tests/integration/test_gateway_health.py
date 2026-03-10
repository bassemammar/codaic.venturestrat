"""
Integration tests for gateway health and basic functionality.

These tests require the gateway stack to be running.
"""

import pytest


@pytest.mark.integration
class TestGatewayHealth:
    """Test gateway health and basic connectivity."""

    def test_gateway_health_endpoint(self, unauthorized_client):
        """Test gateway health check endpoint."""
        response = unauthorized_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify response format matches API specification
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"

        # Verify timestamp format (ISO 8601)
        timestamp = data["timestamp"]
        assert timestamp.endswith("Z")  # Should be in UTC
        assert len(timestamp) >= 20  # Basic length check for ISO format

        # Should be recent (within 30 seconds)
        from datetime import datetime
        import dateutil.parser

        parsed_timestamp = dateutil.parser.parse(timestamp)
        now = datetime.now(parsed_timestamp.tzinfo)
        time_diff = abs((now - parsed_timestamp).total_seconds())
        assert time_diff < 30  # Should be very recent

    def test_admin_api_accessible(self, admin_client):
        """Test Kong Admin API is accessible."""
        response = admin_client.get("/status")

        assert response.status_code == 200
        data = response.json()

        assert "database" in data
        assert "server" in data

    def test_jwt_issuer_health(self, jwt_issuer_client):
        """Test JWT issuer service health."""
        response = jwt_issuer_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_unknown_route_returns_404(self, unauthorized_client):
        """Test that unknown routes return 404."""
        response = unauthorized_client.get("/nonexistent-route")

        assert response.status_code == 404

    def test_correlation_id_generated(self, gateway_client):
        """Test that correlation ID is generated and returned."""
        response = gateway_client.get("/health")

        # Kong should add correlation ID header
        assert "X-Correlation-ID" in response.headers

        correlation_id = response.headers["X-Correlation-ID"]
        assert correlation_id
        assert len(correlation_id) > 10  # Should be a UUID or similar

    def test_correlation_id_echoed(self, gateway_client, correlation_id):
        """Test that provided correlation ID is echoed back."""
        response = gateway_client.get("/health", headers={"X-Correlation-ID": correlation_id})
        response = gateway_client.get(
            "/health", headers={"X-Correlation-ID": correlation_id}
        )

        assert response.headers.get("X-Correlation-ID") == correlation_id

    def test_gateway_performance_headers(self, gateway_client):
        """Test that Kong adds performance headers."""
        response = gateway_client.get("/health")

        # Kong should add latency headers
        assert "X-Kong-Upstream-Latency" in response.headers
        assert "X-Kong-Proxy-Latency" in response.headers

        # Values should be numeric (milliseconds)
        upstream_latency = response.headers["X-Kong-Upstream-Latency"]
        proxy_latency = response.headers["X-Kong-Proxy-Latency"]

        assert upstream_latency.isdigit()
        assert proxy_latency.isdigit()

    def test_cors_headers_present(self, gateway_client):
        """Test that CORS headers are added."""
        response = gateway_client.options("/health")

        # Should include CORS headers for OPTIONS request
        assert response.status_code in [200, 204]

    def test_rate_limit_headers_present(self, gateway_client):
        """Test that rate limiting headers are added."""
        response = gateway_client.get("/health")

        assert response.status_code == 200

        # Rate limit headers should be present
        assert "X-RateLimit-Limit-Minute" in response.headers
        assert "X-RateLimit-Remaining-Minute" in response.headers

        # Values should be numeric
        limit = response.headers["X-RateLimit-Limit-Minute"]
        remaining = response.headers["X-RateLimit-Remaining-Minute"]

        assert limit.isdigit()
        assert remaining.isdigit()
        assert int(limit) > 0
        assert 0 <= int(remaining) <= int(limit)

    def test_prometheus_metrics_endpoint(self, admin_client):
        """Test that Prometheus metrics are available."""
        response = admin_client.get("/metrics")

        assert response.status_code == 200
        content = response.text

        # Should contain Kong metrics
        assert "kong_http_requests_total" in content
        assert "kong_latency_ms" in content

    @pytest.mark.slow
    def test_gateway_concurrent_requests(self, gateway_client):
        """Test gateway handles concurrent requests correctly."""
        import asyncio
        import httpx

        async def make_request():
            async with httpx.AsyncClient(
                base_url=gateway_client.base_url, headers=gateway_client.headers
            ) as client:
                return await client.get("/health")

        async def test_concurrent():
            # Make 10 concurrent requests
            tasks = [make_request() for _ in range(10)]
            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200

            # Each should have a unique correlation ID
            correlation_ids = [response.headers.get("X-Correlation-ID") for response in responses]
            correlation_ids = [
                response.headers.get("X-Correlation-ID") for response in responses
            ]
            assert len(set(correlation_ids)) == 10  # All unique

        # Run the async test
        asyncio.run(test_concurrent())
