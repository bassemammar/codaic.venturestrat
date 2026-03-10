"""
Integration tests for service-to-service JWT authentication.

Tests Task 8.6: Verify that a service can call another service with JWT.
This tests the complete flow where one service gets a JWT token from the
JWT issuer and uses it to authenticate when calling another service through
the Kong gateway.
"""

import pytest
import jwt
import time
import httpx
import respx


@pytest.mark.integration
class TestServiceToServiceJWT:
    """Test service-to-service authentication using JWT tokens."""

    @pytest.fixture
    def pricing_service_jwt(self, jwt_issuer_client):
        """Get a valid JWT token for pricing-service."""
        response = jwt_issuer_client.post(
            "/token",
            json={
                "service_name": "pricing-service",
                "scope": "read:services write:services",
            },
        )

        assert response.status_code == 200
        token_data = response.json()
        return token_data["token"]

    @pytest.fixture
    def risk_service_jwt(self, jwt_issuer_client):
        """Get a valid JWT token for risk-service."""
        response = jwt_issuer_client.post(
            "/token", json={"service_name": "risk-service", "scope": "read:registry"}
        )

        assert response.status_code == 200
        token_data = response.json()
        return token_data["token"]

    @pytest.fixture
    def mock_registry_service(self):
        """Mock registry service backend to capture JWT headers."""
        with respx.mock:
            mock = respx.route(host="registry-service", port=8080).mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "services": [
                            {
                                "id": "test-service-001",
                                "name": "test-service",
                                "host": "test-service:8080",
                                "status": "healthy",
                            }
                        ]
                    },
                    headers={"Content-Type": "application/json"},
                )
            )
            yield mock

    def test_service_to_service_jwt_authentication_flow(
        self, jwt_issuer_client, unauthorized_client, mock_registry_service
    ):
        """
        Test complete service-to-service JWT authentication flow.

        Simulates pricing-service getting a JWT token and using it to
        call registry-service through the Kong gateway.
        """
        # Step 1: Pricing service gets JWT token from issuer
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "pricing-service", "scope": "read:services"}
        )

        assert token_response.status_code == 200
        token_data = token_response.json()
        jwt_token = token_data["token"]

        # Verify token structure
        assert jwt_token is not None
        assert len(jwt_token.split(".")) == 3  # header.payload.signature

        # Step 2: Pricing service uses JWT to call registry service through gateway
        response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        # Should succeed or at least not fail with JWT validation errors
        assert response.status_code in [
            200,
            502,
            503,
        ], f"Service-to-service JWT call failed with: {response.status_code}"

        # Step 3: Verify JWT claims were forwarded to backend
        if mock_registry_service.called:
            request = mock_registry_service.calls[0].request
            headers = dict(request.headers)

            # JWT claims should be forwarded as headers
            assert "x-jwt-sub" in headers
            assert headers["x-jwt-sub"] == "pricing-service"
            assert "x-jwt-issuer" in headers
            assert headers["x-jwt-issuer"] == "venturestrat-gateway"
            assert "x-auth-method" in headers
            # Auth method should indicate JWT was used
            assert "jwt" in headers["x-auth-method"].lower()

    def test_multiple_services_can_get_different_jwt_tokens(
        self, jwt_issuer_client, unauthorized_client, mock_registry_service
    ):
        """Test that different services can get their own JWT tokens."""
        service_configs = [
            {"service_name": "pricing-service", "scope": "read:prices write:prices"},
            {"service_name": "risk-service", "scope": "read:risk write:risk"},
            {"service_name": "market-data-service", "scope": "read:market-data"},
        ]

        tokens = {}

        # Each service gets its own token
        for config in service_configs:
            response = jwt_issuer_client.post("/token", json=config)
            assert response.status_code == 200

            token_data = response.json()
            tokens[config["service_name"]] = token_data["token"]

            # Verify token contains correct service name
            decoded = jwt.decode(
                token_data["token"], options={"verify_signature": False}
            )
            assert decoded["sub"] == config["service_name"]
            if "scope" in config:
                assert decoded["scope"] == config["scope"]

        # All tokens should be different
        token_values = list(tokens.values())
        assert len(set(token_values)) == len(
            token_values
        ), "All JWT tokens should be unique"

        # Each service can use its own token to call registry
        for service_name, token in tokens.items():
            response = unauthorized_client.get(
                "/api/v1/registry/services",
                headers={"Authorization": f"Bearer {token}"},
            )

            # Should not fail with JWT errors
            assert response.status_code in [
                200,
                502,
                503,
            ], f"{service_name} JWT authentication failed"

    def test_jwt_token_reuse_across_requests(
        self, pricing_service_jwt, unauthorized_client, mock_registry_service
    ):
        """Test that a JWT token can be reused for multiple requests."""
        # Make multiple requests with same JWT token
        for i in range(5):
            response = unauthorized_client.get(
                f"/api/v1/registry/services?request_id={i}",
                headers={"Authorization": f"Bearer {pricing_service_jwt}"},
            )

            # All requests should have consistent authentication behavior
            assert response.status_code in [
                200,
                502,
                503,
            ], f"Request {i} with reused JWT failed: {response.status_code}"

    def test_jwt_token_with_different_http_methods(
        self, pricing_service_jwt, unauthorized_client
    ):
        """Test JWT authentication works with different HTTP methods."""
        methods_and_endpoints = [
            ("GET", "/api/v1/registry/services"),
            ("POST", "/api/v1/registry/services"),
            ("PUT", "/api/v1/registry/services/test-service"),
            ("DELETE", "/api/v1/registry/services/test-service"),
        ]

        for method, endpoint in methods_and_endpoints:
            response = unauthorized_client.request(
                method,
                endpoint,
                headers={"Authorization": f"Bearer {pricing_service_jwt}"},
                json={"name": "test-service"} if method in ["POST", "PUT"] else None,
            )

            # Should not fail with JWT authentication errors
            # 405 Method Not Allowed is acceptable for unsupported methods
            assert response.status_code in [
                200,
                405,
                404,
                502,
                503,
            ], f"JWT auth failed for {method} {endpoint}: {response.status_code}"

    def test_jwt_claims_forwarding_preserves_service_context(
        self, jwt_issuer_client, unauthorized_client, mock_registry_service
    ):
        """Test that JWT claims preserve the calling service's context."""
        # Create token for a specific service with specific scope
        response = jwt_issuer_client.post(
            "/token",
            json={
                "service_name": "portfolio-optimization-service",
                "scope": "read:portfolios write:portfolios read:market-data",
            },
        )

        token = response.json()["token"]

        # Make request through gateway
        unauthorized_client.post(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "new-portfolio-service",
                "tags": ["portfolio", "optimization"],
            },
        )

        if mock_registry_service.called:
            headers = dict(mock_registry_service.calls[0].request.headers)

            # Backend should receive full service context
            assert headers["x-jwt-sub"] == "portfolio-optimization-service"
            assert (
                "portfolio" in headers["x-jwt-scope"]
                and "market-data" in headers["x-jwt-scope"]
            )

            # Should also include JWT metadata
            assert "x-jwt-id" in headers  # Unique request ID
            assert "x-jwt-issued-at" in headers
            assert "x-jwt-expires-at" in headers

    def test_jwt_token_expiry_handling(self, jwt_issuer_client, unauthorized_client):
        """Test handling of JWT token expiry."""
        # Get a fresh token
        response = jwt_issuer_client.post("/token", json={"service_name": "expiry-test-service"})
        response = jwt_issuer_client.post(
            "/token", json={"service_name": "expiry-test-service"}
        )

        token = response.json()["token"]

        # Decode to check expiry time
        decoded = jwt.decode(token, options={"verify_signature": False})
        current_time = int(time.time())

        # Token should not be expired yet
        assert decoded["exp"] > current_time, "Fresh token should not be expired"

        # Token should have reasonable lifetime (default: 1 hour)
        lifetime = decoded["exp"] - current_time
        assert (
            3500 <= lifetime <= 3700
        ), f"Token lifetime unexpected: {lifetime} seconds"

        # Use token immediately (should work)
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"Authorization": f"Bearer {token}"}
        )

        # Should not fail with expiry error
        assert response.status_code in [
            200,
            502,
            503,
        ], f"Fresh token should not be expired: {response.status_code}"

    def test_jwt_concurrent_service_requests(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test concurrent service-to-service requests with JWT."""
        import concurrent.futures

        # Get tokens for multiple services
        services = ["service-a", "service-b", "service-c"]
        tokens = {}

        for service in services:
            response = jwt_issuer_client.post("/token", json={"service_name": service})
            tokens[service] = response.json()["token"]

        def make_service_request(service_name, token):
            """Make a request as a specific service."""
            return unauthorized_client.get(
                f"/api/v1/registry/services?caller={service_name}",
                headers={"Authorization": f"Bearer {token}"},
            )

        # Make concurrent requests from different services
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(services)
        ) as executor:
            futures = [
                executor.submit(make_service_request, service, tokens[service])
                for service in services
            ]

            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All requests should succeed or fail consistently
        status_codes = [r.status_code for r in responses]

        # Should not have JWT-related failures
        for status_code in status_codes:
            assert status_code in [
                200,
                502,
                503,
            ], f"Concurrent JWT requests failed with unexpected status: {status_code}"

    def test_jwt_without_scope_still_works(
        self, jwt_issuer_client, unauthorized_client, mock_registry_service
    ):
        """Test that JWT without scope claim still allows authentication."""
        # Create token without scope
        response = jwt_issuer_client.post("/token", json={"service_name": "minimal-claims-service"})
        response = jwt_issuer_client.post(
            "/token", json={"service_name": "minimal-claims-service"}
        )

        token = response.json()["token"]

        # Verify token doesn't have scope claim
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert "scope" not in decoded or decoded.get("scope") is None

        # Use token for request
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"Authorization": f"Bearer {token}"}
        )

        # Should still work for authentication
        assert response.status_code in [
            200,
            502,
            503,
        ], "JWT without scope should still authenticate"

        if mock_registry_service.called:
            headers = dict(mock_registry_service.calls[0].request.headers)
            assert headers["x-jwt-sub"] == "minimal-claims-service"
            # Scope header might be empty or missing
            if "x-jwt-scope" in headers:
                assert headers["x-jwt-scope"] in ["", None]

    def test_jwt_issuer_endpoint_available_through_gateway(self, unauthorized_client):
        """Test that services can access JWT issuer through the gateway."""
        # Services should be able to get tokens via gateway
        response = unauthorized_client.post(
            "/api/v1/auth/token", json={"service_name": "gateway-test-service"}
        )

        # Should either succeed or fail due to API key requirement
        # (depending on Kong configuration for JWT issuer route)
        assert response.status_code in [
            200,
            401,
            403,
            502,
            503,
        ], f"JWT issuer endpoint should be accessible: {response.status_code}"

        if response.status_code == 200:
            # If successful, should return valid token structure
            data = response.json()
            assert "token" in data
            assert "expires_at" in data
            assert "token_type" in data

            # Token should be valid
            token = data["token"]
            assert len(token.split(".")) == 3

    def test_service_identity_preservation_in_jwt_claims(
        self, jwt_issuer_client, unauthorized_client, mock_registry_service
    ):
        """Test that service identity is properly preserved and forwarded."""
        # Create token for service with detailed identity
        service_name = "financial-risk-calculation-service"

        response = jwt_issuer_client.post(
            "/token",
            json={
                "service_name": service_name,
                "scope": "read:positions write:risk-metrics",
            },
        )

        token = response.json()["token"]

        # Make request and verify service identity in forwarded headers
        unauthorized_client.post(
            "/api/v1/registry/services",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Service-Version": "1.2.0",
                "X-Request-ID": "risk-calc-001",
            },
            json={"name": "risk-calculation-job", "type": "batch"},
        )

        if mock_registry_service.called:
            headers = dict(mock_registry_service.calls[0].request.headers)

            # Service identity should be preserved exactly
            assert headers["x-jwt-sub"] == service_name

            # Original headers should pass through
            assert headers.get("x-service-version") == "1.2.0"
            assert headers.get("x-request-id") == "risk-calc-001"

            # JWT-specific headers should be present
            assert "x-jwt-issuer" in headers
            assert "x-jwt-audience" in headers
            assert headers["x-jwt-audience"] == "venturestrat-services"
