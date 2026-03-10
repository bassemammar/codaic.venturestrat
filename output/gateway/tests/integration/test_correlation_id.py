"""
Integration tests for correlation ID functionality.

Tests actual correlation ID generation, preservation, and echoing behavior
through the Kong gateway.
"""

import pytest
import uuid
import re


@pytest.mark.integration
class TestCorrelationIdGeneration:
    """Test correlation ID generation when not provided."""

    def test_generates_correlation_id_when_missing(self, gateway_client):
        """Test that gateway generates correlation ID when none provided."""
        # Make request without correlation ID header
        response = gateway_client.get("/health")

        assert response.status_code == 200
        assert (
            "X-Correlation-ID" in response.headers
        ), "Gateway should add correlation ID header"

        correlation_id = response.headers["X-Correlation-ID"]
        assert correlation_id is not None, "Correlation ID should not be None"
        assert len(correlation_id) > 0, "Correlation ID should not be empty"

    def test_generated_correlation_id_format(self, gateway_client):
        """Test that generated correlation ID follows UUID format."""
        response = gateway_client.get("/health")

        assert response.status_code == 200
        correlation_id = response.headers.get("X-Correlation-ID")
        assert correlation_id is not None, "Correlation ID should be present"

        # Should be UUID format: 8-4-4-4-12 hex digits
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )

        assert uuid_pattern.match(
            correlation_id
        ), f"Correlation ID '{correlation_id}' should be valid UUID format"

    def test_generated_correlation_id_uniqueness(self, gateway_client):
        """Test that multiple requests generate unique correlation IDs."""
        correlation_ids = set()
        num_requests = 10

        for _ in range(num_requests):
            response = gateway_client.get("/health")
            assert response.status_code == 200

            correlation_id = response.headers.get("X-Correlation-ID")
            assert correlation_id is not None, "Each request should have correlation ID"
            assert (
                correlation_id not in correlation_ids
            ), f"Correlation ID collision detected: {correlation_id}"

            correlation_ids.add(correlation_id)

        assert (
            len(correlation_ids) == num_requests
        ), "All correlation IDs should be unique"

    def test_correlation_id_generated_for_different_endpoints(self, gateway_client):
        """Test correlation ID generation across different endpoints."""
        endpoints = ["/health", "/api/v1/registry/services"]

        for endpoint in endpoints:
            response = gateway_client.get(endpoint)
            # Accept various status codes (service may be down)
            assert response.status_code in [200, 404, 502, 503]

            correlation_id = response.headers.get("X-Correlation-ID")
            assert correlation_id is not None, f"Correlation ID missing for {endpoint}"
            assert len(correlation_id) > 10, f"Correlation ID too short for {endpoint}"

    def test_correlation_id_generated_for_different_methods(self, gateway_client):
        """Test correlation ID generation for different HTTP methods."""
        methods_and_endpoints = [
            ("GET", "/health"),
            (
                "POST",
                "/api/v1/registry/services",
            ),  # May fail but should have correlation ID
            ("OPTIONS", "/health"),
        ]

        for method, endpoint in methods_and_endpoints:
            response = gateway_client.request(method, endpoint)
            # Accept various status codes
            assert response.status_code in [200, 201, 404, 405, 502, 503]

            correlation_id = response.headers.get("X-Correlation-ID")
            assert correlation_id is not None, f"Correlation ID missing for {method} {endpoint}"
            assert (
                correlation_id is not None
            ), f"Correlation ID missing for {method} {endpoint}"


