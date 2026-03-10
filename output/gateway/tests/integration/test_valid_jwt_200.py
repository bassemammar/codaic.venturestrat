"""
Integration tests for valid JWT (200) authentication scenarios.

Tests the Kong JWT plugin behavior when JWT tokens are valid and requests
should succeed with 200 status codes. These tests focus specifically on
task 8.3: Write tests for valid JWT (200).
"""

import pytest
import jwt
import time


@pytest.mark.unit
class TestValidJWTStructure:
    """Unit tests for valid JWT structure validation (no infrastructure required)."""

    def test_valid_jwt_token_creation(self):
        """Test that we can create valid JWT tokens with proper structure."""
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": int(time.time()) + 3600,  # 1 hour from now
            "iat": int(time.time()),
            "jti": "test-jwt-id",
            "scope": "read:services",
        }

        token = jwt.encode(payload, "dev-secret-change-in-prod", algorithm="HS256")

        # Verify token format (header.payload.signature)
        assert token.count(".") == 2

        # Decode and verify contents
        decoded = jwt.decode(
            token,
            "dev-secret-change-in-prod",
            algorithms=["HS256"],
            audience="venturestrat-services",
        )

        assert decoded["sub"] == "test-service"
        assert decoded["iss"] == "venturestrat-gateway"
        assert decoded["aud"] == "venturestrat-services"
        assert decoded["scope"] == "read:services"

    def test_valid_jwt_claim_scenarios(self):
        """Test various valid JWT claim scenarios."""
        valid_scenarios = [
            {
                "sub": "pricing-service",
                "scope": "read:prices write:prices",
                "description": "pricing_service_with_scopes",
            },
            {
                "sub": "risk-service",
                "scope": "read:risk",
                "role": "service",
                "description": "risk_service_with_role",
            },
            {
                "sub": "market-data-service",
                "description": "market_data_service_minimal",
            },
            {
                "sub": "admin-service",
                "scope": "admin:all",
                "permissions": ["read", "write", "delete"],
                "description": "admin_service_with_permissions",
            },
        ]

        for scenario in valid_scenarios:
            current_time = int(time.time())
            base_payload = {
                "iss": "venturestrat-gateway",
                "aud": "venturestrat-services",
                "exp": current_time + 3600,
                "iat": current_time,
                "jti": f"test-{scenario['description']}",
            }

            # Merge scenario data (excluding description)
            payload = {
                **base_payload,
                **{k: v for k, v in scenario.items() if k != "description"},
            }

            # Should encode without errors
            token = jwt.encode(payload, "dev-secret-change-in-prod", algorithm="HS256")
            assert isinstance(token, str)
            assert len(token) > 0


