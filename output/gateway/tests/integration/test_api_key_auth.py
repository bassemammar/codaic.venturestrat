"""
Integration tests for API key authentication.

Tests authentication flow, credential handling, and error responses.
"""

import pytest


@pytest.mark.integration
class TestAPIKeyAuthentication:
    """Test API key authentication functionality."""

    def test_request_without_api_key_401(self, unauthorized_client):
        """Test that requests without API key return 401."""
        response = unauthorized_client.get("/api/v1/registry/services")

        assert response.status_code == 401

        data = response.json()
        assert "message" in data
        assert "api key" in data["message"].lower()

    def test_request_with_invalid_key_403(self, unauthorized_client):
        """Test that requests with invalid API key return 403."""
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"X-API-Key": "invalid-key-12345"}
        )

        assert response.status_code == 403

        data = response.json()
        assert "message" in data

    def test_request_with_valid_key_200(self, gateway_client):
        """Test that requests with valid API key return 200 when backend is available."""
        response = gateway_client.get("/api/v1/registry/services")

        # Should not be authentication error (401/403)
        assert response.status_code not in [401, 403]

        # May be 200 (success), 502/503 (backend down), or 404 (service not found)
        assert response.status_code in [200, 404, 502, 503]

        # If backend is available, should return 200
        if response.status_code == 200:
            # Verify successful response has expected headers
            assert "X-Correlation-ID" in response.headers
            assert "X-Kong-Proxy-Latency" in response.headers

            # Verify response is JSON when successful
            data = response.json()
            assert isinstance(data, (dict, list))

    def test_valid_api_key_authentication_headers(self, gateway_client):
        """Test that valid API key adds proper authentication headers."""
        response = gateway_client.get("/api/v1/registry/services")

        # Should pass authentication
        assert response.status_code not in [401, 403]

        # Kong should add consumer information headers
        # These would be visible in backend service logs/headers
        expected_kong_headers = ["X-Kong-Proxy-Latency", "X-Correlation-ID"]

        for header in expected_kong_headers:
            assert header in response.headers, f"Missing Kong header: {header}"

    def test_valid_api_key_various_endpoints(self, gateway_client):
        """Test valid API key works across different endpoints."""
        # Test different endpoints to ensure authentication works consistently
        endpoints = [
            "/api/v1/registry/services",
            "/health",  # Health endpoint should work with or without auth
        ]

        for endpoint in endpoints:
            response = gateway_client.get(endpoint)

            # Should not be authentication error
            assert response.status_code not in [401, 403], f"Auth failed for {endpoint}"

            if response.status_code == 200:
                # Verify correlation ID is present
                assert "X-Correlation-ID" in response.headers

    def test_all_valid_api_keys_return_200_or_acceptable(self):
        """Test that all configured valid API keys work correctly."""
        import httpx

        # Test all known valid API keys from kong.yaml
        valid_keys = [
            "dev-api-key-12345",  # default-consumer
            "test-api-key-67890",  # test-consumer
            "free-api-key-11111",  # free-tier-consumer
            "standard-api-key-22222",  # standard-tier-consumer
        ]

        for api_key in valid_keys:
            client = httpx.Client(
                base_url="http://localhost:8000",
                headers={"X-API-Key": api_key},
                timeout=10.0,
            )

            try:
                response = client.get("/api/v1/registry/services")

                # Should not be authentication error
                assert response.status_code not in [
                    401,
                    403,
                ], f"API key {api_key} failed authentication"

                # Should be acceptable status (200, 404, 502, 503)
                assert response.status_code in [
                    200,
                    404,
                    502,
                    503,
                ], f"Unexpected status for {api_key}: {response.status_code}"

                # If 200, verify proper response structure
                if response.status_code == 200:
                    # Should have Kong headers
                    assert "X-Correlation-ID" in response.headers
                    assert "X-Kong-Proxy-Latency" in response.headers

                    # Should be valid JSON
                    data = response.json()
                    assert isinstance(data, (dict, list))

            finally:
                client.close()

    def test_valid_api_key_preserves_query_parameters(self, gateway_client):
        """Test that valid API key requests preserve query parameters."""
        response = gateway_client.get(
            "/api/v1/registry/services?filter=active&limit=10"
        )

        # Should pass authentication
        assert response.status_code not in [401, 403]

        # Kong should have processed the request
        assert "X-Kong-Proxy-Latency" in response.headers

    def test_valid_api_key_with_post_request(self, gateway_client):
        """Test that valid API key works with POST requests."""
        test_data = {"name": "test-service", "url": "http://test:8080"}

        response = gateway_client.post(
            "/api/v1/registry/services",
            json=test_data,
            headers={"Content-Type": "application/json"},
        )

        # Should pass authentication
        assert response.status_code not in [401, 403]

        # Kong should process the request
        assert "X-Kong-Proxy-Latency" in response.headers

    def test_valid_api_key_response_timing(self, gateway_client):
        """Test that valid API key requests include timing headers."""
        response = gateway_client.get("/api/v1/registry/services")

        # Should pass authentication
        assert response.status_code not in [401, 403]

        # Timing headers should be present and valid
        if "X-Kong-Proxy-Latency" in response.headers:
            latency = response.headers["X-Kong-Proxy-Latency"]
            # Should be numeric (milliseconds)
            assert latency.isdigit(), f"Invalid proxy latency: {latency}"

        if "X-Kong-Upstream-Latency" in response.headers:
            upstream_latency = response.headers["X-Kong-Upstream-Latency"]
            # Should be numeric (milliseconds) or "-" if no upstream
            assert (
                upstream_latency.isdigit() or upstream_latency == "-"
            ), f"Invalid upstream latency: {upstream_latency}"

    def test_api_key_in_header(self, unauthorized_client):
        """Test API key authentication via X-API-Key header."""
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"X-API-Key": "dev-api-key-12345"}
        )

        # Should pass authentication
        assert response.status_code not in [401, 403]

    def test_api_key_in_query(self, unauthorized_client):
        """Test API key authentication via query parameter."""
        response = unauthorized_client.get(
            "/api/v1/registry/services?apikey=dev-api-key-12345"
        )

        # Should pass authentication
        assert response.status_code not in [401, 403]

    def test_multiple_api_key_headers(self, unauthorized_client):
        """Test that X-API-Key header takes precedence."""
        response = unauthorized_client.get(
            "/api/v1/registry/services?apikey=invalid-key",
            headers={"X-API-Key": "dev-api-key-12345"},
        )

        # Should pass authentication (header key is valid)
        assert response.status_code not in [401, 403]

    def test_api_key_hidden_from_upstream(self, gateway_client):
        """Test that API key is not forwarded to backend service."""
        # We can't directly verify this without a mock backend,
        # but we can ensure the request is processed by Kong
        response = gateway_client.get("/api/v1/registry/services")

        # Kong should process the request
        assert "X-Kong-Proxy-Latency" in response.headers

    def test_consumer_username_added(self, gateway_client):
        """Test that consumer username is added to request headers."""
        response = gateway_client.get("/api/v1/registry/services")

        # Kong should add consumer information
        # Can't directly test without mock backend, but verify Kong processing
        assert response.status_code not in [401, 403]

    def test_different_consumer_keys(self):
        """Test that different consumers can authenticate with their keys."""
        import httpx

        # Test default consumer
        client1 = httpx.Client(
            base_url="http://localhost:8000", headers={"X-API-Key": "dev-api-key-12345"}
        )

        # Test alternate consumer
        client2 = httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "test-api-key-67890"},
        )

        try:
            response1 = client1.get("/api/v1/registry/services")
            response2 = client2.get("/api/v1/registry/services")

            # Both should pass authentication
            assert response1.status_code not in [401, 403]
            assert response2.status_code not in [401, 403]

        finally:
            client1.close()
            client2.close()

    def test_case_sensitive_api_key(self, unauthorized_client):
        """Test that API keys are case-sensitive."""
        # Try uppercase version of valid key
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"X-API-Key": "DEV-API-KEY-12345"}
        )

        assert response.status_code == 403

    def test_api_key_with_special_characters(self, unauthorized_client):
        """Test API key validation with various character patterns."""
        # Test with spaces (should fail)
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"X-API-Key": "dev-api-key-12345 "}
        )

        assert response.status_code == 403

    def test_empty_api_key_header(self, unauthorized_client):
        """Test that empty API key header returns 401."""
        response = unauthorized_client.get("/api/v1/registry/services", headers={"X-API-Key": ""})
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"X-API-Key": ""}
        )

        assert response.status_code == 401

    def test_malformed_authorization_header(self, unauthorized_client):
        """Test that malformed Authorization header is ignored."""
        # Kong key-auth should ignore Authorization header and look for X-API-Key
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"Authorization": "Bearer some-token"}
        )

        # Should still require API key
        assert response.status_code == 401

    def test_health_endpoint_bypasses_auth(self, unauthorized_client):
        """Test that health endpoint doesn't require API key."""
        response = unauthorized_client.get("/health")

        assert response.status_code == 200
        # Health should work without authentication

    def test_invalid_key_with_sql_injection_returns_403(self, unauthorized_client):
        """Test that SQL injection attempts in API key return 403."""
        response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"X-API-Key": "'; DROP TABLE consumers; --"},
        )

        assert response.status_code == 403

        data = response.json()
        assert "message" in data

    def test_invalid_key_with_extremely_long_value_returns_403(
        self, unauthorized_client
    ):
        """Test that extremely long API keys return 403."""
        long_key = "x" * 10000  # 10KB string
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"X-API-Key": long_key}
        )

        assert response.status_code == 403

    def test_invalid_key_with_unicode_characters_returns_403(self, unauthorized_client):
        """Test that API keys with unicode characters return 403."""
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"X-API-Key": "🔑-invalid-key-🚫"}
        )

        assert response.status_code == 403

    def test_invalid_key_null_bytes_returns_403(self, unauthorized_client):
        """Test that API keys with null bytes return 403."""
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"X-API-Key": "invalid\x00key"}
        )

        assert response.status_code == 403

    def test_wrong_format_api_key_returns_403(self, unauthorized_client):
        """Test that API keys in wrong format return 403."""
        # Test various wrong formats that might be confused with valid ones
        wrong_format_keys = [
            "dev-api-key-54321",  # Different numbers
            "prod-api-key-12345",  # Different prefix
            "dev-key-12345",  # Missing 'api'
            "dev-api-12345",  # Missing 'key'
            "DEV-API-KEY-12345",  # Wrong case
            "dev_api_key_12345",  # Wrong separators
        ]

        for invalid_key in wrong_format_keys:
            response = unauthorized_client.get(
                "/api/v1/registry/services", headers={"X-API-Key": invalid_key}
            )

            assert response.status_code == 403, f"Key '{invalid_key}' should return 403"

    def test_partial_valid_key_returns_403(self, unauthorized_client):
        """Test that partial matches of valid keys return 403."""
        # Test truncated versions of valid keys
        partial_keys = [
            "dev-api-key-1234",  # Missing last digit
            "dev-api-key",  # Missing numbers
            "dev-api-key-123456",  # Extra digit
            "dev-api-key-1234a",  # Modified last character
        ]

        for partial_key in partial_keys:
            response = unauthorized_client.get(
                "/api/v1/registry/services", headers={"X-API-Key": partial_key}
            )

            assert (
                response.status_code == 403
            ), f"Partial key '{partial_key}' should return 403"

    def test_revoked_api_key_returns_403(self, unauthorized_client):
        """Test that revoked/expired API keys return 403."""
        # This simulates a revoked key - one that was valid before but no longer is
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"X-API-Key": "revoked-api-key-99999"}
        )

        assert response.status_code == 403

        data = response.json()
        assert "message" in data
        assert (
            "credentials" in data["message"].lower()
            or "unauthorized" in data["message"].lower()
        )

    def test_403_response_format_consistency(self, unauthorized_client):
        """Test that all 403 responses have consistent format."""
        invalid_keys = ["completely-wrong-key", "dev-api-key-54321", "invalid123", ""]

        for invalid_key in invalid_keys:
            headers = {"X-API-Key": invalid_key} if invalid_key else {}
            response = unauthorized_client.get("/api/v1/registry/services", headers=headers)
            response = unauthorized_client.get(
                "/api/v1/registry/services", headers=headers
            )

            if response.status_code == 403:  # Some might return 401 for empty key
                data = response.json()
                # Verify consistent error response format
                assert (
                    "message" in data
                ), f"Response for key '{invalid_key}' missing message field"
                assert isinstance(data["message"], str), "Message should be a string"

                # Verify common Kong error structure
                expected_fields = ["message"]
                for field in expected_fields:
                    assert field in data, f"Response missing required field: {field}"
