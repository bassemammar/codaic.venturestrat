"""
Unit tests for service-to-service JWT authentication.

Tests Task 8.6: Verify that a service can call another service with JWT.
These are unit tests that verify JWT token creation and validation without
requiring the full gateway stack.
"""

import pytest
import jwt
import time
from fastapi.testclient import TestClient

# Import the JWT issuer app
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent / "jwt-issuer"))

from main import app as jwt_issuer_app


@pytest.mark.unit
class TestServiceToServiceJWTUnit:
    """Unit tests for service-to-service JWT authentication."""

    @pytest.fixture
    def jwt_client(self):
        """Test client for JWT issuer service."""
        return TestClient(jwt_issuer_app)

    def test_service_can_request_jwt_token(self, jwt_client):
        """Test that a service can request and receive a valid JWT token."""
        # Service requests a JWT token
        response = jwt_client.post(
            "/token",
            json={
                "service_name": "pricing-service",
                "scope": "read:services write:services",
            },
        )

        assert response.status_code == 200

        token_data = response.json()
        assert "token" in token_data
        assert "token_type" in token_data
        assert "expires_at" in token_data
        assert "expires_in" in token_data

        assert token_data["token_type"] == "Bearer"

        # Verify token structure
        token = token_data["token"]
        assert len(token.split(".")) == 3  # header.payload.signature

        # Decode token without signature verification to check claims
        payload = jwt.decode(token, options={"verify_signature": False})

        # Verify required claims
        assert payload["sub"] == "pricing-service"
        assert payload["iss"] == "venturestrat-gateway"
        assert payload["aud"] == "venturestrat-services"
        assert payload["scope"] == "read:services write:services"
        assert "jti" in payload  # Unique token ID
        assert "iat" in payload  # Issued at
        assert "exp" in payload  # Expires at

        # Verify token is not expired
        current_time = int(time.time())
        assert payload["exp"] > current_time
        assert payload["iat"] <= current_time

    def test_different_services_get_different_tokens(self, jwt_client):
        """Test that different services get tokens with their specific identity."""
        services = [
            {"name": "pricing-service", "scope": "read:prices write:prices"},
            {"name": "risk-service", "scope": "read:risk"},
            {"name": "market-data-service", "scope": "read:market-data"},
        ]

        tokens = {}

        for service in services:
            response = jwt_client.post(
                "/token",
                json={"service_name": service["name"], "scope": service["scope"]},
            )

            assert response.status_code == 200
            token = response.json()["token"]
            tokens[service["name"]] = token

            # Verify token contains correct service identity
            payload = jwt.decode(token, options={"verify_signature": False})
            assert payload["sub"] == service["name"]
            assert payload["scope"] == service["scope"]

        # All tokens should be unique
        token_values = list(tokens.values())
        assert len(set(token_values)) == len(token_values)

    def test_jwt_token_validation_with_correct_secret(self, jwt_client):
        """Test that JWT tokens can be validated with the correct secret."""
        # Get a token
        response = jwt_client.post("/token", json={"service_name": "validation-test-service"})
        response = jwt_client.post(
            "/token", json={"service_name": "validation-test-service"}
        )

        token = response.json()["token"]

        # Validate with the same secret used to sign
        secret = "dev-secret-change-in-prod"  # Matches JWT_SECRET in issuer

        decoded_payload = jwt.decode(
            token, secret, algorithms=["HS256"], audience="venturestrat-services"
        )

        assert decoded_payload["sub"] == "validation-test-service"
        assert decoded_payload["iss"] == "venturestrat-gateway"

    def test_jwt_token_validation_with_wrong_secret_fails(self, jwt_client):
        """Test that JWT token validation fails with wrong secret."""
        # Get a token
        response = jwt_client.post("/token", json={"service_name": "security-test-service"})
        response = jwt_client.post(
            "/token", json={"service_name": "security-test-service"}
        )

        token = response.json()["token"]

        # Try to validate with wrong secret
        wrong_secret = "wrong-secret"

        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(
                token,
                wrong_secret,
                algorithms=["HS256"],
                audience="venturestrat-services",
            )

    def test_expired_jwt_token_validation_fails(self, jwt_client):
        """Test that expired JWT tokens fail validation."""
        # Create an expired token manually
        past_time = int(time.time()) - 3600  # 1 hour ago

        payload = {
            "sub": "expired-test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - 3600,
            "jti": "expired-token-id",
        }

        secret = "dev-secret-change-in-prod"
        expired_token = jwt.encode(payload, secret, algorithm="HS256")

        # Validation should fail with expired signature
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                expired_token,
                secret,
                algorithms=["HS256"],
                audience="venturestrat-services",
            )

    def test_jwt_token_with_wrong_audience_fails(self, jwt_client):
        """Test that JWT tokens with wrong audience fail validation."""
        # Create token with wrong audience
        current_time = int(time.time())

        payload = {
            "sub": "wrong-audience-service",
            "iss": "venturestrat-gateway",
            "aud": "wrong-audience",  # Wrong audience
            "exp": current_time + 3600,
            "iat": current_time,
            "jti": "wrong-audience-token",
        }

        secret = "dev-secret-change-in-prod"
        wrong_audience_token = jwt.encode(payload, secret, algorithm="HS256")

        # Validation should fail with invalid audience
        with pytest.raises(jwt.InvalidAudienceError):
            jwt.decode(
                wrong_audience_token,
                secret,
                algorithms=["HS256"],
                audience="venturestrat-services",
            )

    def test_service_to_service_authentication_flow_simulation(self, jwt_client):
        """
        Simulate the complete service-to-service authentication flow.

        This test simulates:
        1. Service A requests JWT from issuer
        2. Service A makes call to Service B through gateway with JWT
        3. Gateway validates JWT and forwards claims to Service B
        """
        # Step 1: Service A (pricing-service) gets JWT token
        token_response = jwt_client.post(
            "/token",
            json={
                "service_name": "pricing-service",
                "scope": "read:registry call:risk-service",
            },
        )

        assert token_response.status_code == 200
        jwt_token = token_response.json()["token"]

        # Step 2: Simulate gateway JWT validation (what Kong would do)
        # Decode and validate the token
        secret = "dev-secret-change-in-prod"

        try:
            payload = jwt.decode(
                jwt_token, secret, algorithms=["HS256"], audience="venturestrat-services"
            )
            jwt_valid = True
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            jwt_valid = False

        assert jwt_valid is True

        # Step 3: Simulate gateway forwarding JWT claims as headers
        # These are the headers that Kong would add to the backend request
        forwarded_headers = {
            "X-JWT-Sub": payload["sub"],
            "X-JWT-Issuer": payload["iss"],
            "X-JWT-Audience": payload["aud"],
            "X-JWT-ID": payload["jti"],
            "X-JWT-Scope": payload.get("scope", ""),
            "X-JWT-Issued-At": str(payload["iat"]),
            "X-JWT-Expires-At": str(payload["exp"]),
            "X-Auth-Method": "jwt",
        }

        # Step 4: Verify that Service B would receive correct identity information
        assert forwarded_headers["X-JWT-Sub"] == "pricing-service"
        assert forwarded_headers["X-JWT-Issuer"] == "venturestrat-gateway"
        assert forwarded_headers["X-Auth-Method"] == "jwt"
        assert "call:risk-service" in forwarded_headers["X-JWT-Scope"]

        # Service B can now trust the identity and scope information

    def test_jwt_claims_preserve_service_context(self, jwt_client):
        """Test that JWT claims preserve full service context."""
        # Create token with rich context
        response = jwt_client.post(
            "/token",
            json={
                "service_name": "portfolio-optimization-service",
                "scope": "read:portfolios write:portfolios read:market-data admin:risk",
            },
        )

        token = response.json()["token"]
        payload = jwt.decode(token, options={"verify_signature": False})

        # Verify all context is preserved
        assert payload["sub"] == "portfolio-optimization-service"
        assert "read:portfolios" in payload["scope"]
        assert "write:portfolios" in payload["scope"]
        assert "read:market-data" in payload["scope"]
        assert "admin:risk" in payload["scope"]

        # Verify standard JWT claims
        assert payload["iss"] == "venturestrat-gateway"
        assert payload["aud"] == "venturestrat-services"
        assert payload["typ"] == "access_token"

        # Verify unique identifiers
        assert "jti" in payload  # Unique token ID for tracking

    def test_jwt_issuer_validation_endpoint(self, jwt_client):
        """Test the JWT issuer's built-in validation endpoint."""
        # Get a token
        token_response = jwt_client.post(
            "/token", json={"service_name": "validation-endpoint-test"}
        )

        token = token_response.json()["token"]

        # Use the validation endpoint
        validation_response = jwt_client.post("/validate", json={"token": token})

        assert validation_response.status_code == 200

        validation_data = validation_response.json()
        assert validation_data["valid"] is True
        assert "payload" in validation_data
        assert "expires_in" in validation_data

        # Verify payload structure
        payload = validation_data["payload"]
        assert payload["sub"] == "validation-endpoint-test"
        assert payload["iss"] == "venturestrat-gateway"

        # Expires in should be positive (token not expired)
        assert validation_data["expires_in"] > 0

    def test_multiple_jwt_tokens_for_same_service_are_unique(self, jwt_client):
        """Test that multiple tokens for the same service have unique JTIs."""
        service_name = "multi-token-test-service"
        tokens = []

        # Get 5 tokens for the same service
        for i in range(5):
            response = jwt_client.post("/token", json={"service_name": service_name})

            assert response.status_code == 200
            tokens.append(response.json()["token"])

        # All tokens should be different
        assert len(set(tokens)) == len(tokens)

        # All JTIs should be unique
        jtis = []
        for token in tokens:
            payload = jwt.decode(token, options={"verify_signature": False})
            jtis.append(payload["jti"])

        assert len(set(jtis)) == len(jtis)

        # But all tokens should be for the same service
        for token in tokens:
            payload = jwt.decode(token, options={"verify_signature": False})
            assert payload["sub"] == service_name

    def test_jwt_token_without_scope_works(self, jwt_client):
        """Test that JWT tokens work without scope claim."""
        response = jwt_client.post("/token", json={"service_name": "no-scope-service"})

        assert response.status_code == 200
        token = response.json()["token"]

        # Token should still be valid without scope
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == "no-scope-service"

        # Scope may be missing or empty
        scope = payload.get("scope")
        assert scope is None or scope == ""

    def test_jwt_token_timestamp_accuracy(self, jwt_client):
        """Test that JWT timestamps are accurate."""
        before_request = int(time.time())

        response = jwt_client.post("/token", json={"service_name": "timestamp-test-service"})
        response = jwt_client.post(
            "/token", json={"service_name": "timestamp-test-service"}
        )

        after_request = int(time.time())

        token = response.json()["token"]
        payload = jwt.decode(token, options={"verify_signature": False})

        # iat should be between before and after request
        assert before_request <= payload["iat"] <= after_request

        # exp should be iat + expiry duration (default 1 hour)
        expected_exp = payload["iat"] + 3600  # 1 hour in seconds
        assert abs(payload["exp"] - expected_exp) <= 1  # Allow 1 second tolerance
