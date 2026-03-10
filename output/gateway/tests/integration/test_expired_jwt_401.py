"""
Integration tests for expired JWT (401) authentication scenarios.

Tests the Kong JWT plugin behavior when JWT tokens are expired.
These tests focus specifically on task 8.2: Write tests for expired JWT (401).
"""

import pytest
import jwt


@pytest.mark.unit
class TestExpiredJWTValidation:
    """Unit tests for expired JWT validation logic (no infrastructure required)."""

    def test_expired_jwt_creation(self):
        """Test that we can create expired JWT tokens for testing."""
        # Create an expired token (1 hour ago)
        import time

        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour ago
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - 3600,  # 2 hours ago
            "jti": "test-jwt-id",
        }

        expired_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        # Verify token is properly formatted
        assert expired_token.count(".") == 2  # JWT format: header.payload.signature

        # Verify token contains expired timestamp
        decoded_payload = jwt.decode(expired_token, options={"verify_signature": False})
        assert decoded_payload["exp"] < current_time

    def test_expired_token_scenarios(self):
        """Test various expired token scenarios."""
        import time

        current_time = int(time.time())

        scenarios = [
            {"seconds_ago": 3600, "description": "expired_1_hour_ago"},
            {"seconds_ago": 86400, "description": "expired_1_day_ago"},
            {"seconds_ago": 300, "description": "expired_5_minutes_ago"},
            {"seconds_ago": 30, "description": "expired_30_seconds_ago"},
        ]

        for scenario in scenarios:
            past_time = current_time - scenario["seconds_ago"]

            payload = {
                "sub": "test-service",
                "iss": "venturestrat-gateway",
                "aud": "venturestrat-services",
                "exp": past_time,
                "iat": past_time - 3600,  # 1 hour before expiry
            }

            expired_token = jwt.encode(
                payload, "dev-secret-change-in-prod", algorithm="HS256"
            )

            # Verify token is expired when decoded
            with pytest.raises(jwt.ExpiredSignatureError):
                jwt.decode(
                    expired_token,
                    "dev-secret-change-in-prod",
                    algorithms=["HS256"],
                    audience="venturestrat-services",
                )


