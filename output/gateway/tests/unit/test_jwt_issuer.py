"""
Unit tests for JWT issuer service.

Tests JWT token generation, validation, and error handling.
"""

import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient

# Import the JWT issuer application
import sys
from pathlib import Path

# Add jwt-issuer directory to Python path for imports
jwt_issuer_path = Path(__file__).parent.parent.parent / "jwt-issuer"
sys.path.insert(0, str(jwt_issuer_path))

# Import from jwt-issuer main module specifically
import importlib.util

spec = importlib.util.spec_from_file_location("jwt_main", jwt_issuer_path / "main.py")
jwt_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jwt_main)

app = jwt_main.app
JWT_SECRET = jwt_main.JWT_SECRET
JWT_ISSUER = jwt_main.JWT_ISSUER
JWT_ALGORITHM = jwt_main.JWT_ALGORITHM
JWT_EXPIRY_HOURS = jwt_main.JWT_EXPIRY_HOURS


@pytest.fixture
def client():
    """Test client for JWT issuer service."""
    return TestClient(app)


@pytest.mark.unit
class TestJWTIssuerService:
    """Test suite for JWT issuer service."""

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

        # Validate timestamp format
        timestamp = data["timestamp"]
        assert timestamp.endswith("Z")
        datetime.fromisoformat(timestamp[:-1])  # Should parse without error

    def test_issue_token_valid_request(self, client):
        """Test token issuance with valid request."""
        request_data = {"service_name": "pricing-service", "scope": "read:prices"}

        response = client.post("/token", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "token" in data
        assert data["token_type"] == "Bearer"
        assert "expires_at" in data
        assert "expires_in" in data
        assert data["expires_in"] == JWT_EXPIRY_HOURS * 3600

        # Verify JWT token format
        token = data["token"]
        assert isinstance(token, str)
        assert token.count(".") == 2  # JWT format: header.payload.signature

    def test_issue_token_missing_service_name(self, client):
        """Test token issuance with missing service name."""
        request_data = {"scope": "read:prices"}

        response = client.post("/token", json=request_data)

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    def test_issue_token_empty_service_name(self, client):
        """Test token issuance with empty service name."""
        request_data = {"service_name": ""}

        response = client.post("/token", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "Service name is required" in data["detail"]

    def test_issue_token_whitespace_service_name(self, client):
        """Test token issuance with whitespace-only service name."""
        request_data = {"service_name": "   "}

        response = client.post("/token", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "Service name is required" in data["detail"]

    def test_token_has_required_claims(self, client):
        """Test that issued token contains required claims."""
        request_data = {"service_name": "test-service"}

        response = client.post("/token", json=request_data)
        assert response.status_code == 200

        token = response.json()["token"]

        # Decode token without verification for claim inspection
        unverified_payload = jwt.decode(token, options={"verify_signature": False})

        # Verify required claims
        assert unverified_payload["sub"] == "test-service"
        assert unverified_payload["iss"] == JWT_ISSUER
        assert unverified_payload["aud"] == "venturestrat-services"
        assert unverified_payload["typ"] == "access_token"
        assert "exp" in unverified_payload
        assert "iat" in unverified_payload
        assert "jti" in unverified_payload

    def test_token_expiry(self, client):
        """Test that token expires in the expected time."""
        import time

        request_data = {"service_name": "test-service"}

        issue_timestamp = int(time.time())
        response = client.post("/token", json=request_data)
        assert response.status_code == 200

        data = response.json()
        token = data["token"]

        # Decode token
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience="venturestrat-services",
        )

        # Verify expiry is approximately correct using timestamps
        exp_timestamp = payload["exp"]
        expected_exp_timestamp = issue_timestamp + (JWT_EXPIRY_HOURS * 3600)

        # Allow 5 second tolerance
        time_diff = abs(exp_timestamp - expected_exp_timestamp)
        assert time_diff < 5

    def test_token_signature_valid(self, client):
        """Test that token signature validates correctly."""
        request_data = {"service_name": "test-service"}

        response = client.post("/token", json=request_data)
        assert response.status_code == 200

        token = response.json()["token"]

        # This should not raise an exception
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience="venturestrat-services",
        )

        assert payload["sub"] == "test-service"

    def test_token_with_scope(self, client):
        """Test token issuance with scope."""
        request_data = {"service_name": "risk-service", "scope": "read:risk write:risk"}

        response = client.post("/token", json=request_data)
        assert response.status_code == 200

        token = response.json()["token"]

        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience="venturestrat-services",
        )

        assert payload["scope"] == "read:risk write:risk"

    def test_token_without_scope(self, client):
        """Test token issuance without scope."""
        request_data = {"service_name": "test-service"}

        response = client.post("/token", json=request_data)
        assert response.status_code == 200

        token = response.json()["token"]

        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience="venturestrat-services",
        )

        assert "scope" not in payload

    def test_validate_token_valid(self, client):
        """Test token validation with valid token."""
        # First, issue a token
        request_data = {"service_name": "test-service"}
        response = client.post("/token", json=request_data)
        token = response.json()["token"]

        # Then validate it
        response = client.post("/validate", json={"token": token})

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert "payload" in data
        assert "expires_in" in data
        assert data["expires_in"] > 0

    def test_validate_token_expired(self, client):
        """Test token validation with expired token."""
        # Create an expired token
        past_time = datetime.utcnow() - timedelta(hours=1)
        payload = {
            "sub": "test-service",
            "iss": JWT_ISSUER,
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - timedelta(hours=1),
            "jti": "test-jti",
        }

        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": expired_token})

        assert response.status_code == 401
        data = response.json()
        assert "expired" in data["detail"].lower()

    def test_validate_token_invalid_signature(self, client):
        """Test token validation with invalid signature."""
        # Create a token with wrong secret
        payload = {
            "sub": "test-service",
            "iss": JWT_ISSUER,
            "aud": "venturestrat-services",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "jti": "test-jti",
        }

        invalid_token = jwt.encode(payload, "wrong-secret", algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": invalid_token})

        assert response.status_code == 401
        data = response.json()
        assert "Invalid token" in data["detail"]

    def test_validate_token_malformed(self, client):
        """Test token validation with malformed token."""
        malformed_token = "not.a.valid.jwt.token"

        response = client.post("/validate", json={"token": malformed_token})

        assert response.status_code == 401
        data = response.json()
        assert "Invalid token" in data["detail"]

    def test_unique_jti_per_request(self, client):
        """Test that each token has a unique JTI."""
        request_data = {"service_name": "test-service"}

        # Issue two tokens
        response1 = client.post("/token", json=request_data)
        response2 = client.post("/token", json=request_data)

        token1 = response1.json()["token"]
        token2 = response2.json()["token"]

        # Decode both tokens
        payload1 = jwt.decode(token1, options={"verify_signature": False})
        payload2 = jwt.decode(token2, options={"verify_signature": False})

        # JTI should be different
        assert payload1["jti"] != payload2["jti"]

    @patch("main.jwt.encode")
    def test_jwt_encoding_error(self, mock_encode, client):
        """Test error handling when JWT encoding fails."""
        mock_encode.side_effect = jwt.InvalidKeyError("Invalid key")

        request_data = {"service_name": "test-service"}
        response = client.post("/token", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert "Internal server error" in data["detail"]

    def test_expires_at_iso_format(self, client):
        """Test that expires_at is in proper ISO format with Z suffix."""
        request_data = {"service_name": "test-service"}

        response = client.post("/token", json=request_data)
        assert response.status_code == 200

        expires_at = response.json()["expires_at"]

        # Should end with Z (UTC indicator)
        assert expires_at.endswith("Z")

        # Should parse as ISO format
        datetime.fromisoformat(expires_at[:-1])  # Remove Z for parsing
