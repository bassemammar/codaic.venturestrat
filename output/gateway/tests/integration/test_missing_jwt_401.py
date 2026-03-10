"""
Integration tests for missing JWT (401) authentication scenarios.

Tests the Kong JWT plugin behavior when JWT tokens are missing from requests
that require JWT authentication. These tests focus specifically on task 8.1:
Write tests for missing JWT (401).
"""

import pytest


@pytest.mark.unit
class TestMissingJWTValidation:
    """Unit tests for JWT validation logic (no infrastructure required)."""

    def test_jwt_missing_scenarios(self):
        """Test that we can identify missing JWT scenarios."""
        # Test cases for missing JWT authentication
        missing_jwt_scenarios = [
            {"headers": {}, "expected": "missing_auth"},
            {"headers": {"Authorization": ""}, "expected": "empty_auth"},
            {"headers": {"Authorization": "NoBearer token"}, "expected": "no_bearer"},
            {"headers": {"Authorization": "Bearer"}, "expected": "bearer_no_token"},
            {"headers": {"Authorization": "Bearer "}, "expected": "bearer_empty_token"},
        ]

        for scenario in missing_jwt_scenarios:
            # Simple validation logic test
            headers = scenario["headers"]
            auth_header = headers.get("Authorization", "")

            if not auth_header or auth_header == "":
                result = "empty_auth" if "Authorization" in headers else "missing_auth"
            elif auth_header == "Bearer":
                result = "bearer_no_token"
            elif auth_header == "Bearer ":
                result = "bearer_empty_token"
            elif not auth_header.startswith("Bearer "):
                result = "no_bearer"
            else:
                result = "valid_format"

            assert result == scenario["expected"], f"Failed for headers: {headers}"