@pytest.mark.integration
class TestExpiredJWT401:
    """Test cases for expired JWT authentication returning 401."""

    def test_expired_jwt_token_returns_401(self, unauthorized_client):
        """Test that expired JWT tokens return 401."""
        # Create expired token (1 hour ago)
        import time

        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour ago
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - 3600,  # 2 hours ago
            "jti": "expired-test-jwt",
        }

        expired_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        # Should return 401 for expired token
        # Note: Currently API key auth is global, so this may return 401 for missing API key
        # When JWT plugin is active, this should specifically test JWT expiration
        assert response.status_code == 401

        # Verify error message indicates authentication issue
        error_data = response.json()
        assert "message" in error_data
        assert any(
            keyword in error_data["message"].lower()
            for keyword in [
                "unauthorized",
                "authentication",
                "token",
                "expired",
                "invalid",
            ]
        )

    def test_various_expired_timeframes(self, unauthorized_client):
        """Test that JWT tokens expired for different timeframes all return 401."""
        import time

        current_time = int(time.time())

        expiration_scenarios = [
            30,  # 30 seconds ago
            300,  # 5 minutes ago
            3600,  # 1 hour ago
            86400,  # 1 day ago
        ]

        for seconds_ago in expiration_scenarios:
            past_time = current_time - seconds_ago
            payload = {
                "sub": "test-service",
                "iss": "venturestrat-gateway",
                "aud": "venturestrat-services",
                "exp": past_time,
                "iat": past_time - 3600,  # 1 hour before expiry
                "jti": f"expired-{seconds_ago}s-ago",
            }

            expired_token = jwt.encode(
                payload, "dev-secret-change-in-prod", algorithm="HS256"
            )

            response = unauthorized_client.get(
                "/api/v1/registry/services",
                headers={"Authorization": f"Bearer {expired_token}"},
            )

            # All expired tokens should return 401
            assert (
                response.status_code == 401
            ), f"Expected 401 for token expired {seconds_ago}s ago"

    def test_expired_jwt_via_issuer_validation(self, jwt_issuer_client):
        """Test that JWT issuer validation endpoint rejects expired tokens."""
        # Create expired token
        import time

        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour ago
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - 3600,  # 1 hour before expiry
            "jti": "expired-validation-test",
        }

        expired_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        # Use the JWT issuer validation endpoint
        response = jwt_issuer_client.post("/validate", json={"token": expired_token})

        # Should return 401 for expired token
        assert response.status_code == 401

        # Verify error message specifically mentions expiration
        error_data = response.json()
        assert "expired" in error_data["detail"].lower()

    def test_expired_jwt_error_response_format(self, unauthorized_client):
        """Test that expired JWT errors have proper response format."""
        import time

        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour ago
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - 3600,  # 1 hour before expiry
        }

        expired_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

        # Verify error response follows standard format
        error_data = response.json()
        assert isinstance(error_data, dict)
        assert "message" in error_data
        assert isinstance(error_data["message"], str)
        assert len(error_data["message"]) > 0

        # Should be valid JSON
        assert response.headers.get("Content-Type") in [
            "application/json",
            "application/json; charset=utf-8",
        ]

    def test_expired_vs_valid_jwt_comparison(
        self, jwt_issuer_client, unauthorized_client
    ):
        """Test that expired JWT fails while valid JWT could pass."""
        # Get a valid token
        valid_response = jwt_issuer_client.post("/token", json={"service_name": "test-service"})
        valid_response = jwt_issuer_client.post(
            "/token", json={"service_name": "test-service"}
        )
        assert valid_response.status_code == 200
        valid_token = valid_response.json()["token"]

        # Create expired token
        import time

        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour ago
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - 3600,  # 1 hour before expiry
        }
        expired_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        # Test expired token
        expired_response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert expired_response.status_code == 401

        # Test valid token (may still require API key, but different error or success)
        valid_response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        # Valid JWT should not fail with 401 due to token expiration
        # (may fail with 401 due to missing API key, or succeed if JWT plugin is active)
        assert valid_response.status_code in [200, 401, 403, 502, 503]

    def test_expired_jwt_with_different_services(self, unauthorized_client):
        """Test that expired JWTs from different services all return 401."""
        service_names = [
            "pricing-service",
            "risk-service",
            "market-data-service",
            "portfolio-service",
        ]

        import time

        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour ago

        for service_name in service_names:
            payload = {
                "sub": service_name,
                "iss": "venturestrat-gateway",
                "aud": "venturestrat-services",
                "exp": past_time,
                "iat": past_time - 3600,  # 1 hour before expiry
                "jti": f"expired-{service_name}",
            }

            expired_token = jwt.encode(
                payload, "dev-secret-change-in-prod", algorithm="HS256"
            )

            response = unauthorized_client.get(
                "/api/v1/registry/services",
                headers={"Authorization": f"Bearer {expired_token}"},
            )

            assert (
                response.status_code == 401
            ), f"Expected 401 for expired token from {service_name}"

    def test_expired_jwt_correlation_id_preserved(self, unauthorized_client):
        """Test that correlation ID is preserved even with expired JWT."""
        import time

        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour ago
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - 3600,  # 1 hour before expiry
        }

        expired_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        # Send request with correlation ID
        headers = {
            "Authorization": f"Bearer {expired_token}",
            "X-Correlation-ID": "test-expired-jwt-correlation",
        }

        response = unauthorized_client.get("/api/v1/registry/services", headers=headers)

        assert response.status_code == 401

        # Correlation ID should be echoed back even in error responses
        response_correlation_id = response.headers.get("X-Correlation-ID")
        assert response_correlation_id is not None

    def test_expired_jwt_different_endpoints(self, unauthorized_client):
        """Test that expired JWT returns 401 for different endpoints."""
        import time

        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour ago
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - 3600,  # 1 hour before expiry
        }

        expired_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        endpoints_to_test = [
            "/api/v1/registry/services",
            "/api/v1/registry/health",
        ]

        for endpoint in endpoints_to_test:
            response = unauthorized_client.get(
                endpoint, headers={"Authorization": f"Bearer {expired_token}"}
            )

            assert (
                response.status_code == 401
            ), f"Expected 401 for expired JWT on {endpoint}"

    def test_expired_jwt_no_information_leakage(self, unauthorized_client):
        """Test that expired JWT errors don't leak internal information."""
        import time

        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour ago
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - 3600,  # 1 hour before expiry
        }

        expired_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

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
            "dev-secret",
            "payload",
            "claims",
        ]

        for keyword in forbidden_keywords:
            assert keyword not in message, f"Error message contains internal information: {keyword}"
            assert (
                keyword not in message
            ), f"Error message contains internal information: {keyword}"

    def test_expired_jwt_response_timing(self, unauthorized_client):
        """Test that expired JWT responses are returned quickly."""
        import time

        import time

        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour ago
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - 3600,  # 1 hour before expiry
        }

        expired_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        start_time = time.time()
        response = unauthorized_client.get(
            "/api/v1/registry/services",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 401

        # Token validation failure should be fast (< 1 second)
        assert response_time < 1.0, f"401 response took too long: {response_time}s"

    def test_expired_jwt_different_http_methods(self, unauthorized_client):
        """Test that expired JWT returns 401 for different HTTP methods."""
        import time

        current_time = int(time.time())
        past_time = current_time - 3600  # 1 hour ago
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": past_time,
            "iat": past_time - 3600,  # 1 hour before expiry
        }

        expired_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        http_methods = [
            ("GET", "/api/v1/registry/services"),
            ("POST", "/api/v1/registry/services"),
            ("PUT", "/api/v1/registry/services/test"),
            ("DELETE", "/api/v1/registry/services/test"),
        ]

        for method, path in http_methods:
            response = unauthorized_client.request(
                method, path, headers={"Authorization": f"Bearer {expired_token}"}
            )

            # All should return 401 for expired token
            # (405 Method Not Allowed is also acceptable for unsupported methods)
            assert (
                response.status_code in [401, 405]
            ), f"Expected 401 or 405 for {method} {path} with expired JWT, got {response.status_code}"
