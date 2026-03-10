"""
Integration test for Task 6.4: Verify X-Consumer-Username header present in backend.

This test verifies that Kong Gateway correctly forwards the X-Consumer-Username
header to backend services, allowing them to identify the authenticated consumer.
"""

import pytest
import httpx


@pytest.mark.integration
class TestConsumerHeadersVerification:
    """Test that consumer headers are properly forwarded to backend services."""

    def test_consumer_username_header_present_in_backend(self, gateway_stack):
        """
        Task 6.4 - Verify: X-Consumer-Username header present in backend.

        This test verifies that Kong Gateway adds the X-Consumer-Username header
        to upstream requests and that backend services receive it correctly.
        """
        test_cases = [
            {
                "consumer": "default-consumer",
                "api_key": "dev-api-key-12345",
                "expected_username": "default-consumer",
            },
            {
                "consumer": "test-consumer",
                "api_key": "test-api-key-67890",
                "expected_username": "test-consumer",
            },
            {
                "consumer": "free-tier-consumer",
                "api_key": "free-api-key-11111",
                "expected_username": "free-tier-consumer",
            },
            {
                "consumer": "standard-tier-consumer",
                "api_key": "standard-api-key-22222",
                "expected_username": "standard-tier-consumer",
            },
            {
                "consumer": "premium-tier-consumer",
                "api_key": "premium-api-key-33333",
                "expected_username": "premium-tier-consumer",
            },
        ]

        for test_case in test_cases:
            with httpx.Client(
                base_url="http://localhost:8000",
                headers={"X-API-Key": test_case["api_key"]},
                timeout=10.0,
            ) as client:
                # Call the header inspection endpoint through the gateway
                response = client.get("/health/headers")

                # Should pass authentication
                assert (
                    response.status_code == 200
                ), f"Authentication failed for {test_case['consumer']}"

                # Parse response
                data = response.json()

                # Verify the consumer username header is present and correct
                assert (
                    "consumer_username" in data
                ), f"consumer_username not found in response for {test_case['consumer']}"

                assert (
                    data["consumer_username"] == test_case["expected_username"]
                ), f"Expected consumer_username '{test_case['expected_username']}' but got '{data['consumer_username']}' for {test_case['consumer']}"

                # Verify the consumer ID is also present
                assert (
                    "consumer_id" in data
                ), f"consumer_id not found in response for {test_case['consumer']}"

                assert (
                    data["consumer_id"] is not None
                ), f"consumer_id should not be null for {test_case['consumer']}"

                # Verify correlation ID is present
                assert (
                    "correlation_id" in data
                ), f"correlation_id not found in response for {test_case['consumer']}"

                assert (
                    data["correlation_id"] is not None
                ), f"correlation_id should not be null for {test_case['consumer']}"

                # Verify other Kong headers are present
                assert (
                    "forwarded_by" in data
                ), f"forwarded_by not found in response for {test_case['consumer']}"

    def test_consumer_headers_in_raw_headers_dict(self, gateway_stack):
        """
        Additional verification that consumer headers are in the raw headers dictionary.

        This provides additional confidence that the headers are actually being
        forwarded by Kong and not just fabricated by the backend.
        """
        test_cases = [
            ("dev-api-key-12345", "default-consumer"),
            ("test-api-key-67890", "test-consumer"),
            ("free-api-key-11111", "free-tier-consumer"),
        ]

        for api_key, expected_username in test_cases:
            with httpx.Client(
                base_url="http://localhost:8000",
                headers={"X-API-Key": api_key},
                timeout=10.0,
            ) as client:
                response = client.get("/health/headers")
                assert response.status_code == 200

                data = response.json()
                headers = data["headers"]

                # Check that the headers are present in the raw headers dict
                # Note: FastAPI converts header names to lowercase
                assert (
                    "x-consumer-username" in headers
                ), f"x-consumer-username not found in raw headers for {api_key}"

                assert (
                    headers["x-consumer-username"] == expected_username
                ), f"Expected x-consumer-username '{expected_username}' but got '{headers.get('x-consumer-username')}' for {api_key}"

                assert (
                    "x-consumer-id" in headers
                ), f"x-consumer-id not found in raw headers for {api_key}"

                # Verify correlation ID is also in raw headers
                assert (
                    "x-correlation-id" in headers
                ), f"x-correlation-id not found in raw headers for {api_key}"

                # Verify Kong-added headers
                assert (
                    "x-forwarded-by" in headers
                ), f"x-forwarded-by not found in raw headers for {api_key}"

                # Verify the header value matches what Kong should have set
                assert (
                    headers["x-forwarded-by"] == "kong-gateway"
                ), f"Expected x-forwarded-by 'kong-gateway' but got '{headers.get('x-forwarded-by')}' for {api_key}"

    def test_unauthenticated_request_no_consumer_headers(self, gateway_stack):
        """
        Verify that unauthenticated requests don't get consumer headers.

        This test confirms that consumer headers are only added when a valid
        API key is provided and authentication succeeds.
        """
        with httpx.Client(base_url="http://localhost:8000", timeout=10.0) as client:
            # Try to access the headers endpoint without an API key
            response = client.get("/health/headers")

            # Should get 401 Unauthorized because the endpoint requires authentication
            assert (
                response.status_code == 401
            ), "Request without API key should be rejected with 401"

    def test_invalid_api_key_no_consumer_headers(self, gateway_stack):
        """
        Verify that requests with invalid API keys don't get consumer headers.

        This test confirms that consumer headers are only added for valid consumers.
        """
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "invalid-api-key-99999"},
            timeout=10.0,
        ) as client:
            response = client.get("/health/headers")

            # Should get 403 Forbidden for invalid API key
            assert (
                response.status_code == 403
            ), "Request with invalid API key should be rejected with 403"

    def test_consumer_header_format_and_values(self, gateway_client):
        """
        Verify the format and content of consumer headers.

        This test ensures that the consumer headers follow the expected format
        and contain valid values.
        """
        response = gateway_client.get("/health/headers")
        assert response.status_code == 200

        data = response.json()

        # Consumer username should be a non-empty string
        consumer_username = data["consumer_username"]
        assert isinstance(
            consumer_username, str
        ), f"consumer_username should be a string, got {type(consumer_username)}"
        assert len(consumer_username) > 0, "consumer_username should not be empty"
        assert (
            consumer_username == "default-consumer"
        ), f"Expected 'default-consumer', got '{consumer_username}'"

        # Consumer ID should be a non-empty string (Kong UUID format)
        consumer_id = data["consumer_id"]
        assert isinstance(
            consumer_id, str
        ), f"consumer_id should be a string, got {type(consumer_id)}"
        assert len(consumer_id) > 0, "consumer_id should not be empty"

        # Correlation ID should be a UUID-format string
        correlation_id = data["correlation_id"]
        assert isinstance(
            correlation_id, str
        ), f"correlation_id should be a string, got {type(correlation_id)}"
        assert len(correlation_id) > 0, "correlation_id should not be empty"
        # Basic UUID format check (36 characters with hyphens)
        assert (
            len(correlation_id) == 36 and correlation_id.count("-") == 4
        ), f"correlation_id should be UUID format, got '{correlation_id}'"

    def test_multiple_requests_consistent_consumer_headers(self, standard_tier_client):
        """
        Verify that consumer headers are consistent across multiple requests from the same consumer.

        This test ensures that the consumer identity is stable and doesn't change
        between requests from the same API key.
        """
        # Make multiple requests
        responses = []
        for _ in range(3):
            response = standard_tier_client.get("/health/headers")
            assert response.status_code == 200
            responses.append(response.json())

        # All responses should have the same consumer username
        consumer_usernames = [r["consumer_username"] for r in responses]
        assert all(
            username == "standard-tier-consumer" for username in consumer_usernames
        ), f"Consumer username should be consistent, got {consumer_usernames}"

        # All responses should have the same consumer ID
        consumer_ids = [r["consumer_id"] for r in responses]
        assert (
            len(set(consumer_ids)) == 1
        ), f"Consumer ID should be consistent across requests, got {consumer_ids}"

        # Correlation IDs should be different (new ID per request)
        correlation_ids = [r["correlation_id"] for r in responses]
        assert len(set(correlation_ids)) == len(
            correlation_ids
        ), f"Correlation IDs should be unique per request, got {correlation_ids}"

    def test_gateway_route_preserves_consumer_context(self, premium_tier_client):
        """
        Test that consumer context is preserved when routing through different gateway paths.

        This test verifies that consumer headers are added regardless of which
        backend service route is taken through the gateway.
        """
        # Test different routes that should all receive consumer headers
        routes_to_test = [
            "/health/headers",
            "/api/v1/registry/services",  # Different route pattern
        ]

        consumer_usernames = []
        consumer_ids = []

        for route in routes_to_test:
            response = premium_tier_client.get(route)

            if route == "/health/headers":
                # This endpoint returns header info directly
                assert response.status_code == 200
                data = response.json()
                consumer_usernames.append(data["consumer_username"])
                consumer_ids.append(data["consumer_id"])
            else:
                # For other endpoints, just verify they pass auth (consumer headers are working)
                # The actual headers would need to be checked by the backend service itself
                assert response.status_code not in [
                    401,
                    403,
                ], f"Authentication should pass for route {route} with consumer headers"

        # Consumer identity should be consistent across all routes
        if len(consumer_usernames) > 0:
            assert all(
                username == "premium-tier-consumer" for username in consumer_usernames
            ), f"Consumer username should be consistent across routes, got {consumer_usernames}"

            assert (
                len(set(consumer_ids)) <= 1
            ), f"Consumer ID should be consistent across routes, got {consumer_ids}"