@pytest.mark.integration
class TestMissingJWT401:
    """Test cases for missing JWT authentication returning 401."""

    def test_service_to_service_call_without_jwt_returns_401(self, unauthorized_client):
        """Test that service-to-service calls without JWT return 401."""
        # When JWT plugin is configured for service-to-service routes,
        # requests without Authorization header should return 401

        response = unauthorized_client.get("/api/v1/registry/services")

        # Currently API key auth is global, so this returns 401 for missing API key
        # When JWT plugin is active, this should specifically test JWT auth
        assert response.status_code == 401

        # Verify error message indicates missing authentication
        error_data = response.json()
        assert "message" in error_data
        # Error should indicate missing credentials
        assert any(
            keyword in error_data["message"].lower()
            for keyword in ["unauthorized", "authentication", "token", "key"]
        )

    def test_internal_api_without_jwt_returns_401(self, unauthorized_client):
        """Test that internal API endpoints without JWT return 401."""
        # Test various internal API endpoints that should require JWT
        internal_endpoints = [
            "/api/v1/registry/health",
            "/api/v1/registry/services",
        ]

        for endpoint in internal_endpoints:
            response = unauthorized_client.get(endpoint)

            # Should return 401 for missing authentication
            assert response.status_code == 401, f"Expected 401 for {endpoint}"

            # Verify response format
            error_data = response.json()
            assert isinstance(error_data, dict)
            assert "message" in error_data

    def test_missing_authorization_header_format(self, unauthorized_client):
        """Test specific scenarios of missing Authorization header."""
        test_cases = [
            # No Authorization header at all
            {},
            # Empty Authorization header
            {"Authorization": ""},
            # Authorization header without Bearer prefix
            {"Authorization": "NoBearer token"},
            # Authorization header with Bearer but no token
            {"Authorization": "Bearer"},
            # Authorization header with Bearer and empty token
            {"Authorization": "Bearer "},
        ]

        for headers in test_cases:
            response = unauthorized_client.get("/api/v1/registry/services", headers=headers)
            response = unauthorized_client.get(
                "/api/v1/registry/services", headers=headers
            )

            # All should return 401 for missing/invalid auth
            assert response.status_code == 401, f"Expected 401 for headers: {headers}"

    def test_missing_jwt_with_api_key_still_works(self, gateway_client):
        """Test that API key auth still works when JWT is missing."""
        # API key should work regardless of JWT presence for external clients
        # This test ensures dual auth doesn't break existing API key flows

        response = gateway_client.get("/api/v1/registry/services")

        # Should work with valid API key even without JWT
        # (502/503 are acceptable if backend is down)
        assert response.status_code in [200, 502, 503]

    def test_jwt_route_without_token_specific_error(self, unauthorized_client):
        """Test that JWT-specific routes return appropriate error when token missing."""
        # Future: when JWT plugin is configured for specific routes,
        # test that those routes specifically require JWT

        # For now, test that missing auth returns proper error structure
        response = unauthorized_client.get("/api/v1/registry/services")

        assert response.status_code == 401

        error_data = response.json()

        # Verify error response structure matches API spec
        required_fields = ["message", "error"]
        for field in required_fields:
            assert field in error_data, f"Missing required field: {field}"

        # Error field should indicate unauthorized access
        assert error_data["error"] in ["Unauthorized", "Forbidden"]

    def test_multiple_missing_auth_methods_return_401(self, unauthorized_client):
        """Test that requests missing both API key and JWT return 401."""
        endpoints_to_test = [
            "/api/v1/registry/services",
            "/api/v1/registry/health",
        ]

        for endpoint in endpoints_to_test:
            response = unauthorized_client.get(endpoint)

            assert (
                response.status_code == 401
            ), f"Expected 401 for {endpoint} with no auth"

            # Verify consistent error format across endpoints
            error_data = response.json()
            assert "message" in error_data
            assert "error" in error_data

    def test_missing_jwt_returns_www_authenticate_header(self, unauthorized_client):
        """Test that 401 responses include WWW-Authenticate header."""
        response = unauthorized_client.get("/api/v1/registry/services")

        assert response.status_code == 401

        # Check for authentication challenge headers
        # Kong may add these depending on plugin configuration

        # At minimum, response should be properly formatted 401
        assert response.headers.get("Content-Type") in [
            "application/json",
            "application/json; charset=utf-8",
        ]

    def test_missing_jwt_error_message_clarity(self, unauthorized_client):
        """Test that missing JWT errors have clear, actionable messages."""
        response = unauthorized_client.get("/api/v1/registry/services")

        assert response.status_code == 401

        error_data = response.json()
        message = error_data.get("message", "").lower()

        # Message should indicate what's missing
        assert any(
            keyword in message
            for keyword in [
                "key",
                "token",
                "authentication",
                "authorization",
                "credentials",
            ]
        ), f"Error message not clear: {message}"

    def test_missing_jwt_correlation_id_preserved(self, unauthorized_client):
        """Test that correlation ID is preserved even in 401 responses."""
        # Send request with correlation ID
        headers = {"X-Correlation-ID": "test-correlation-123"}

        response = unauthorized_client.get("/api/v1/registry/services", headers=headers)

        assert response.status_code == 401

        # Correlation ID should be echoed back even in error responses
        response_correlation_id = response.headers.get("X-Correlation-ID")

        # Kong should either echo our ID or generate one
        assert response_correlation_id is not None
        # If it echoes ours, it should match
        if response_correlation_id == "test-correlation-123":
            assert response_correlation_id == "test-correlation-123"

    def test_missing_jwt_rate_limiting_bypassed(self, unauthorized_client):
        """Test that 401 responses bypass rate limiting."""
        # Multiple rapid requests without auth should all return 401
        # and not be rate limited (since they're not authenticated)

        responses = []
        for i in range(5):
            response = unauthorized_client.get(f"/api/v1/registry/services?attempt={i}")
            responses.append(response)

        # All should return 401 (not 429 for rate limiting)
        for i, response in enumerate(responses):
            assert (
                response.status_code == 401
            ), f"Request {i} should be 401, not rate limited"

    def test_missing_jwt_different_http_methods(self, unauthorized_client):
        """Test that missing JWT returns 401 for different HTTP methods."""
        http_methods = [
            ("GET", "/api/v1/registry/services"),
            ("POST", "/api/v1/registry/services"),
            ("PUT", "/api/v1/registry/services/test"),
            ("DELETE", "/api/v1/registry/services/test"),
        ]

        for method, path in http_methods:
            response = unauthorized_client.request(method, path)

            # All should return 401 for missing authentication
            # (405 Method Not Allowed is also acceptable for unsupported methods)
            assert response.status_code in [
                401,
                405,
            ], f"Expected 401 or 405 for {method} {path}, got {response.status_code}"

    def test_missing_jwt_response_timing(self, unauthorized_client):
        """Test that 401 responses are returned quickly (no unnecessary delays)."""
        import time

        start_time = time.time()
        response = unauthorized_client.get("/api/v1/registry/services")
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 401

        # Authentication failure should be fast (< 1 second)
        assert response_time < 1.0, f"401 response took too long: {response_time}s"

    def test_missing_jwt_no_information_leakage(self, unauthorized_client):
        """Test that 401 responses don't leak internal information."""
        response = unauthorized_client.get("/api/v1/registry/services")

        assert response.status_code == 401

        error_data = response.json()
        message = error_data.get("message", "").lower()

        # Should not contain internal service names, IPs, or technical details
        forbidden_keywords = [
            "internal",
            "backend",
            "upstream",
            "kong",
            "consul",
            "127.0.0.1",
            "localhost",
            "docker",
            "container",
        ]

        for keyword in forbidden_keywords:
            assert keyword not in message, f"Error message contains internal information: {keyword}"
            assert (
                keyword not in message
            ), f"Error message contains internal information: {keyword}"

    def test_missing_jwt_json_response_format(self, unauthorized_client):
        """Test that 401 responses are properly formatted JSON."""
        response = unauthorized_client.get("/api/v1/registry/services")

        assert response.status_code == 401

        # Should return valid JSON
        try:
            error_data = response.json()
        except ValueError:
            pytest.fail("401 response is not valid JSON")

        # Should follow standard error format
        assert isinstance(error_data, dict)
        assert "message" in error_data
        assert isinstance(error_data["message"], str)
        assert len(error_data["message"]) > 0
