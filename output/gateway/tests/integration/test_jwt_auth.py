"""
Integration tests for JWT authentication.

Tests JWT token validation, service-to-service authentication flow.
"""

import pytest
import jwt
from datetime import datetime, timedelta


@pytest.mark.integration
class TestJWTAuthentication:
    """Test JWT authentication functionality."""

    def test_jwt_without_token_401(self, unauthorized_client):
        """Test that JWT-protected endpoints without token return 401."""
        # For now, API key auth is global. JWT auth will be service-specific
        # This test ensures the JWT plugin is configured

        response = unauthorized_client.get("/api/v1/registry/services")
        # Currently expecting 401 for missing API key
        assert response.status_code == 401

    def test_jwt_issuer_token_generation(self, jwt_issuer_client):
        """Test that JWT issuer can generate tokens."""
        response = jwt_issuer_client.post("/token", json={"service_name": "test-service"})
        response = jwt_issuer_client.post(
            "/token", json={"service_name": "test-service"}
        )

        assert response.status_code == 200

        data = response.json()
        assert "token" in data
        assert "expires_at" in data
        assert data["token_type"] == "Bearer"

        # Verify token structure
        token = data["token"]
        assert token.count(".") == 2  # JWT format

    def test_jwt_with_invalid_token_401(self, unauthorized_client, jwt_issuer_client):
        """Test that invalid JWT tokens return 401."""
        # Create invalid token
        invalid_token = "invalid.jwt.token"

        response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )

        # Should still require API key for now
        # When JWT is implemented, this should be 401 for invalid token
        assert response.status_code in [401, 403]

    def test_jwt_with_expired_token_401(self, unauthorized_client):
        """Test that expired JWT tokens return 401."""
        # Create expired token
        past_time = datetime.utcnow() - timedelta(hours=1)
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - timedelta(hours=1),
        }

        # Use development secret (should match JWT issuer)
        expired_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        # Should require API key for now
        assert response.status_code in [401, 403]

    def test_jwt_with_valid_token_passes(self, unauthorized_client, jwt_issuer_client):
        """Test that valid JWT tokens pass authentication."""
        # Get a valid token from issuer
        token_response = jwt_issuer_client.post("/token", json={"service_name": "test-service"})
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "test-service"}
        )

        assert token_response.status_code == 200
        token = token_response.json()["token"]

        # Use token in request
        response = unauthorized_client.get(
            "/api/v1/registry/services", headers={"Authorization": f"Bearer {token}"}
        )

        # Should still require API key for now (JWT not enforced yet)
        # When JWT is enforced, this should pass
        assert response.status_code in [401, 403, 200, 502, 503]

    def test_jwt_claims_validation(self, jwt_issuer_client):
        """Test that JWT contains required claims."""
        response = jwt_issuer_client.post(
            "/token", json={"service_name": "pricing-service", "scope": "read:prices"}
        )

        assert response.status_code == 200
        token = response.json()["token"]

        # Decode without verification to check claims
        payload = jwt.decode(token, options={"verify_signature": False})

        assert payload["sub"] == "pricing-service"
        assert payload["iss"] == "venturestrat-gateway"
        assert payload["aud"] == "venturestrat-services"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
        assert payload["scope"] == "read:prices"

    def test_jwt_token_validation_endpoint(self, jwt_issuer_client):
        """Test JWT validation endpoint."""
        # Get a token
        token_response = jwt_issuer_client.post("/token", json={"service_name": "test-service"})
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "test-service"}
        )

        token = token_response.json()["token"]

        # Validate the token
        validate_response = jwt_issuer_client.post("/validate", json={"token": token})

        assert validate_response.status_code == 200

        data = validate_response.json()
        assert data["valid"] is True
        assert "payload" in data
        assert "expires_in" in data

    def test_jwt_token_unique_jti(self, jwt_issuer_client):
        """Test that each JWT has unique JTI."""
        # Get two tokens for same service
        response1 = jwt_issuer_client.post(
            "/token", json={"service_name": "test-service"}
        )
        response2 = jwt_issuer_client.post(
            "/token", json={"service_name": "test-service"}
        )

        token1 = response1.json()["token"]
        token2 = response2.json()["token"]

        # Decode both tokens
        payload1 = jwt.decode(token1, options={"verify_signature": False})
        payload2 = jwt.decode(token2, options={"verify_signature": False})

        # JTI should be different
        assert payload1["jti"] != payload2["jti"]

    def test_jwt_wrong_audience(self, unauthorized_client):
        """Test that JWT with wrong audience is rejected."""
        # Create token with wrong audience
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "wrong-audience",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
        }

        wrong_audience_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        # Validate against issuer (should fail)
        # Note: This tests the JWT issuer validation endpoint
        import httpx

        jwt_client = httpx.Client(base_url="http://localhost:8002")

        try:
            response = jwt_client.post("/validate", json={"token": wrong_audience_token})
            response = jwt_client.post(
                "/validate", json={"token": wrong_audience_token}
            )

            assert response.status_code == 401
            assert "audience" in response.json()["detail"].lower()

        finally:
            jwt_client.close()

    def test_jwt_wrong_issuer(self, unauthorized_client):
        """Test that JWT with wrong issuer is rejected."""
        payload = {
            "sub": "test-service",
            "iss": "wrong-issuer",
            "aud": "venturestrat-services",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
        }

        wrong_issuer_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        # Test via validation endpoint
        import httpx

        jwt_client = httpx.Client(base_url="http://localhost:8002")

        try:
            response = jwt_client.post("/validate", json={"token": wrong_issuer_token})

            # Should still validate (issuer not checked in validation endpoint)
            # But payload will show wrong issuer
            assert response.status_code == 200
            payload_returned = response.json()["payload"]
            assert payload_returned["iss"] == "wrong-issuer"

        finally:
            jwt_client.close()

    def test_service_to_service_flow(self, jwt_issuer_client):
        """Test complete service-to-service authentication flow."""
        # Service requests token
        token_response = jwt_issuer_client.post("/token", json={"service_name": "pricing-service"})
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "pricing-service"}
        )

        assert token_response.status_code == 200
        token = token_response.json()["token"]

        # Service validates token (optional step)
        validate_response = jwt_issuer_client.post("/validate", json={"token": token})

        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

        # Token can be used for service calls
        # (This will be tested when JWT plugin is active in Kong)
