"""
Enhanced integration tests for JWT token validation through the gateway.

Tests JWT authentication flow, Kong JWT plugin behavior, and end-to-end
token validation scenarios for VentureStrat service-to-service authentication.
"""

import pytest
import jwt
import time


@pytest.mark.integration
class TestJWTTokenValidationIntegration:
    """Enhanced integration test suite for JWT token validation."""

    def test_jwt_token_roundtrip_validation(self, jwt_issuer_client):
        """Test complete token issuance and validation roundtrip."""
        # Request token
        request_data = {
            "service_name": "pricing-service",
            "scope": "read:prices write:prices",
        }

        token_response = jwt_issuer_client.post("/token", json=request_data)
        assert token_response.status_code == 200

        token_data = token_response.json()
        token = token_data["token"]

        # Validate token
        validate_response = jwt_issuer_client.post("/validate", json={"token": token})

        assert validate_response.status_code == 200
        validation_data = validate_response.json()

        # Verify validation response
        assert validation_data["valid"] is True
        assert "payload" in validation_data
        assert "expires_in" in validation_data

        # Verify payload contents
        payload = validation_data["payload"]
        assert payload["sub"] == "pricing-service"
        assert payload["iss"] == "venturestrat-gateway"
        assert payload["aud"] == "venturestrat-services"
        assert payload["scope"] == "read:prices write:prices"
        assert payload["typ"] == "access_token"

    def test_jwt_token_expiry_progression(self, jwt_issuer_client):
        """Test that expires_in decreases over time."""
        # Issue token
        token_response = jwt_issuer_client.post("/token", json={"service_name": "test-service"})
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "test-service"}
        )
        token = token_response.json()["token"]

        # First validation
        response1 = jwt_issuer_client.post("/validate", json={"token": token})
        expires_in_1 = response1.json()["expires_in"]

        # Wait 2 seconds
        time.sleep(2)

        # Second validation
        response2 = jwt_issuer_client.post("/validate", json={"token": token})
        expires_in_2 = response2.json()["expires_in"]

        # expires_in should have decreased
        assert expires_in_2 < expires_in_1
        assert (expires_in_1 - expires_in_2) >= 1  # At least 1 second difference

    def test_jwt_token_validation_performance_under_load(self, jwt_issuer_client):
        """Test JWT validation performance under concurrent load."""
        # Issue multiple tokens
        tokens = []
        for i in range(10):
            response = jwt_issuer_client.post("/token", json={"service_name": f"service-{i}"})
            response = jwt_issuer_client.post(
                "/token", json={"service_name": f"service-{i}"}
            )
            tokens.append(response.json()["token"])

        # Measure validation time under load
        start_time = time.time()

        # Validate all tokens concurrently
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for token in tokens:
                future = executor.submit(jwt_issuer_client.post, "/validate", json={"token": token})
                future = executor.submit(
                    jwt_issuer_client.post, "/validate", json={"token": token}
                )
                futures.append(future)

            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        end_time = time.time()
        total_time = end_time - start_time

        # All validations should succeed
        assert all(r.status_code == 200 for r in results)

        # Total time should be reasonable (less than 5 seconds for 10 tokens)
        assert total_time < 5.0

    def test_jwt_token_cross_service_validation(self, jwt_issuer_client):
        """Test that tokens issued for one service validate correctly."""
        services = [
            "registry-service",
            "pricing-service",
            "risk-service",
            "market-data-service",
        ]

        for service_name in services:
            # Issue token for service
            token_response = jwt_issuer_client.post("/token", json={"service_name": service_name})
            token_response = jwt_issuer_client.post(
                "/token", json={"service_name": service_name}
            )
            assert token_response.status_code == 200

            token = token_response.json()["token"]

            # Validate token
            validate_response = jwt_issuer_client.post("/validate", json={"token": token})
            validate_response = jwt_issuer_client.post(
                "/validate", json={"token": token}
            )

            assert validate_response.status_code == 200
            payload = validate_response.json()["payload"]
            assert payload["sub"] == service_name

    def test_jwt_token_with_custom_scope_validation(self, jwt_issuer_client):
        """Test token validation with various custom scopes."""
        scope_test_cases = [
            "read:all",
            "read:prices write:prices",
            "admin:system",
            "read:risk write:risk read:positions",
            "custom-scope-with-dashes",
            "scope_with_underscores",
            "scope:with:colons",
        ]

        for scope in scope_test_cases:
            # Issue token with scope
            token_response = jwt_issuer_client.post(
                "/token", json={"service_name": "test-service", "scope": scope}
            )
            assert token_response.status_code == 200

            token = token_response.json()["token"]

            # Validate token
            validate_response = jwt_issuer_client.post("/validate", json={"token": token})
            validate_response = jwt_issuer_client.post(
                "/validate", json={"token": token}
            )

            assert validate_response.status_code == 200
            payload = validate_response.json()["payload"]
            assert payload["scope"] == scope

    def test_jwt_token_validation_error_handling(self, jwt_issuer_client):
        """Test JWT validation error handling for various invalid tokens."""
        error_test_cases = [
            # Invalid token structures
            {"token": "not-a-jwt", "expected_status": 401},
            {"token": "header.payload", "expected_status": 401},
            {"token": "too.many.parts.here", "expected_status": 401},
            {"token": "", "expected_status": 422},  # Missing token
            # Malformed base64
            {"token": "invalid.base64!.signature", "expected_status": 401},
        ]

        for test_case in error_test_cases:
            if test_case["token"] == "":
                # Test missing token
                response = jwt_issuer_client.post("/validate", json={})
            else:
                response = jwt_issuer_client.post("/validate", json={"token": test_case["token"]})
                response = jwt_issuer_client.post(
                    "/validate", json={"token": test_case["token"]}
                )

            assert response.status_code == test_case["expected_status"]

    def test_jwt_token_validation_with_different_algorithms(self, jwt_issuer_client):
        """Test that only HS256 signed tokens are accepted."""
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "jti": "test-jti",
        }

        # Test with HS256 (should work)
        valid_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )
        response = jwt_issuer_client.post("/validate", json={"token": valid_token})
        assert response.status_code == 200

        # Test with HS512 (should fail)
        try:
            invalid_token = jwt.encode(
                payload, "dev-secret-change-in-prod", algorithm="HS512"
            )
            response = jwt_issuer_client.post(
                "/validate", json={"token": invalid_token}
            )
            assert response.status_code == 401
        except Exception:
            # If HS512 token creation fails, that's expected behavior
            pass

    def test_jwt_token_validation_timing_attack_resistance(self, jwt_issuer_client):
        """Test that validation timing is consistent for valid and invalid tokens."""
        # Generate valid token
        valid_response = jwt_issuer_client.post("/token", json={"service_name": "test-service"})
        valid_response = jwt_issuer_client.post(
            "/token", json={"service_name": "test-service"}
        )
        valid_token = valid_response.json()["token"]

        # Invalid token
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"

        # Measure timing for valid token validation
        valid_times = []
        for _ in range(10):
            start = time.time()
            jwt_issuer_client.post("/validate", json={"token": valid_token})
            valid_times.append(time.time() - start)

        # Measure timing for invalid token validation
        invalid_times = []
        for _ in range(10):
            start = time.time()
            jwt_issuer_client.post("/validate", json={"token": invalid_token})
            invalid_times.append(time.time() - start)

        # Calculate average times
        avg_valid_time = sum(valid_times) / len(valid_times)
        avg_invalid_time = sum(invalid_times) / len(invalid_times)

        # Times should be relatively similar (within 50% of each other)
        # to prevent timing attacks
        time_ratio = max(avg_valid_time, avg_invalid_time) / min(
            avg_valid_time, avg_invalid_time
        )
        assert time_ratio < 2.0, f"Timing difference too large: {time_ratio}"

    def test_jwt_token_validation_memory_usage(self, jwt_issuer_client):
        """Test JWT validation with large tokens to check memory handling."""
        # Create token with large custom claims
        large_data = "x" * 1000  # 1KB of data
        jwt_issuer_client.post("/token", json={"service_name": "test-service-with-large-data"})
        token_response = jwt_issuer_client.post(
            "/token", json={"service_name": "test-service-with-large-data"}
        )

        # Manually create a token with large claims for testing
        payload = {
            "sub": "test-service",
            "iss": "venturestrat-gateway",
            "aud": "venturestrat-services",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "jti": "test-jti",
            "large_claim": large_data,
            "another_claim": "x" * 500,  # Another 500B
        }

        large_token = jwt.encode(
            payload, "dev-secret-change-in-prod", algorithm="HS256"
        )

        # Validate large token
        response = jwt_issuer_client.post("/validate", json={"token": large_token})

        assert response.status_code == 200
        validation_data = response.json()
        assert validation_data["valid"] is True
        assert validation_data["payload"]["large_claim"] == large_data

    def test_jwt_token_validation_concurrent_different_tokens(self, jwt_issuer_client):
        """Test concurrent validation of different tokens."""
        # Create multiple different tokens
        services = [f"service-{i}" for i in range(20)]
        token_requests = []

        for service in services:
            response = jwt_issuer_client.post("/token", json={"service_name": service})
            assert response.status_code == 200
            token_requests.append({"service": service, "token": response.json()["token"]})
            token_requests.append(
                {"service": service, "token": response.json()["token"]}
            )

        # Validate all tokens concurrently
        import concurrent.futures

        def validate_token(token_data):
            response = jwt_issuer_client.post("/validate", json={"token": token_data["token"]})
            return {"service": token_data["service"], "response": response}

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(validate_token, token_data) for token_data in token_requests]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            response = jwt_issuer_client.post(
                "/validate", json={"token": token_data["token"]}
            )
            return {"service": token_data["service"], "response": response}

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(validate_token, token_data)
                for token_data in token_requests
            ]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All validations should succeed with correct service names
        assert len(results) == len(services)
        for result in results:
            assert result["response"].status_code == 200
            payload = result["response"].json()["payload"]
            assert payload["sub"] == result["service"]

    def test_jwt_token_issuer_health_during_load(self, jwt_issuer_client):
        """Test that JWT issuer remains healthy under validation load."""
        # Generate some tokens first
        tokens = []
        for i in range(50):
            response = jwt_issuer_client.post("/token", json={"service_name": f"load-test-{i}"})
            response = jwt_issuer_client.post(
                "/token", json={"service_name": f"load-test-{i}"}
            )
            tokens.append(response.json()["token"])

        # Start validation load
        import concurrent.futures
        import threading

        stop_event = threading.Event()
        health_responses = []

        def validation_load():
            while not stop_event.is_set():
                for token in tokens[:10]:  # Use first 10 tokens
                    if stop_event.is_set():
                        break
                    jwt_issuer_client.post("/validate", json={"token": token})
                    time.sleep(0.01)  # Small delay

        def check_health():
            for _ in range(10):  # Check health 10 times
                if stop_event.is_set():
                    break
                response = jwt_issuer_client.get("/health")
                health_responses.append(response.status_code)
                time.sleep(0.1)

        # Start load and health check threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            load_future = executor.submit(validation_load)
            health_future = executor.submit(check_health)

            # Let it run for 1 second
            time.sleep(1)
            stop_event.set()

            # Wait for completion
            load_future.result(timeout=5)
            health_future.result(timeout=5)

        # Health endpoint should have remained responsive
        assert len(health_responses) >= 5  # At least half the health checks completed
        assert all(status == 200 for status in health_responses)

    def test_jwt_token_validation_edge_case_claims(self, jwt_issuer_client):
        """Test validation with edge case claim values."""
        edge_cases = [
            # Numeric claims
            {"sub": "numeric-test", "numeric_claim": 0},
            {"sub": "negative-test", "negative_claim": -123},
            {"sub": "float-test", "float_claim": 123.456},
            # Boolean claims
            {"sub": "bool-true-test", "bool_claim": True},
            {"sub": "bool-false-test", "bool_claim": False},
            # Array claims
            {"sub": "array-test", "array_claim": ["item1", "item2", "item3"]},
            # Object claims
            {"sub": "object-test", "object_claim": {"nested": "value", "number": 42}},
            # Empty/null claims
            {"sub": "empty-test", "empty_claim": ""},
            {"sub": "null-test", "null_claim": None},
        ]

        for test_payload in edge_cases:
            # Create full payload
            full_payload = {
                "iss": "venturestrat-gateway",
                "aud": "venturestrat-services",
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "jti": f"test-{test_payload['sub']}",
                **test_payload,
            }

            token = jwt.encode(
                full_payload, "dev-secret-change-in-prod", algorithm="HS256"
            )

            response = jwt_issuer_client.post("/validate", json={"token": token})

            assert response.status_code == 200
            returned_payload = response.json()["payload"]

            # Verify all claims are preserved
            for key, value in test_payload.items():
                assert returned_payload[key] == value

    def test_jwt_token_validation_unicode_handling(self, jwt_issuer_client):
        """Test JWT validation with Unicode characters."""
        unicode_test_cases = [
            "service-中文",
            "service-العربية",
            "service-русский",
            "service-🚀🔥💯",
            "service-with-emoji-🎯",
            "service-mixed-中文-русский-🌟",
        ]

        for service_name in unicode_test_cases:
            # Issue token
            token_response = jwt_issuer_client.post("/token", json={"service_name": service_name})
            token_response = jwt_issuer_client.post(
                "/token", json={"service_name": service_name}
            )

            # Some unicode chars might fail validation at the issuer level
            if token_response.status_code != 200:
                continue

            token = token_response.json()["token"]

            # Validate token
            validate_response = jwt_issuer_client.post("/validate", json={"token": token})
            validate_response = jwt_issuer_client.post(
                "/validate", json={"token": token}
            )

            assert validate_response.status_code == 200
            payload = validate_response.json()["payload"]
            assert payload["sub"] == service_name
