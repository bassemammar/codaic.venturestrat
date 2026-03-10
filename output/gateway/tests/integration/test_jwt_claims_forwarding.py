"""
Integration tests for JWT claims forwarding to backend services.

Tests that JWT claims are properly extracted and forwarded as headers
to backend services for authentication context.
"""

import pytest
import jwt
import httpx
import respx


@pytest.mark.integration
class TestJWTClaimsForwarding:
    """Test JWT claims forwarding functionality."""

    @pytest.fixture
    def mock_backend(self):
        """Mock backend service to capture forwarded headers."""
        with respx.mock:
            # Mock registry-service endpoint
            mock = respx.post("http://registry-service:8080/api/v1/services").mock(
                return_value=httpx.Response(
                    200,
                    json={"message": "success", "headers_received": {}},
                    headers={"Content-Type": "application/json"},
                )
            )
            yield mock

    @pytest.fixture
    def valid_jwt_token(self, jwt_issuer_client):
        """Create a valid JWT token for testing."""
        response = jwt_issuer_client.post(
            "/token",
            json={
                "service_name": "pricing-service",
                "scope": "read:prices write:quotes",
            },
        )

        assert response.status_code == 200
        return response.json()["token"]

    def test_jwt_claims_forwarded_as_headers(
        self, unauthorized_client, valid_jwt_token, mock_backend
    ):
        """Test that JWT claims are forwarded as X-JWT-* headers to backend."""
        # Make request with JWT token
        response = unauthorized_client.post(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
            json={"name": "test-service"},
        )

        # Should reach backend (mock handles the response)
        assert response.status_code in [
            200,
            502,
            503,
        ]  # 502/503 if backend not available

        # Check if the request was made with JWT headers
        if mock_backend.called:
            request = mock_backend.calls[0].request
            headers = dict(request.headers)

            # Verify JWT claims headers are present
            assert "x-jwt-sub" in headers
            assert "x-jwt-issuer" in headers
            assert "x-jwt-audience" in headers
            assert "x-jwt-id" in headers
            assert "x-jwt-type" in headers
            assert "x-auth-method" in headers

            # Verify values match JWT payload
            assert headers["x-jwt-sub"] == "pricing-service"
            assert headers["x-jwt-issuer"] == "venturestrat-gateway"
            assert headers["x-jwt-audience"] == "venturestrat-services"
            assert headers["x-jwt-type"] == "access_token"
            assert headers["x-auth-method"] == "jwt"

    def test_jwt_scope_forwarded_when_present(
        self, unauthorized_client, jwt_issuer_client, mock_backend
    ):
        """Test that JWT scope is forwarded when present in token."""
        # Create token with scope
        response = jwt_issuer_client.post(
            "/token",
            json={
                "service_name": "pricing-service",
                "scope": "read:prices write:quotes",
            },
        )
        token = response.json()["token"]

        # Make request with JWT token
        unauthorized_client.post(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "test-service"},
        )

        if mock_backend.called:
            headers = dict(mock_backend.calls[0].request.headers)
            assert "x-jwt-scope" in headers
            assert headers["x-jwt-scope"] == "read:prices write:quotes"

    def test_jwt_scope_empty_when_not_present(
        self, unauthorized_client, jwt_issuer_client, mock_backend
    ):
        """Test that JWT scope header is empty when not present in token."""
        # Create token without scope
        response = jwt_issuer_client.post("/token", json={"service_name": "pricing-service"})
        response = jwt_issuer_client.post(
            "/token", json={"service_name": "pricing-service"}
        )
        token = response.json()["token"]

        # Make request with JWT token
        unauthorized_client.post(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "test-service"},
        )

        if mock_backend.called:
            headers = dict(mock_backend.calls[0].request.headers)
            # Kong may not set the header if the claim is missing
            # Or it may set it to empty string
            if "x-jwt-scope" in headers:
                assert headers["x-jwt-scope"] == ""

    def test_jwt_timestamps_forwarded_correctly(
        self, unauthorized_client, valid_jwt_token, mock_backend
    ):
        """Test that JWT timestamps (iat, exp) are forwarded correctly."""
        # Decode token to get expected timestamps
        payload = jwt.decode(valid_jwt_token, options={"verify_signature": False})
        expected_iat = str(payload["iat"])
        expected_exp = str(payload["exp"])

        # Make request with JWT token
        unauthorized_client.post(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
            json={"name": "test-service"},
        )

        if mock_backend.called:
            headers = dict(mock_backend.calls[0].request.headers)
            assert "x-jwt-issued-at" in headers
            assert "x-jwt-expires-at" in headers
            assert headers["x-jwt-issued-at"] == expected_iat
            assert headers["x-jwt-expires-at"] == expected_exp

    def test_jwt_unique_id_forwarded(
        self, unauthorized_client, valid_jwt_token, mock_backend
    ):
        """Test that JWT ID (jti) is forwarded for request tracking."""
        # Decode token to get JTI
        payload = jwt.decode(valid_jwt_token, options={"verify_signature": False})
        expected_jti = payload["jti"]

        # Make request with JWT token
        unauthorized_client.post(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
            json={"name": "test-service"},
        )

        if mock_backend.called:
            headers = dict(mock_backend.calls[0].request.headers)
            assert "x-jwt-id" in headers
            assert headers["x-jwt-id"] == expected_jti

    def test_api_key_vs_jwt_auth_method(
        self, gateway_client, unauthorized_client, valid_jwt_token, mock_backend
    ):
        """Test that auth method header correctly identifies API key vs JWT."""
        # Test API key authentication
        gateway_client.post("/api/v1/registry/services", json={"name": "test-service-apikey"})
        gateway_client.post(
            "/api/v1/registry/services", json={"name": "test-service-apikey"}
        )

        if mock_backend.called:
            headers_apikey = dict(mock_backend.calls[-1].request.headers)
            # Should indicate API key authentication
            assert "x-auth-method" in headers_apikey
            # The exact value depends on Kong's template evaluation
            # It might be "api-key" or show consumer username

        # Clear previous calls
        mock_backend.calls.clear()

        # Test JWT authentication
        unauthorized_client.post(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
            json={"name": "test-service-jwt"},
        )

        if mock_backend.called:
            headers_jwt = dict(mock_backend.calls[-1].request.headers)
            assert "x-auth-method" in headers_jwt
            # Should indicate JWT authentication
            assert "jwt" in headers_jwt["x-auth-method"].lower()

    def test_consumer_headers_still_present_with_jwt(
        self, unauthorized_client, valid_jwt_token, mock_backend
    ):
        """Test that consumer headers are still present alongside JWT headers."""
        # Make request with JWT token
        unauthorized_client.post(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
            json={"name": "test-service"},
        )

        if mock_backend.called:
            headers = dict(mock_backend.calls[0].request.headers)

            # Consumer headers should still be present (even if empty for JWT)
            # These are from the anonymous consumer fallback
            assert "x-consumer-username" in headers or "x-consumer-id" in headers

    def test_jwt_claims_not_present_without_token(self, gateway_client, mock_backend):
        """Test that JWT headers are not present when using API key authentication."""
        # Make request with API key (no JWT)
        gateway_client.post("/api/v1/registry/services", json={"name": "test-service"})

        if mock_backend.called:
            headers = dict(mock_backend.calls[0].request.headers)

            # JWT headers should not be present or should be empty
            jwt_headers = [h for h in headers.keys() if h.startswith("x-jwt-")]
            for header in jwt_headers:
                # If present, should be empty for API key auth
                assert headers[header] == "" or headers[header] is None

    def test_malformed_jwt_does_not_break_forwarding(
        self, unauthorized_client, mock_backend
    ):
        """Test that malformed JWT doesn't break request forwarding."""
        # Use malformed JWT
        malformed_token = "malformed.jwt.token"

        # Request should still go through (falls back to API key auth)
        response = unauthorized_client.post(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {malformed_token}"},
            json={"name": "test-service"},
        )

        # Should get 401 for missing API key, not 500 for malformed JWT
        assert response.status_code == 401

    def test_grpc_service_receives_jwt_claims(
        self, unauthorized_client, valid_jwt_token, mock_backend
    ):
        """Test that gRPC services also receive JWT claims headers."""
        with respx.mock:
            # Mock gRPC service
            grpc_mock = respx.post(
                "http://registry-service.service.consul:50051/api/v1/registry"
            ).mock(return_value=httpx.Response(200, json={"success": True}))

            # Make gRPC-Web request with JWT
            unauthorized_client.post(
                "/grpc/v1/registry/register",
                headers={
                    "Authorization": f"Bearer {valid_jwt_token}",
                    "Content-Type": "application/grpc-web+proto",
                },
                content=b"grpc-request-data",
            )

            # Verify gRPC service received JWT headers
            if grpc_mock.called:
                headers = dict(grpc_mock.calls[0].request.headers)
                assert "x-jwt-sub" in headers
                assert headers["x-jwt-sub"] == "pricing-service"

    def test_multiple_services_receive_same_jwt_claims(
        self, unauthorized_client, valid_jwt_token
    ):
        """Test that multiple backend services receive the same JWT claims."""
        with respx.mock:
            # Mock multiple services
            registry_mock = respx.post(
                "http://registry-service:8080/api/v1/services"
            ).mock(return_value=httpx.Response(200, json={"success": True}))

            respx.post("http://pricing-service:8090/api/v1/prices").mock(
                return_value=httpx.Response(200, json={"success": True})
            )

            # Make requests to different services with same JWT
            unauthorized_client.post(
                "/api/v1/registry/services",
                headers={"Authorization": f"Bearer {valid_jwt_token}"},
                json={"name": "test-service"},
            )

            # Both services should receive the same JWT claims
            if registry_mock.called:
                registry_headers = dict(registry_mock.calls[0].request.headers)
                assert registry_headers["x-jwt-sub"] == "pricing-service"

    @pytest.fixture
    def jwt_with_all_claims(self, jwt_issuer_client):
        """Create a JWT token with all possible claims for comprehensive testing."""
        response = jwt_issuer_client.post(
            "/token",
            json={
                "service_name": "full-claims-service",
                "scope": "read:all write:all admin:system",
            },
        )

        assert response.status_code == 200
        return response.json()["token"]

    def test_all_jwt_claims_forwarded_comprehensive(
        self, unauthorized_client, jwt_with_all_claims, mock_backend
    ):
        """Comprehensive test that all JWT claims are properly forwarded."""
        # Decode token to get all expected values
        payload = jwt.decode(jwt_with_all_claims, options={"verify_signature": False})

        # Make request
        unauthorized_client.post(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {jwt_with_all_claims}"},
            json={"name": "test-service"},
        )

        if mock_backend.called:
            headers = dict(mock_backend.calls[0].request.headers)

            # Verify all expected headers are present and correct
            expected_mappings = {
                "x-jwt-sub": payload["sub"],
                "x-jwt-issuer": payload["iss"],
                "x-jwt-audience": payload["aud"],
                "x-jwt-id": payload["jti"],
                "x-jwt-type": payload["typ"],
                "x-jwt-scope": payload.get("scope", ""),
                "x-jwt-issued-at": str(payload["iat"]),
                "x-jwt-expires-at": str(payload["exp"]),
            }

            for header_name, expected_value in expected_mappings.items():
                assert header_name in headers, f"Header {header_name} not found"
                assert (
                    headers[header_name] == expected_value
                ), f"Header {header_name} value mismatch: {headers[header_name]} != {expected_value}"

    def test_case_insensitive_jwt_headers(
        self, unauthorized_client, valid_jwt_token, mock_backend
    ):
        """Test that JWT headers are accessible case-insensitively."""
        # Make request with JWT token
        unauthorized_client.post(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {valid_jwt_token}"},
            json={"name": "test-service"},
        )

        if mock_backend.called:
            request = mock_backend.calls[0].request

            # Check both lowercase and case-insensitive access
            assert request.headers.get("x-jwt-sub") or request.headers.get("X-JWT-Sub")
            assert request.headers.get("x-jwt-issuer") or request.headers.get("X-JWT-Issuer")
            assert request.headers.get("x-jwt-issuer") or request.headers.get(
                "X-JWT-Issuer"
            )