@pytest.mark.integration
class TestCorrelationIdPreservation:
    """Test correlation ID preservation when provided in request."""

    def test_preserves_provided_correlation_id(self, gateway_client, correlation_id):
        """Test that gateway preserves correlation ID when provided."""
        response = gateway_client.get("/health", headers={"X-Correlation-ID": correlation_id})
        response = gateway_client.get(
            "/health", headers={"X-Correlation-ID": correlation_id}
        )

        assert response.status_code == 200
        returned_correlation_id = response.headers.get("X-Correlation-ID")
        assert (
            returned_correlation_id == correlation_id
        ), "Gateway should preserve provided correlation ID"

    def test_preserves_custom_correlation_id_formats(self, gateway_client):
        """Test preservation of various correlation ID formats."""
        test_correlation_ids = [
            "simple-123",
            "trace.span.456",
            "session_abc123_request_xyz789",
            "req:12345:user:67890",
            str(uuid.uuid4()),  # Standard UUID
            "custom-" + str(uuid.uuid4()),  # UUID with prefix
            "2024-01-04-request-12345",  # Date-based
            "user-johndoe-session-98765",  # Descriptive
        ]

        for test_id in test_correlation_ids:
            response = gateway_client.get("/health", headers={"X-Correlation-ID": test_id})
            response = gateway_client.get(
                "/health", headers={"X-Correlation-ID": test_id}
            )

            assert response.status_code == 200
            returned_id = response.headers.get("X-Correlation-ID")
            assert (
                returned_id == test_id
            ), f"Gateway should preserve correlation ID format: {test_id}"

    def test_preserves_correlation_id_across_different_endpoints(self, gateway_client):
        """Test that correlation ID preservation works across endpoints."""
        test_correlation_id = "test-endpoint-preservation-" + str(uuid.uuid4())[:8]
        endpoints = ["/health", "/api/v1/registry/services"]

        for endpoint in endpoints:
            response = gateway_client.get(
                endpoint, headers={"X-Correlation-ID": test_correlation_id}
            )

            # Accept various status codes
            assert response.status_code in [200, 404, 502, 503]

            returned_id = response.headers.get("X-Correlation-ID")
            assert (
                returned_id == test_correlation_id
            ), f"Correlation ID not preserved for {endpoint}"

    def test_correlation_id_case_sensitivity(self, gateway_client):
        """Test correlation ID header case sensitivity."""
        test_correlation_id = "test-case-sensitivity-123"

        # Test different header case variations
        header_variations = [
            "X-Correlation-ID",
            "x-correlation-id",
            "X-CORRELATION-ID",
            "x-Correlation-Id",
        ]

        for header_name in header_variations:
            response = gateway_client.get("/health", headers={header_name: test_correlation_id})
            response = gateway_client.get(
                "/health", headers={header_name: test_correlation_id}
            )

            assert response.status_code == 200

            # Kong should normalize to standard case
            returned_id = response.headers.get("X-Correlation-ID")
            if returned_id is not None:
                # If the header was recognized, it should preserve the value
                assert (
                    returned_id == test_correlation_id
                ), f"Correlation ID value not preserved with header: {header_name}"

    def test_correlation_id_with_special_characters(self, gateway_client):
        """Test correlation IDs with various special characters."""
        # Test reasonable special characters
        test_cases = [
            "trace-123_span-456",  # Hyphens and underscores
            "trace.service.operation.123",  # Dots
            "session:abc:request:123",  # Colons
            "user+session+12345",  # Plus signs
            "trace=123&span=456",  # Equals and ampersands (URL-encoded values)
        ]

        for test_id in test_cases:
            response = gateway_client.get("/health", headers={"X-Correlation-ID": test_id})
            response = gateway_client.get(
                "/health", headers={"X-Correlation-ID": test_id}
            )

            assert response.status_code == 200
            returned_id = response.headers.get("X-Correlation-ID")
            assert (
                returned_id == test_id
            ), f"Special characters not preserved in correlation ID: {test_id}"

    def test_correlation_id_length_limits(self, gateway_client):
        """Test correlation ID preservation with various lengths."""
        test_cases = [
            "a",  # Very short
            "short-id",  # Short
            str(uuid.uuid4()),  # Standard UUID length (36)
            "long-" + "x" * 100,  # Long ID
            "very-long-" + "y" * 200,  # Very long ID
        ]

        for test_id in test_cases:
            response = gateway_client.get("/health", headers={"X-Correlation-ID": test_id})
            response = gateway_client.get(
                "/health", headers={"X-Correlation-ID": test_id}
            )

            assert response.status_code == 200
            returned_id = response.headers.get("X-Correlation-ID")
            assert (
                returned_id == test_id
            ), f"Length not preserved for correlation ID: {test_id} (length: {len(test_id)})"


@pytest.mark.integration
class TestCorrelationIdEcho:
    """Test correlation ID echo behavior in responses."""

    def test_correlation_id_echoed_in_response(self, gateway_client):
        """Test that correlation ID is always echoed in response headers."""
        # Test both generated and provided correlation IDs
        test_cases = [
            None,  # Let gateway generate
            "user-provided-correlation-123",  # User provided
        ]

        for correlation_id in test_cases:
            headers = {}
            if correlation_id:
                headers["X-Correlation-ID"] = correlation_id

            response = gateway_client.get("/health", headers=headers)

            assert response.status_code == 200
            assert (
                "X-Correlation-ID" in response.headers
            ), "Response should always include X-Correlation-ID header"

            returned_id = response.headers["X-Correlation-ID"]
            assert returned_id is not None, "Correlation ID should not be None"
            assert len(returned_id) > 0, "Correlation ID should not be empty"

            if correlation_id:
                assert (
                    returned_id == correlation_id
                ), "Provided correlation ID should be echoed exactly"

    def test_correlation_id_echo_with_errors(self, gateway_client):
        """Test that correlation ID is echoed even with error responses."""
        test_correlation_id = "test-error-echo-" + str(uuid.uuid4())[:8]

        # Request to non-existent endpoint (should return 404)
        response = gateway_client.get(
            "/non-existent-endpoint", headers={"X-Correlation-ID": test_correlation_id}
        )

        assert response.status_code == 404
        assert (
            "X-Correlation-ID" in response.headers
        ), "Correlation ID should be echoed even with errors"

        returned_id = response.headers["X-Correlation-ID"]
        assert (
            returned_id == test_correlation_id
        ), "Correlation ID should be preserved in error responses"

    def test_correlation_id_echo_unauthorized_requests(self, unauthorized_client):
        """Test correlation ID echo for unauthorized requests."""
        test_correlation_id = "test-unauth-echo-" + str(uuid.uuid4())[:8]

        # Request without API key (should return 401)
        response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"X-Correlation-ID": test_correlation_id},
        )

        # Should be unauthorized but still echo correlation ID
        assert response.status_code == 401
        assert (
            "X-Correlation-ID" in response.headers
        ), "Correlation ID should be echoed for unauthorized requests"

        returned_id = response.headers["X-Correlation-ID"]
        assert (
            returned_id == test_correlation_id
        ), "Correlation ID should be preserved for unauthorized requests"

    def test_correlation_id_echo_different_content_types(self, gateway_client):
        """Test correlation ID echo for different response content types."""
        test_correlation_id = "test-content-type-" + str(uuid.uuid4())[:8]

        # Test different endpoints that may return different content types
        endpoints = [
            "/health",  # JSON response
            "/api/v1/registry/services",  # JSON or error
        ]

        for endpoint in endpoints:
            response = gateway_client.get(
                endpoint, headers={"X-Correlation-ID": test_correlation_id}
            )

            # Accept various status codes and content types
            assert response.status_code in [200, 404, 401, 502, 503]
            assert "X-Correlation-ID" in response.headers, f"Correlation ID missing for {endpoint}"
            assert (
                "X-Correlation-ID" in response.headers
            ), f"Correlation ID missing for {endpoint}"

            returned_id = response.headers["X-Correlation-ID"]
            assert (
                returned_id == test_correlation_id
            ), f"Correlation ID not preserved for {endpoint}"