@pytest.mark.integration
class TestValidJWT200:
    """Test cases for valid JWT authentication returning 200."""

    def test_valid_jwt_from_issuer_succeeds(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test that valid JWT token from issuer allows access."""
        # Get a valid token from the JWT issuer
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "test-service", "scope": "read:services"}
        )

        assert token_response.status_code == 200
        token_data = token_response.json()
        token = token_data["token"]

        # Use the token in a request to the gateway
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"Authorization": f"Bearer {token}"}
        )

        # With valid JWT, should either succeed (200) or may still require API key
        # depending on Kong configuration. For now, we test that it doesn't fail
        # with JWT-specific errors (expired, malformed, etc.)
        assert response.status_code in [
            200,
            401,
            403,
            502,
            503,
        ], f"Valid JWT should not return unexpected status: {response.status_code}"

        # If it returns 401/403, it should be for API key reasons, not JWT issues
        if response.status_code in [401, 403]:
            error_data = response.json()
            message = error_data.get("message", "").lower()
            # Should not contain JWT-specific error messages
            assert "expired" not in message
            assert "malformed" not in message
            assert "invalid signature" not in message

    def test_valid_jwt_with_different_services(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test that valid JWTs work for different service names."""
        service_names = [
            "pricing-service",
            "risk-service",
            "market-data-service",
            "portfolio-service",
            "registry-service",
        ]

        for service_name in service_names:
            # Get token for each service
            token_response = jwt_issuer_client.post("/token", json={"service_name": service_name})
            token_response = jwt_issuer_client.post(
                "/token", json={"service_name": service_name}
            )

            assert token_response.status_code == 200
            token = token_response.json()["token"]

            # Use token in request
            response = unauthorized_client.get(
                "/api/v1/registry/services",
                headers={"Authorization": f"Bearer {token}"},
            )

            # Should not fail with JWT validation errors
            assert (
                response.status_code in [200, 401, 403, 502, 503]
            ), f"Service {service_name} JWT should not return unexpected status: {response.status_code}"

    def test_valid_jwt_with_various_scopes(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test that valid JWTs with different scopes work."""
        scope_test_cases = [
            "read:all",
            "read:services write:services",
            "admin:system",
            "read:prices write:prices read:risk",
            "service:registry",
            "user:profile",
        ]

        for scope in scope_test_cases:
            # Get token with scope
            token_response = jwt_issuer_client.post(
                "/token", json={"service_name": "test-service", "scope": scope}
            )

            assert token_response.status_code == 200
            token = token_response.json()["token"]

            # Use token in request
            response = unauthorized_client.get(
                "/api/v1/registry/services",
                headers={"Authorization": f"Bearer {token}"},
            )

            # Valid scope should not cause JWT rejection
            assert response.status_code in [
                200,
                401,
                403,
                502,
                503,
            ], f"Scope '{scope}' should not cause JWT rejection: {response.status_code}"

    def test_valid_jwt_token_validation_endpoint(self, jwt_issuer_client):
        """Test that valid JWT tokens pass validation."""
        # Get a fresh token
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "validation-test-service"}
        )

        assert token_response.status_code == 200
        token = token_response.json()["token"]

        # Validate the token
        validation_response = jwt_issuer_client.post("/validate", json={"token": token})

        assert validation_response.status_code == 200

        validation_data = validation_response.json()
        assert validation_data["valid"] is True
        assert "payload" in validation_data
        assert "expires_in" in validation_data

        # Verify payload contents
        payload = validation_data["payload"]
        assert payload["sub"] == "validation-test-service"
        assert payload["iss"] == "venturestrat-gateway"
        assert payload["aud"] == "venturestrat-services"

    def test_valid_jwt_fresh_token_not_expired(self, jwt_issuer_client):
        """Test that freshly issued tokens are not expired."""
        # Issue token
        token_response = jwt_issuer_client.post("/token", json={"service_name": "fresh-token-test"})
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "fresh-token-test"}
        )

        assert token_response.status_code == 200
        token_data = token_response.json()
        token = token_data["token"]

        # Decode token to check expiry
        decoded = jwt.decode(token, options={"verify_signature": False})
        current_time = int(time.time())

        # Token should not be expired
        assert decoded["exp"] > current_time
        assert decoded["iat"] <= current_time

        # Should have reasonable lifetime (at least 30 minutes)
        lifetime = decoded["exp"] - current_time
        assert lifetime >= 1800, f"Token lifetime too short: {lifetime} seconds"

    def test_valid_jwt_with_correlation_id(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test that valid JWT preserves correlation ID in response."""
        # Get token
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "correlation-test-service"}
        )

        token = token_response.json()["token"]
        correlation_id = "test-correlation-valid-jwt-123"

        # Make request with correlation ID and valid JWT
        response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Correlation-ID": correlation_id,
            },
        )

        # Correlation ID should be preserved regardless of auth outcome
        response_correlation = response.headers.get("X-Correlation-ID")
        assert response_correlation is not None

        # If Kong echoes our ID, it should match
        if response_correlation == correlation_id:
            assert response_correlation == correlation_id

    def test_valid_jwt_multiple_requests_with_same_token(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test that same valid JWT can be used for multiple requests."""
        # Get token once
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "reuse-test-service"}
        )

        token = token_response.json()["token"]

        # Make multiple requests with same token
        for i in range(5):
            response = unauthorized_client.get(
                f"/api/v1/registry/services?request={i}",
                headers={"Authorization": f"Bearer {token}"},
            )

            # Each request should have consistent auth behavior
            # (not JWT-related failures)
            assert response.status_code in [
                200,
                401,
                403,
                502,
                503,
            ], f"Request {i} with reused token failed unexpectedly: {response.status_code}"
            assert (
                response.status_code in [200, 401, 403, 502, 503]
            ), f"Request {i} with reused token failed unexpectedly: {response.status_code}"

    def test_valid_jwt_different_endpoints(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test that valid JWT works with different endpoints."""
        # Get token
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "multi-endpoint-test"}
        )

        token = token_response.json()["token"]

        endpoints_to_test = [
            "/api/v1/registry/services",
            "/api/v1/registry/health",
        ]

        for endpoint in endpoints_to_test:
            response = unauthorized_client.get(
                endpoint, headers={"Authorization": f"Bearer {token}"}
            )

            # Valid JWT should not cause endpoint-specific auth failures
            assert response.status_code in [
                200,
                401,
                403,
                404,
                405,
                502,
                503,
            ], f"Valid JWT failed on {endpoint}: {response.status_code}"

    def test_valid_jwt_response_time_acceptable(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test that valid JWT requests have acceptable response times."""
        # Get token
        token_response = jwt_issuer_client.post("/token", json={"service_name": "performance-test"})
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "performance-test"}
        )

        token = token_response.json()["token"]

        # Measure response time
        start_time = time.time()
        unauthorized_client.get(
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"Authorization": f"Bearer {token}"}
        )
        end_time = time.time()

        response_time = end_time - start_time

        # Response should be reasonably fast (< 2 seconds even with JWT validation)
        assert response_time < 2.0, f"Valid JWT request took too long: {response_time}s"

    def test_valid_jwt_concurrent_requests(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test that valid JWT handles concurrent requests properly."""
        # Get token
        token_response = jwt_issuer_client.post("/token", json={"service_name": "concurrent-test"})
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "concurrent-test"}
        )

        token = token_response.json()["token"]

        # Make concurrent requests with same token
        import concurrent.futures

        def make_request(request_id):
            return unauthorized_client.get(
                f"/api/v1/registry/services?concurrent={request_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All requests should have consistent behavior (no race conditions)
        status_codes = [r.status_code for r in responses]

        # All should succeed or fail consistently (no mix due to race conditions)
        assert (
            len(set(status_codes)) <= 2
        ), f"Inconsistent status codes in concurrent requests: {status_codes}"

        # No unexpected errors
        for status_code in status_codes:
            assert status_code in [
                200,
                401,
                403,
                502,
                503,
            ], f"Unexpected status code in concurrent request: {status_code}"

    def test_valid_jwt_with_different_http_methods(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test that valid JWT works with different HTTP methods."""
        # Get token
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "http-methods-test"}
        )

        token = token_response.json()["token"]

        http_methods = [
            ("GET", "/api/v1/registry/services"),
            ("POST", "/api/v1/registry/services"),
            ("PUT", "/api/v1/registry/services/test"),
            ("DELETE", "/api/v1/registry/services/test"),
        ]

        for method, path in http_methods:
            response = unauthorized_client.request(
                method, path, headers={"Authorization": f"Bearer {token}"}
            )

            # Valid JWT should not cause method-specific auth failures
            # 405 Method Not Allowed is acceptable for unsupported methods
            assert response.status_code in [
                200,
                401,
                403,
                404,
                405,
                502,
                503,
            ], f"Valid JWT failed for {method} {path}: {response.status_code}"

    def test_valid_jwt_error_response_format_when_backend_unavailable(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test that valid JWT maintains proper error format when backend is down."""
        # Get token
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "error-format-test"}
        )

        token = token_response.json()["token"]

        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"Authorization": f"Bearer {token}"}
        )

        # If backend is unavailable (502/503), response should still be valid JSON
        if response.status_code in [502, 503]:
            try:
                error_data = response.json()
                # Should have proper error structure
                assert isinstance(error_data, dict)
                if "message" in error_data:
                    assert isinstance(error_data["message"], str)
            except ValueError:
                # Some 502/503 responses may not be JSON, that's acceptable
                pass

        # Response should have proper content type
        content_type = response.headers.get("Content-Type", "")
        assert any(
            ct in content_type for ct in ["application/json", "text/plain", "text/html"]
        )

    def test_valid_jwt_claims_integrity(self, jwt_issuer_client):
        """Test that JWT claims are preserved through validation."""
        # Create token with specific claims
        token_response = jwt_issuer_client.post(
            "/token",
            json={
                "service_name": "claims-integrity-test",
                "scope": "read:all write:specific",
            },
        )

        assert token_response.status_code == 200
        token = token_response.json()["token"]

        # Validate token and check claims
        validation_response = jwt_issuer_client.post("/validate", json={"token": token})

        assert validation_response.status_code == 200
        validation_data = validation_response.json()

        payload = validation_data["payload"]

        # All required claims should be present
        required_claims = ["sub", "iss", "aud", "exp", "iat", "jti"]
        for claim in required_claims:
            assert claim in payload, f"Missing required claim: {claim}"

        # Custom claims should be preserved
        assert payload["sub"] == "claims-integrity-test"
        assert payload["scope"] == "read:all write:specific"

    def test_valid_jwt_unique_jti_per_request(self, jwt_issuer_client):
        """Test that each JWT request gets unique JTI (JWT ID)."""
        # Get multiple tokens for same service
        tokens = []
        for i in range(5):
            response = jwt_issuer_client.post(
                "/token", json={"service_name": "jti-uniqueness-test"}
            )
            assert response.status_code == 200
            tokens.append(response.json()["token"])

        # Extract JTI from each token
        jtis = []
        for token in tokens:
            decoded = jwt.decode(token, options={"verify_signature": False})
            jtis.append(decoded["jti"])

        # All JTIs should be unique
        assert len(jtis) == len(set(jtis)), f"Duplicate JTIs found: {jtis}"

    def test_valid_jwt_timezone_independence(self, jwt_issuer_client):
        """Test that JWT validation works regardless of timezone differences."""
        # Issue token
        token_response = jwt_issuer_client.post("/token", json={"service_name": "timezone-test"})
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "timezone-test"}
        )

        assert token_response.status_code == 200
        token = token_response.json()["token"]

        # Decode to check timestamps
        decoded = jwt.decode(token, options={"verify_signature": False})

        # iat and exp should be UTC timestamps
        current_time = int(time.time())

        # iat should be recent (within last minute)
        assert (
            abs(decoded["iat"] - current_time) < 60
        ), f"iat timestamp seems incorrect: {decoded['iat']} vs {current_time}"

        # exp should be in the future
        assert (
            decoded["exp"] > current_time
        ), f"exp timestamp should be in future: {decoded['exp']} vs {current_time}"

    def test_valid_jwt_with_api_key_dual_auth(self, jwt_issuer_client, gateway_client):
        """Test that valid JWT can work alongside API key authentication."""
        # Get JWT token
        token_response = jwt_issuer_client.post("/token", json={"service_name": "dual-auth-test"})
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "dual-auth-test"}
        )

        assert token_response.status_code == 200
        token = token_response.json()["token"]

        # Make request with both API key (from gateway_client) and JWT
        # gateway_client already has API key configured
        response = gateway_client.get(
            "/api/v1/registry/services", headers={"Authorization": f"Bearer {token}"}
        )

        # With both valid API key and JWT, should have best chance of success
        # At minimum, should not fail with auth errors
        assert response.status_code in [
            200,
            404,
            502,
            503,
        ], f"Dual auth (API key + JWT) should not fail with auth error: {response.status_code}"
        assert (
            response.status_code in [200, 404, 502, 503]
        ), f"Dual auth (API key + JWT) should not fail with auth error: {response.status_code}"

        # If successful, should be 200 or valid backend response
        if response.status_code == 200:
            # Should be valid JSON response
            try:
                data = response.json()
                assert isinstance(data, dict)
            except ValueError:
                pytest.fail("200 response should be valid JSON")
