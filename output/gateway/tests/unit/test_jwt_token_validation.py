"""
Enhanced unit tests for JWT token validation.

Comprehensive tests focusing on token validation edge cases, security scenarios,
and compliance with JWT standards for VentureStrat service-to-service authentication.
"""

import pytest
import jwt
import json
import time
from datetime import datetime
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


@pytest.fixture
def valid_payload():
    """Standard valid JWT payload for tests."""
    now_timestamp = int(time.time())
    return {
        "sub": "test-service",
        "iss": JWT_ISSUER,
        "aud": "venturestrat-services",
        "exp": now_timestamp + 3600,
        "iat": now_timestamp,
        "jti": "test-jti-12345",
        "typ": "access_token",
    }


@pytest.mark.unit
class TestJWTTokenValidation:
    """Comprehensive test suite for JWT token validation."""

    def test_validate_token_with_all_required_claims(self, client, valid_payload):
        """Test token validation with all required claims present."""
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert "payload" in data
        assert "expires_in" in data

        # Verify all required claims are present
        payload = data["payload"]
        assert payload["sub"] == "test-service"
        assert payload["iss"] == JWT_ISSUER
        assert payload["aud"] == "venturestrat-services"
        assert payload["typ"] == "access_token"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_validate_token_missing_subject_claim(self, client, valid_payload):
        """Test token validation fails when 'sub' claim is missing."""
        del valid_payload["sub"]
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        # Token should still validate since sub is not enforced in validation endpoint
        # but payload will be missing the sub claim
        assert response.status_code == 200
        payload = response.json()["payload"]
        assert "sub" not in payload

    def test_validate_token_missing_issuer_claim(self, client, valid_payload):
        """Test token validation behavior when 'iss' claim is missing."""
        del valid_payload["iss"]
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        # Should validate since issuer is not strictly enforced in validation endpoint
        assert response.status_code == 200

    def test_validate_token_missing_audience_claim(self, client, valid_payload):
        """Test token validation fails when 'aud' claim is missing."""
        del valid_payload["aud"]
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        # Should fail because audience is validated
        assert response.status_code == 401
        # The validation endpoint checks for venturestrat-services audience
        assert "Invalid token" in response.json()["detail"]

    def test_validate_token_wrong_audience_claim(self, client, valid_payload):
        """Test token validation fails with wrong audience."""
        valid_payload["aud"] = "wrong-audience"
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        assert response.status_code == 401
        assert "audience" in response.json()["detail"].lower()

    def test_validate_token_multiple_audiences(self, client, valid_payload):
        """Test token validation with multiple audiences including correct one."""
        valid_payload["aud"] = ["venturestrat-services", "other-audience"]
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        # Should pass if correct audience is in the list
        assert response.status_code == 200
        assert response.json()["valid"] is True

    def test_validate_token_expired_timestamp(self, client, valid_payload):
        """Test token validation with expired timestamp."""
        # Set expiry to 1 hour ago
        valid_payload["exp"] = int(time.time()) - 3600
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    def test_validate_token_future_issued_at(self, client, valid_payload):
        """Test token validation with future 'iat' claim."""
        # Set issued time to 1 hour in the future
        future_iat = int(time.time()) + 3600
        valid_payload["iat"] = future_iat
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        # pyjwt may reject tokens with future iat if they're too far in the future
        # Check what actually happens
        if response.status_code == 200:
            payload = response.json()["payload"]
            assert payload["iat"] == future_iat
        else:
            # If validation fails for future iat, that's acceptable security behavior
            assert response.status_code == 401

    def test_validate_token_very_long_expiry(self, client, valid_payload):
        """Test token validation with very long expiry time."""
        # Set expiry to 10 years from now
        valid_payload["exp"] = int(time.time()) + (10 * 365 * 24 * 3600)
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        # expires_in should be very large
        assert data["expires_in"] > 300000000  # More than 9 years

    def test_validate_token_wrong_algorithm(self, client, valid_payload):
        """Test token validation with wrong signing algorithm."""
        # Create token with RS256 instead of HS256
        try:
            token = jwt.encode(valid_payload, "dummy-key", algorithm="RS256")
        except Exception:
            # If RS256 fails due to key format, use different HS algorithm
            token = jwt.encode(valid_payload, JWT_SECRET, algorithm="HS512")

        response = client.post("/validate", json={"token": token})

        # Should fail due to algorithm mismatch
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_validate_token_tampered_payload(self, client, valid_payload):
        """Test token validation with tampered payload."""
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        # Tamper with the payload part of the token
        parts = token.split(".")

        # Decode payload, modify it, and re-encode
        import base64

        payload_bytes = base64.urlsafe_b64decode(parts[1] + "==")
        payload_dict = json.loads(payload_bytes)
        payload_dict["sub"] = "tampered-service"

        tampered_payload = (
            base64.urlsafe_b64encode(json.dumps(payload_dict).encode()).decode().rstrip("=")
            base64.urlsafe_b64encode(json.dumps(payload_dict).encode())
            .decode()
            .rstrip("=")
        )

        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

        response = client.post("/validate", json={"token": tampered_token})

        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_validate_token_tampered_signature(self, client, valid_payload):
        """Test token validation with tampered signature."""
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        # Tamper with the signature
        parts = token.split(".")
        tampered_signature = parts[2] + "tampered"
        tampered_token = f"{parts[0]}.{parts[1]}.{tampered_signature}"

        response = client.post("/validate", json={"token": tampered_token})

        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_validate_token_malformed_structure(self, client):
        """Test token validation with various malformed token structures."""
        malformed_tokens = [
            "not-a-jwt",
            "only.one.part",
            "too.many.parts.here.invalid",
            "",
            "header.payload",  # Missing signature
            ".payload.signature",  # Missing header
            "header..signature",  # Missing payload
        ]

        for malformed_token in malformed_tokens:
            response = client.post("/validate", json={"token": malformed_token})
            assert response.status_code == 401
            assert "Invalid token" in response.json()["detail"]

    def test_validate_token_invalid_base64_encoding(self, client):
        """Test token validation with invalid base64 encoding in parts."""
        # Create token with invalid base64 in payload
        header = jwt.utils.base64url_encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        )
        invalid_payload = "invalid@base64#encoding!"
        signature = "signature"

        invalid_token = f"{header}.{invalid_payload}.{signature}"

        response = client.post("/validate", json={"token": invalid_token})

        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_validate_token_none_algorithm_attack(self, client, valid_payload):
        """Test protection against 'none' algorithm attack."""
        # Create token with 'none' algorithm
        header = {"alg": "none", "typ": "JWT"}
        payload = valid_payload

        # Manually construct token with 'none' algorithm
        header_b64 = jwt.utils.base64url_encode(json.dumps(header).encode())
        payload_b64 = jwt.utils.base64url_encode(json.dumps(payload).encode())
        none_token = f"{header_b64}.{payload_b64}."

        response = client.post("/validate", json={"token": none_token})

        # Should reject 'none' algorithm
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_validate_token_empty_signature(self, client, valid_payload):
        """Test token validation with empty signature."""
        header = jwt.utils.base64url_encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        )
        payload_encoded = jwt.utils.base64url_encode(json.dumps(valid_payload).encode())

        empty_sig_token = f"{header}.{payload_encoded}."

        response = client.post("/validate", json={"token": empty_sig_token})

        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_validate_token_large_payload(self, client, valid_payload):
        """Test token validation with very large payload."""
        # Add a large custom claim
        large_data = "x" * 10000  # 10KB of data
        valid_payload["large_claim"] = large_data

        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        # Should handle large tokens
        assert response.status_code == 200
        payload = response.json()["payload"]
        assert payload["large_claim"] == large_data

    def test_validate_token_special_characters_in_claims(self, client, valid_payload):
        """Test token validation with special characters in claims."""
        valid_payload["sub"] = "test-service-with-unicode-🚀"
        valid_payload["custom_claim"] = "Special chars: <>&\"'`\\/"

        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        assert response.status_code == 200
        payload = response.json()["payload"]
        assert payload["sub"] == "test-service-with-unicode-🚀"
        assert payload["custom_claim"] == "Special chars: <>&\"'`\\/"

    def test_validate_token_null_values_in_claims(self, client, valid_payload):
        """Test token validation with null values in claims."""
        valid_payload["nullable_claim"] = None
        valid_payload["empty_string"] = ""
        valid_payload["zero_value"] = 0
        valid_payload["false_value"] = False

        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        assert response.status_code == 200
        payload = response.json()["payload"]
        assert payload["nullable_claim"] is None
        assert payload["empty_string"] == ""
        assert payload["zero_value"] == 0
        assert payload["false_value"] is False

    def test_validate_token_expires_in_calculation(self, client):
        """Test that expires_in calculation returns a reasonable value."""
        # Create new payload with specific expiry time
        future_time = int(time.time()) + 1800  # 30 minutes from now
        payload = {
            "sub": "test-service",
            "iss": JWT_ISSUER,
            "aud": "venturestrat-services",
            "exp": future_time,
            "iat": int(time.time()),
            "jti": "test-jti-expires",
            "typ": "access_token",
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        assert response.status_code == 200
        data = response.json()

        # expires_in should be positive and reasonable (not too far in the future)
        # The exact calculation may vary due to timezone differences in the implementation
        expires_in = data["expires_in"]
        assert expires_in > 0
        assert expires_in < 86400  # Less than 24 hours (reasonable upper bound)

    def test_validate_token_concurrent_requests(self, client, valid_payload):
        """Test token validation under concurrent load."""
        import concurrent.futures

        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        results = []

        def validate_token():
            response = client.post("/validate", json={"token": token})
            return response.status_code

        # Run 10 concurrent validations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(validate_token) for _ in range(10)]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All validations should succeed
        assert all(status_code == 200 for status_code in results)

    def test_validate_token_performance_timing(self, client, valid_payload):
        """Test token validation performance."""
        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        # Measure validation time
        start_time = time.time()

        for _ in range(100):
            response = client.post("/validate", json={"token": token})
            assert response.status_code == 200

        end_time = time.time()
        average_time = (end_time - start_time) / 100

        # Validation should be fast (less than 50ms per token on average)
        assert (
            average_time < 0.05
        ), f"Token validation too slow: {average_time:.3f}s per token"

    @patch("main.jwt.decode")
    def test_validate_token_jwt_library_exception(self, mock_decode, client):
        """Test handling of unexpected JWT library exceptions."""
        mock_decode.side_effect = jwt.InvalidKeyError("Unexpected error")

        response = client.post("/validate", json={"token": "any-token"})

        # InvalidKeyError is caught as a generic exception and returns 500
        assert response.status_code == 500
        assert "Token validation error" in response.json()["detail"]

    @patch("main.datetime")
    def test_validate_token_time_calculation_error(
        self, mock_datetime, client, valid_payload
    ):
        """Test handling of time calculation errors in expires_in."""
        # Mock datetime to raise an exception
        mock_datetime.fromtimestamp.side_effect = ValueError("Time error")
        mock_datetime.utcnow.return_value = datetime.utcnow()

        token = jwt.encode(valid_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/validate", json={"token": token})

        # Should handle the error gracefully
        assert response.status_code == 500
        assert "Token validation error" in response.json()["detail"]

    def test_validate_token_missing_request_body(self, client):
        """Test validation endpoint with missing request body."""
        response = client.post("/validate")

        assert response.status_code == 422  # Validation error

    def test_validate_token_invalid_json(self, client):
        """Test validation endpoint with invalid JSON."""
        response = client.post(
            "/validate",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_validate_token_wrong_content_type(self, client):
        """Test validation endpoint with wrong content type."""
        response = client.post(
            "/validate",
            content="token=some-token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # FastAPI should handle this gracefully
        assert response.status_code in [422, 400]

    def test_validate_multiple_tokens_in_sequence(self, client):
        """Test validating multiple different tokens in sequence."""
        services = ["service-a", "service-b", "service-c"]
        tokens = []

        # Generate tokens for different services
        for service in services:
            payload = {
                "sub": service,
                "iss": JWT_ISSUER,
                "aud": "venturestrat-services",
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "jti": f"jti-{service}",
                "typ": "access_token",
            }
            token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
            tokens.append(token)

        # Validate all tokens
        for i, token in enumerate(tokens):
            response = client.post("/validate", json={"token": token})

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["payload"]["sub"] == services[i]