@pytest.mark.integration
class TestCorrelationIdIntegration:
    """Test correlation ID integration with other gateway features."""

    def test_correlation_id_with_api_key_auth(self, gateway_client):
        """Test correlation ID works with API key authentication."""
        test_correlation_id = "test-auth-integration-" + str(uuid.uuid4())[:8]

        response = gateway_client.get(
            "/api/v1/registry/services",
            headers={"X-Correlation-ID": test_correlation_id},
        )

        # Should pass auth and include correlation ID
        assert response.status_code in [200, 502, 503]  # Service may be down
        assert "X-Correlation-ID" in response.headers

        returned_id = response.headers["X-Correlation-ID"]
        assert returned_id == test_correlation_id

    def test_correlation_id_with_rate_limiting(self, gateway_client):
        """Test correlation ID works with rate limiting headers."""
        test_correlation_id = "test-rate-limit-" + str(uuid.uuid4())[:8]

        response = gateway_client.get("/health", headers={"X-Correlation-ID": test_correlation_id})
        response = gateway_client.get(
            "/health", headers={"X-Correlation-ID": test_correlation_id}
        )

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers

        # Should also have rate limiting headers
        rate_limit_headers = [
            "X-RateLimit-Limit-Minute",
            "X-RateLimit-Remaining-Minute",
        ]

        for header in rate_limit_headers:
            if header in response.headers:
                # If rate limiting headers are present, correlation ID should still work
                returned_id = response.headers["X-Correlation-ID"]
                assert returned_id == test_correlation_id

    def test_correlation_id_with_kong_proxy_headers(self, gateway_client):
        """Test correlation ID coexists with Kong proxy headers."""
        test_correlation_id = "test-kong-headers-" + str(uuid.uuid4())[:8]

        response = gateway_client.get("/health", headers={"X-Correlation-ID": test_correlation_id})
        response = gateway_client.get(
            "/health", headers={"X-Correlation-ID": test_correlation_id}
        )

        assert response.status_code == 200

        # Should have correlation ID
        assert "X-Correlation-ID" in response.headers
        assert response.headers["X-Correlation-ID"] == test_correlation_id

        # Should also have Kong headers
        kong_headers = ["X-Kong-Upstream-Latency", "X-Kong-Proxy-Latency"]

        # At least one Kong header should be present
        kong_header_found = any(header in response.headers for header in kong_headers)
        if kong_header_found:
            # Kong headers present confirms request went through Kong
            # and correlation ID still worked
            assert response.headers["X-Correlation-ID"] == test_correlation_id

    def test_correlation_id_performance_impact(self, gateway_client):
        """Test that correlation ID doesn't significantly impact response time."""
        import time

        # Measure response time without correlation ID
        start_time = time.time()
        response_without = gateway_client.get("/health")
        time_without = time.time() - start_time

        assert response_without.status_code == 200

        # Measure response time with correlation ID
        test_correlation_id = "perf-test-" + str(uuid.uuid4())[:8]
        start_time = time.time()
        response_with = gateway_client.get(
            "/health", headers={"X-Correlation-ID": test_correlation_id}
        )
        time_with = time.time() - start_time

        assert response_with.status_code == 200
        assert response_with.headers["X-Correlation-ID"] == test_correlation_id

        # Correlation ID processing should not add significant latency
        # Allow for some variance in measurement, but flag if dramatically slower
        max_acceptable_overhead = max(0.1, time_without * 2)  # 100ms or 2x base time
        assert (
            time_with <= time_without + max_acceptable_overhead
        ), f"Correlation ID overhead too high: {time_with - time_without:.3f}s"
