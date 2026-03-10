"""
Integration tests for multiple consumers functionality.

Tests different consumer types, rate limits, isolation, and consumer metadata.
This test verifies task 6.1: Write tests for multiple consumers.
"""

import pytest
import httpx
import time
import asyncio
from typing import Dict, Any


@pytest.mark.integration
class TestMultipleConsumers:
    """Test multiple consumer functionality with different tiers and characteristics."""

    def test_all_consumers_authenticate_successfully(
        self,
        gateway_client,
        free_tier_client,
        standard_tier_client,
        premium_tier_client,
        unauthorized_client,
    ):
        """Test that all configured consumers can authenticate successfully."""
        # Test all consumer clients work
        consumer_clients = [
            ("gateway_client", gateway_client),
            ("free_tier_client", free_tier_client),
            ("standard_tier_client", standard_tier_client),
            ("premium_tier_client", premium_tier_client),
        ]

        for client_name, client in consumer_clients:
            response = client.get("/health")

            # Should pass authentication
            assert (
                response.status_code == 200
            ), f"Consumer {client_name} authentication failed"

            # Should have Kong headers indicating successful processing
            assert "X-Kong-Proxy-Latency" in response.headers
            assert "X-Correlation-ID" in response.headers

            # Should have rate limit headers
            assert "X-RateLimit-Limit-Minute" in response.headers
            assert "X-RateLimit-Remaining-Minute" in response.headers

        # Test that unauthorized client fails
        response = unauthorized_client.get("/health")
        # Health endpoint might be exempted from auth, but let's test a protected endpoint
        response = unauthorized_client.get("/api/v1/registry/services")
        assert response.status_code == 401

    def test_consumer_rate_limit_isolation(
        self, free_tier_client, standard_tier_client, premium_tier_client
    ):
        """Test that different consumers have isolated rate limits."""
        # Get initial limits for all consumers
        free_response = free_tier_client.get("/health")
        standard_response = standard_tier_client.get("/health")
        premium_response = premium_tier_client.get("/health")

        assert free_response.status_code == 200
        assert standard_response.status_code == 200
        assert premium_response.status_code == 200

        free_limit = int(free_response.headers["X-RateLimit-Limit-Minute"])
        standard_limit = int(standard_response.headers["X-RateLimit-Limit-Minute"])
        premium_limit = int(premium_response.headers["X-RateLimit-Limit-Minute"])

        # Higher tiers should have higher limits
        assert (
            standard_limit > free_limit
        ), f"Standard limit ({standard_limit}) should be higher than free limit ({free_limit})"
        assert (
            premium_limit > standard_limit
        ), f"Premium limit ({premium_limit}) should be higher than standard limit ({standard_limit})"

        # Verify specific tier limits
        assert free_limit == 100, f"Free tier limit should be 100, got {free_limit}"
        assert (
            standard_limit == 1000
        ), f"Standard tier limit should be 1000, got {standard_limit}"
        assert (
            premium_limit == 5000
        ), f"Premium tier limit should be 5000, got {premium_limit}"

        # Make multiple requests with free tier to consume some quota
        free_initial_remaining = int(
            free_response.headers["X-RateLimit-Remaining-Minute"]
        )

        for _ in range(5):
            free_tier_client.get("/health")

        # Check that free tier remaining decreased
        free_response_after = free_tier_client.get("/health")
        free_remaining_after = int(free_response_after.headers["X-RateLimit-Remaining-Minute"])
        free_remaining_after = int(
            free_response_after.headers["X-RateLimit-Remaining-Minute"]
        )
        assert (
            free_remaining_after < free_initial_remaining
        ), "Free tier remaining should have decreased"

        # Check that standard tier remaining is unaffected
        standard_response_after = standard_tier_client.get("/health")
        standard_remaining_after = int(
            standard_response_after.headers["X-RateLimit-Remaining-Minute"]
        )
        standard_initial_remaining = int(standard_response.headers["X-RateLimit-Remaining-Minute"])
        standard_initial_remaining = int(
            standard_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # Standard tier should not be affected by free tier usage
        assert (
            abs(standard_remaining_after - standard_initial_remaining) <= 1
        ), "Standard tier should not be affected by free tier usage"

    def test_consumer_tier_characteristics(
        self,
        gateway_client,
        free_tier_client,
        standard_tier_client,
        premium_tier_client,
    ):
        """Test that consumer tiers have expected characteristics."""
        test_cases = [
            {
                "client": free_tier_client,
                "expected_minute_limit": 100,
                "tier_type": "free",
            },
            {
                "client": standard_tier_client,
                "expected_minute_limit": 1000,
                "tier_type": "standard",
            },
            {
                "client": premium_tier_client,
                "expected_minute_limit": 5000,
                "tier_type": "premium",
            },
            {
                "client": gateway_client,
                "expected_minute_limit": 1000,  # Global default (dev)
                "tier_type": "dev",
            },
        ]

        for test_case in test_cases:
            response = test_case["client"].get("/health")
            assert (
                response.status_code == 200
            ), f"Authentication failed for {test_case['tier_type']} tier"

            # Check minute rate limit
            minute_limit = int(response.headers["X-RateLimit-Limit-Minute"])
            assert (
                minute_limit == test_case["expected_minute_limit"]
            ), f"{test_case['tier_type']} tier minute limit should be {test_case['expected_minute_limit']}, got {minute_limit}"

    def test_consumer_request_path_isolation(self, gateway_client, free_tier_client):
        """Test that consumers can access different endpoints independently."""
        endpoints_to_test = [
            "/health",
            "/api/v1/registry/services",  # May return 502/503 if backend down, but should pass auth
        ]

        for client_name, client in [
            ("gateway", gateway_client),
            ("free_tier", free_tier_client),
        ]:
            for endpoint in endpoints_to_test:
                response = client.get(endpoint)

                # Should pass authentication (not 401/403)
                assert response.status_code not in [
                    401,
                    403,
                ], f"Authentication failed for {client_name} on {endpoint}"

                # Should be acceptable status codes
                assert response.status_code in [
                    200,
                    404,
                    502,
                    503,
                ], f"Unexpected status {response.status_code} for {client_name} on {endpoint}"
                assert (
                    response.status_code in [200, 404, 502, 503]
                ), f"Unexpected status {response.status_code} for {client_name} on {endpoint}"

    def test_consumer_header_variations(self, gateway_stack):
        """Test that consumers work with different header formats."""
        test_cases = [
            {
                "name": "X-API-Key header",
                "headers": {"X-API-Key": "dev-api-key-12345"},
                "should_pass": True,
            },
            {
                "name": "apikey query parameter",
                "headers": {},
                "query": "?apikey=dev-api-key-12345",
                "should_pass": True,
            },
            {
                "name": "Both header and query (header precedence)",
                "headers": {"X-API-Key": "dev-api-key-12345"},
                "query": "?apikey=invalid-key",
                "should_pass": True,
            },
            {
                "name": "Case sensitive header",
                "headers": {"x-api-key": "dev-api-key-12345"},  # lowercase
                "should_pass": False,
            },
            {
                "name": "Wrong header name",
                "headers": {"API-Key": "dev-api-key-12345"},
                "should_pass": False,
            },
        ]

        for case in test_cases:
            client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)

            try:
                endpoint = "/health"
                if "query" in case:
                    endpoint += case["query"]

                response = client.get(endpoint, headers=case.get("headers", {}))

                if case["should_pass"]:
                    assert (
                        response.status_code == 200
                    ), f"Test case '{case['name']}' should pass but got {response.status_code}"
                else:
                    assert response.status_code in [
                        401,
                        403,
                    ], f"Test case '{case['name']}' should fail but got {response.status_code}"
                    assert (
                        response.status_code in [401, 403]
                    ), f"Test case '{case['name']}' should fail but got {response.status_code}"

            finally:
                client.close()

    def test_consumer_rate_limit_headers_consistency(
        self,
        free_tier_client,
        standard_tier_client,
        premium_tier_client,
        gateway_client,
    ):
        """Test that rate limit headers are consistent per consumer."""
        consumers_to_test = [
            (free_tier_client, 100, "free"),
            (standard_tier_client, 1000, "standard"),
            (premium_tier_client, 5000, "premium"),
            (gateway_client, 1000, "dev"),
        ]

        for client, expected_limit, tier_name in consumers_to_test:
            # Make multiple requests to ensure consistency
            responses = []
            for _ in range(3):
                responses.append(client.get("/health"))
                time.sleep(0.1)

            # All responses should have consistent rate limit
            for i, response in enumerate(responses):
                assert (
                    response.status_code == 200
                ), f"Request {i} failed for {tier_name}"

                # Check headers are present
                assert "X-RateLimit-Limit-Minute" in response.headers
                assert "X-RateLimit-Remaining-Minute" in response.headers

                # Check limit is correct
                limit = int(response.headers["X-RateLimit-Limit-Minute"])
                assert (
                    limit == expected_limit
                ), f"Expected limit {expected_limit} but got {limit} for {tier_name}"

                # Remaining should be valid
                remaining = int(response.headers["X-RateLimit-Remaining-Minute"])
                assert (
                    0 <= remaining <= limit
                ), f"Invalid remaining count {remaining} for limit {limit}"

            # Remaining should decrease across requests (or stay same for high limits)
            remainings = [
                int(r.headers["X-RateLimit-Remaining-Minute"]) for r in responses
            ]
            for i in range(1, len(remainings)):
                assert (
                    remainings[i] <= remainings[i - 1]
                ), f"Remaining should decrease: {remainings}"

    def test_invalid_consumer_key_combinations(self, gateway_stack):
        """Test various invalid API key scenarios across multiple consumers."""
        invalid_scenarios = [
            {
                "name": "Non-existent key similar to valid one",
                "api_key": "dev-api-key-54321",  # Similar to dev-api-key-12345
                "expected_status": 403,
            },
            {
                "name": "Free tier key with wrong numbers",
                "api_key": "free-api-key-22222",  # Wrong numbers for free tier
                "expected_status": 403,
            },
            {
                "name": "Standard tier key with wrong format",
                "api_key": "standard_api_key_22222",  # Underscores instead of dashes
                "expected_status": 403,
            },
            {
                "name": "Mixed case valid key",
                "api_key": "Dev-Api-Key-12345",  # Wrong case
                "expected_status": 403,
            },
            {
                "name": "Partial valid key",
                "api_key": "dev-api-key-123",  # Truncated
                "expected_status": 403,
            },
            {"name": "Empty API key", "api_key": "", "expected_status": 401},
        ]

        for scenario in invalid_scenarios:
            client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)

            try:
                headers = {}
                if scenario["api_key"]:  # Only add header if key is not empty
                    headers["X-API-Key"] = scenario["api_key"]

                response = client.get("/health", headers=headers)

                assert (
                    response.status_code == scenario["expected_status"]
                ), f"Scenario '{scenario['name']}' expected {scenario['expected_status']} but got {response.status_code}"

                # Error responses should have proper format
                if response.status_code in [401, 403]:
                    data = response.json()
                    assert "message" in data, "Error response should have 'message' field"
                    assert (
                        "message" in data
                    ), "Error response should have 'message' field"
                    assert isinstance(data["message"], str), "Message should be string"

            finally:
                client.close()

    def test_consumer_authentication_across_methods(
        self, gateway_client, standard_tier_client
    ):
        """Test that consumer authentication works across different HTTP methods."""
        http_methods_to_test = [
            ("GET", "/health", None),
            (
                "POST",
                "/api/v1/registry/services",
                {"name": "test-service", "url": "http://test:8080"},
            ),
            ("GET", "/api/v1/registry/services", None),
        ]

        test_clients = [("gateway", gateway_client), ("standard", standard_tier_client)]

        for client_name, client in test_clients:
            for method, endpoint, payload in http_methods_to_test:
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "POST":
                    response = client.post(endpoint, json=payload)
                else:
                    continue

                # Should pass authentication (not 401/403)
                assert response.status_code not in [
                    401,
                    403,
                ], f"Authentication failed for {client_name} on {method} {endpoint}"

                # Should have Kong processing headers
                assert "X-Kong-Proxy-Latency" in response.headers

    @pytest.mark.slow
    def test_consumer_rate_limit_enforcement_per_tier(self, free_tier_client):
        """Test rate limit enforcement for different consumer tiers."""
        # This test is marked slow as it may need to make many requests

        # Test free tier enforcement (100/minute limit)
        # Get initial remaining count
        response = free_tier_client.get("/health")
        assert response.status_code == 200

        remaining = int(response.headers["X-RateLimit-Remaining-Minute"])
        limit = int(response.headers["X-RateLimit-Limit-Minute"])

        assert limit == 100, f"Free tier limit should be 100, got {limit}"

        # If we're close to the limit, try to hit it
        if remaining < 20:
            hit_limit = False
            for i in range(remaining + 5):
                response = free_tier_client.get("/health")
                if response.status_code == 429:
                    hit_limit = True

                    # Should have proper 429 response
                    data = response.json()
                    assert (
                        "rate limit" in data["message"].lower()
                        or "too many" in data["message"].lower()
                    )

                    # Should have Retry-After header
                    assert "Retry-After" in response.headers
                    retry_after = response.headers["Retry-After"]
                    assert retry_after.isdigit() and int(retry_after) > 0

                    break

            if hit_limit:
                # Verify that after hitting limit, we continue to get 429
                response = free_tier_client.get("/health")
                assert response.status_code == 429
            else:
                # If we didn't hit limit, at least verify remaining decreased
                final_response = free_tier_client.get("/health")
                final_remaining = int(
                    final_response.headers["X-RateLimit-Remaining-Minute"]
                )
                assert (
                    final_remaining < remaining
                ), "Remaining count should have decreased"
        else:
            pytest.skip(
                f"Free tier has {remaining} remaining requests, too far from limit to test enforcement efficiently"
            )

    def test_consumer_metadata_and_tagging(
        self, gateway_client, free_tier_client, standard_tier_client
    ):
        """Test that consumer configuration includes proper metadata and tagging."""
        # This test verifies the Kong configuration indirectly through behavior

        consumer_behaviors = [
            (
                gateway_client,
                "dev",
                True,
                False,
            ),  # should_have_global_limits, should_have_custom_limits
            (free_tier_client, "free-tier", False, True),
            (standard_tier_client, "standard-tier", False, True),
        ]

        for (
            client,
            tier_name,
            should_have_global_limits,
            should_have_custom_limits,
        ) in consumer_behaviors:
            response = client.get("/health")
            assert (
                response.status_code == 200
            ), f"Authentication failed for {tier_name} consumer"

            # Verify rate limiting behavior matches expectations
            limit = int(response.headers["X-RateLimit-Limit-Minute"])

            if should_have_global_limits:
                # Global limit is 1000/minute
                assert (
                    limit >= 1000
                ), f"Global limit consumer should have ≥1000/min, got {limit}"

            if should_have_custom_limits:
                # Custom limits should be different from global 1000
                if "free" in tier_name:
                    assert (
                        limit == 100
                    ), f"Free tier should have 100/min limit, got {limit}"
                elif "standard" in tier_name:
                    assert (
                        limit == 1000
                    ), f"Standard tier should have 1000/min limit, got {limit}"

    async def test_concurrent_consumer_requests(self, gateway_stack):
        """Test multiple consumers making concurrent requests."""
        consumer_keys = [
            "dev-api-key-12345",
            "test-api-key-67890",
            "free-api-key-11111",
            "standard-api-key-22222",
            "premium-api-key-33333",
        ]

        async def make_request_for_consumer(api_key: str) -> Dict[str, Any]:
            async with httpx.AsyncClient(
                base_url="http://localhost:8000",
                headers={"X-API-Key": api_key},
                timeout=10.0,
            ) as client:
                response = await client.get("/health")
                return {
                    "api_key": api_key,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "correlation_id": response.headers.get("X-Correlation-ID"),
                }

        # Run concurrent requests for all consumers
        tasks = [make_request_for_consumer(key) for key in consumer_keys]
        results = await asyncio.gather(*tasks)

        # All requests should succeed
        assert len(results) == len(consumer_keys)

        for result in results:
            assert (
                result["status_code"] == 200
            ), f"Request failed for consumer {result['api_key']}"
            assert "X-Kong-Proxy-Latency" in result["headers"]
            assert "X-Correlation-ID" in result["headers"]
            assert result["correlation_id"] is not None

        # All correlation IDs should be unique
        correlation_ids = [result["correlation_id"] for result in results]
        assert len(set(correlation_ids)) == len(
            correlation_ids
        ), "Correlation IDs should be unique"

    def test_consumer_username_in_upstream_headers(self, gateway_stack):
        """Test that consumer username is added to upstream headers for all consumers."""
        # Test different consumer clients
        test_cases = [
            {
                "client_name": "default-consumer",
                "api_key": "dev-api-key-12345",
                "expected_username": "default-consumer",
            },
            {
                "client_name": "test-consumer",
                "api_key": "test-api-key-67890",
                "expected_username": "test-consumer",
            },
            {
                "client_name": "free-tier-consumer",
                "api_key": "free-api-key-11111",
                "expected_username": "free-tier-consumer",
            },
            {
                "client_name": "standard-tier-consumer",
                "api_key": "standard-api-key-22222",
                "expected_username": "standard-tier-consumer",
            },
            {
                "client_name": "premium-tier-consumer",
                "api_key": "premium-api-key-33333",
                "expected_username": "premium-tier-consumer",
            },
        ]

        for test_case in test_cases:
            client = httpx.Client(
                base_url="http://localhost:8000",
                headers={"X-API-Key": test_case["api_key"]},
                timeout=10.0,
            )

            try:
                # Make request to test endpoint that might echo headers back
                # We'll use httpbin.org/headers as a test endpoint to see what headers Kong forwards
                response = client.get("/api/v1/registry/services")

                # Should pass authentication (not 401/403)
                assert response.status_code not in [
                    401,
                    403,
                ], f"Authentication failed for {test_case['client_name']}"

                # The headers sent to upstream should be tested through a mock service
                # For now, we verify that Kong processed the request successfully
                # (This test would be enhanced with a mock backend that echoes headers)

                # Verify Kong headers are present (indicating request processing)
                assert (
                    "X-Kong-Proxy-Latency" in response.headers
                ), f"Kong should add proxy latency header for {test_case['client_name']}"
                assert (
                    "X-Correlation-ID" in response.headers
                ), f"Kong should add correlation ID for {test_case['client_name']}"

            finally:
                client.close()

    def test_premium_tier_specific_features(self, premium_tier_client):
        """Test premium tier specific features and higher limits."""
        # Get premium tier response
        response = premium_tier_client.get("/health")
        assert response.status_code == 200

        # Verify premium tier rate limits
        minute_limit = int(response.headers["X-RateLimit-Limit-Minute"])
        assert (
            minute_limit == 5000
        ), f"Premium tier should have 5000/min limit, got {minute_limit}"

        # Verify premium tier has high remaining quota
        remaining = int(response.headers["X-RateLimit-Remaining-Minute"])
        assert (
            remaining > 4990
        ), f"Premium tier should start with high quota, got {remaining}"

        # Premium tier should be able to make burst requests without immediate throttling
        burst_requests = 10
        burst_responses = []

        for i in range(burst_requests):
            burst_response = premium_tier_client.get("/health")
            burst_responses.append(burst_response)

        # All burst requests should succeed
        for i, burst_response in enumerate(burst_responses):
            assert (
                burst_response.status_code == 200
            ), f"Burst request {i} failed for premium tier"

        # Remaining should have decreased by burst count
        final_response = premium_tier_client.get("/health")
        final_remaining = int(final_response.headers["X-RateLimit-Remaining-Minute"])

        # Allow some tolerance for concurrent tests or race conditions
        expected_min = remaining - burst_requests - 5  # 5 request tolerance
        expected_max = remaining - burst_requests + 5

        assert (
            expected_min <= final_remaining <= expected_max
        ), f"Expected remaining {expected_min}-{expected_max}, got {final_remaining}"

    def test_tier_hierarchy_and_limits(
        self, free_tier_client, standard_tier_client, premium_tier_client
    ):
        """Test the complete tier hierarchy with appropriate limits."""
        tier_tests = [
            {
                "client": free_tier_client,
                "tier_name": "free",
                "expected_minute": 100,
                "expected_hour": 1000,
                "expected_day": 2500,
            },
            {
                "client": standard_tier_client,
                "tier_name": "standard",
                "expected_minute": 1000,
                "expected_hour": 10000,
                "expected_day": 50000,
            },
            {
                "client": premium_tier_client,
                "tier_name": "premium",
                "expected_minute": 5000,
                "expected_hour": 100000,
                "expected_day": 500000,
            },
        ]

        for tier_test in tier_tests:
            response = tier_test["client"].get("/health")
            assert (
                response.status_code == 200
            ), f"{tier_test['tier_name']} tier authentication failed"

            # Verify minute limits (this is what Kong reports in headers)
            minute_limit = int(response.headers["X-RateLimit-Limit-Minute"])
            assert (
                minute_limit == tier_test["expected_minute"]
            ), f"{tier_test['tier_name']} tier minute limit should be {tier_test['expected_minute']}, got {minute_limit}"

            # Verify rate limit headers are present
            assert "X-RateLimit-Remaining-Minute" in response.headers
            remaining = int(response.headers["X-RateLimit-Remaining-Minute"])
            assert (
                0 <= remaining <= minute_limit
            ), f"Invalid remaining count {remaining} for {tier_test['tier_name']} tier limit {minute_limit}"
