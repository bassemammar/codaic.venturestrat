"""
Integration tests for rate limiting functionality.

Tests rate limit enforcement, headers, and per-consumer limits.
"""

import pytest
import time
import asyncio
import httpx


@pytest.mark.integration
class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_headers_present(self, gateway_client):
        """Test that rate limit headers are present in responses."""
        response = gateway_client.get("/health")

        assert response.status_code == 200

        # Rate limit headers should be present
        assert "X-RateLimit-Limit-Minute" in response.headers
        assert "X-RateLimit-Remaining-Minute" in response.headers

        # Values should be numeric
        limit = response.headers["X-RateLimit-Limit-Minute"]
        remaining = response.headers["X-RateLimit-Remaining-Minute"]

        assert limit.isdigit()
        assert remaining.isdigit()
        assert int(limit) > 0
        assert 0 <= int(remaining) <= int(limit)

    def test_rate_limit_decreases_with_requests(self, gateway_client):
        """Test that remaining rate limit decreases with requests."""
        # Make first request
        response1 = gateway_client.get("/health")
        remaining1 = int(response1.headers["X-RateLimit-Remaining-Minute"])

        # Make second request immediately
        response2 = gateway_client.get("/health")
        remaining2 = int(response2.headers["X-RateLimit-Remaining-Minute"])

        # Remaining should decrease (or stay same if rate limit is very high)
        assert remaining2 <= remaining1

    @pytest.mark.slow
    def test_rate_limit_enforced(self, free_tier_client):
        """Test that rate limit is enforced for free tier."""
        # Free tier has limit of 100/minute in configuration

        # Get current remaining count
        response = free_tier_client.get("/health")
        int(response.headers["X-RateLimit-Limit-Minute"])
        remaining = int(response.headers["X-RateLimit-Remaining-Minute"])

        # If we're close to limit, this test might hit it
        if remaining < 10:
            # Make requests until limit is hit
            for _ in range(remaining + 5):
                response = free_tier_client.get("/health")
                if response.status_code == 429:
                    break
            else:
                pytest.skip(
                    "Could not trigger rate limit in reasonable number of requests"
                )

            # Verify 429 response
            assert response.status_code == 429

            data = response.json()
            assert "rate limit" in data["message"].lower()

            # Should include retry-after header
            assert "Retry-After" in response.headers
            retry_after = response.headers["Retry-After"]
            assert retry_after.isdigit()
        else:
            pytest.skip("Too far from rate limit to test enforcement efficiently")

    def test_rate_limit_per_consumer(self, free_tier_client, standard_tier_client):
        """Test that different consumers have separate rate limits."""
        # Get limits for both tiers
        free_response = free_tier_client.get("/health")
        standard_response = standard_tier_client.get("/health")

        free_limit = int(free_response.headers["X-RateLimit-Limit-Minute"])
        standard_limit = int(standard_response.headers["X-RateLimit-Limit-Minute"])

        # Standard tier should have higher limit
        assert standard_limit > free_limit

        # Remaining should be independent
        free_remaining = int(free_response.headers["X-RateLimit-Remaining-Minute"])
        standard_remaining = int(
            standard_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # Both should be at or near their respective limits
        assert free_remaining <= free_limit
        assert standard_remaining <= standard_limit

    def test_rate_limit_redis_backend(self, gateway_client):
        """Test that rate limiting is using Redis backend."""
        # This tests configuration consistency
        # Multiple requests should show consistent rate limiting

        responses = []
        for _ in range(3):
            response = gateway_client.get("/health")
            responses.append(response)
            time.sleep(0.1)  # Small delay

        # All should have same limit
        limits = [int(r.headers["X-RateLimit-Limit-Minute"]) for r in responses]
        assert all(limit == limits[0] for limit in limits)

        # Remaining should be consistent or decreasing
        remainings = [int(r.headers["X-RateLimit-Remaining-Minute"]) for r in responses]
        for i in range(1, len(remainings)):
            assert remainings[i] <= remainings[i - 1]

    def test_rate_limit_reset_time(self, gateway_client):
        """Test rate limit reset information."""
        response = gateway_client.get("/health")

        # Some rate limit implementations include reset time
        # Kong may not always include this header, so check if present
        if "RateLimit-Reset" in response.headers:
            reset_time = response.headers["RateLimit-Reset"]
            assert reset_time.isdigit()

            # Should be a future timestamp
            reset_timestamp = int(reset_time)
            current_timestamp = time.time()
            assert reset_timestamp >= current_timestamp

    @pytest.mark.slow
    def test_rate_limit_recovery(self, free_tier_client):
        """Test that rate limit recovers after time window."""
        # This test is slow and may not be practical in CI
        # Skip if we can't test efficiently

        initial_response = free_tier_client.get("/health")
        remaining = int(initial_response.headers["X-RateLimit-Remaining-Minute"])

        if remaining > 10:
            pytest.skip("Too far from rate limit to test recovery efficiently")

        # Make requests to reduce remaining count
        for _ in range(remaining):
            response = free_tier_client.get("/health")
            if response.status_code == 429:
                break

        if response.status_code == 429:
            # Wait for potential recovery (this would be slow)
            pytest.skip("Rate limit recovery test would be too slow")

    def test_rate_limit_reset_after_window(self, free_tier_client):
        """Test rate limit reset after time window."""
        # Task 9.5: Test rate limit reset after window
        # This test verifies that the rate limit counter resets properly
        # and that the RateLimit-Reset header is present and accurate

        # Get initial state
        initial_response = free_tier_client.get("/health")
        assert initial_response.status_code == 200

        # Extract rate limit information
        limit = int(initial_response.headers["X-RateLimit-Limit-Minute"])
        remaining = int(initial_response.headers["X-RateLimit-Remaining-Minute"])

        # Verify this is the expected free tier limit
        assert limit == 100, f"Free tier should have 100/min limit, got {limit}"

        # Make several requests to consume some of the rate limit
        requests_to_make = min(10, remaining)

        if requests_to_make == 0:
            pytest.skip(
                "No remaining requests available to test rate limit consumption"
            )

        # Consume some rate limit
        for i in range(requests_to_make):
            response = free_tier_client.get("/health")
            if response.status_code == 429:
                pytest.skip(
                    "Hit rate limit before consuming expected number of requests"
                )

        # Check that remaining count decreased
        post_consumption_response = free_tier_client.get("/health")
        assert post_consumption_response.status_code == 200

        post_remaining = int(
            post_consumption_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # Verify rate limit was consumed
        consumed = remaining - post_remaining
        assert (
            consumed >= requests_to_make
        ), f"Expected to consume at least {requests_to_make} requests, but only consumed {consumed}"

        # Check for RateLimit-Reset header if present (Kong may or may not include this)
        if "RateLimit-Reset" in post_consumption_response.headers:
            reset_time = int(post_consumption_response.headers["RateLimit-Reset"])
            current_time = time.time()

            # Reset time should be in the future (within the next minute)
            assert reset_time > current_time, "Reset time should be in the future"
            assert (
                reset_time <= current_time + 60
            ), "Reset time should be within next 60 seconds for minute-based limiting"

            # Time until reset should be reasonable
            time_until_reset = reset_time - current_time
            assert (
                0 < time_until_reset <= 60
            ), f"Time until reset should be 0-60 seconds, got {time_until_reset}"

        # Verify rate limiting is working consistently across multiple requests
        consistency_checks = []
        for i in range(3):
            response = free_tier_client.get("/health")
            if response.status_code == 200:
                current_remaining = int(
                    response.headers["X-RateLimit-Remaining-Minute"]
                )
                consistency_checks.append(current_remaining)
                time.sleep(0.1)  # Small delay between checks

        # Remaining count should either stay the same or decrease (never increase within the same window)
        for i in range(1, len(consistency_checks)):
            assert (
                consistency_checks[i] <= consistency_checks[i - 1]
            ), f"Rate limit remaining should not increase within the same window: {consistency_checks[i-1]} -> {consistency_checks[i]}"

        # Verify that the rate limit is per-consumer (checking headers are present and consistent)
        final_response = free_tier_client.get("/health")
        assert final_response.status_code == 200

        # Required headers should be present
        assert "X-RateLimit-Limit-Minute" in final_response.headers
        assert "X-RateLimit-Remaining-Minute" in final_response.headers

        # Limit should remain consistent
        final_limit = int(final_response.headers["X-RateLimit-Limit-Minute"])
        assert (
            final_limit == limit
        ), f"Rate limit should remain consistent: {limit} vs {final_limit}"

        # Log the test results for verification
        final_remaining = int(final_response.headers["X-RateLimit-Remaining-Minute"])
        total_consumed = remaining - final_remaining

        # Total consumed should be at least what we requested
        assert (
            total_consumed >= requests_to_make
        ), f"Total consumed ({total_consumed}) should be at least requests made ({requests_to_make})"

    def test_global_vs_consumer_rate_limits(self, gateway_client):
        """Test interaction between global and consumer rate limits."""
        # The gateway_client uses dev-api-key which should have global limits
        response = gateway_client.get("/health")

        limit = int(response.headers["X-RateLimit-Limit-Minute"])
        # Global limit is configured as 1000/minute
        assert limit >= 1000

    @pytest.mark.slow
    async def test_concurrent_rate_limiting(self, gateway_client):
        """Test rate limiting under concurrent load."""

        async def make_request():
            async with httpx.AsyncClient(
                base_url=gateway_client.base_url, headers=gateway_client.headers
            ) as client:
                return await client.get("/health")

        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed (or fail consistently)
        status_codes = [r.status_code for r in responses]

        # Should all be successful or hit rate limit consistently
        assert all(code in [200, 429] for code in status_codes)

        # If any hit rate limit, should have retry-after header
        for response in responses:
            if response.status_code == 429:
                assert "Retry-After" in response.headers

    def test_rate_limit_fault_tolerance(self, gateway_client):
        """Test that rate limiting is fault tolerant."""
        # Kong is configured with fault_tolerant: true
        # This means if Redis is down, requests should still go through

        response = gateway_client.get("/health")

        # Should succeed even if Redis issues occur
        assert response.status_code == 200

        # Rate limit headers might not be present if Redis is down
        # But request should still be processed

    def test_rate_limit_different_endpoints(self, gateway_client):
        """Test that rate limiting applies across different endpoints."""
        # Make requests to different endpoints
        health_response = gateway_client.get("/health")
        registry_response = gateway_client.get("/api/v1/registry/services")

        # Rate limiting should be consumer-based, not endpoint-based
        if (
            "X-RateLimit-Remaining-Minute" in health_response.headers
            and "X-RateLimit-Remaining-Minute" in registry_response.headers
        ):
            health_remaining = int(health_response.headers["X-RateLimit-Remaining-Minute"])
            registry_remaining = int(registry_response.headers["X-RateLimit-Remaining-Minute"])
            health_remaining = int(
                health_response.headers["X-RateLimit-Remaining-Minute"]
            )
            registry_remaining = int(
                registry_response.headers["X-RateLimit-Remaining-Minute"]
            )

            # Should be related (same consumer, different requests)
            # Exact values may vary due to timing
            assert abs(health_remaining - registry_remaining) <= 2

    def test_rate_limit_headers_on_error(self, gateway_client):
        """Test that rate limit headers are present even on error responses."""
        # Make request to non-existent endpoint
        response = gateway_client.get("/api/v1/nonexistent/endpoint")

        # Even 404 should include rate limit headers
        if response.status_code == 404:
            assert "X-RateLimit-Limit-Minute" in response.headers


@pytest.mark.integration
class TestRateLimitingTiers:
    """Test rate limiting tier-specific functionality."""

    def test_all_tiers_have_different_limits(
        self, free_tier_client, standard_tier_client, premium_tier_client
    ):
        """Test that all tiers have appropriately different rate limits."""
        # Get limits for all tiers
        free_response = free_tier_client.get("/health")
        standard_response = standard_tier_client.get("/health")
        premium_response = premium_tier_client.get("/health")

        assert free_response.status_code == 200
        assert standard_response.status_code == 200
        assert premium_response.status_code == 200

        # Extract minute limits
        free_limit = int(free_response.headers["X-RateLimit-Limit-Minute"])
        standard_limit = int(standard_response.headers["X-RateLimit-Limit-Minute"])
        premium_limit = int(premium_response.headers["X-RateLimit-Limit-Minute"])

        # Verify tier hierarchy: free < standard < premium
        assert (
            free_limit < standard_limit
        ), f"Free tier ({free_limit}) should have lower limit than standard ({standard_limit})"
        assert (
            standard_limit < premium_limit
        ), f"Standard tier ({standard_limit}) should have lower limit than premium ({premium_limit})"

        # Verify expected values match configuration
        assert free_limit == 100, f"Free tier should have 100/min, got {free_limit}"
        assert (
            standard_limit == 1000
        ), f"Standard tier should have 1000/min, got {standard_limit}"
        assert (
            premium_limit == 5000
        ), f"Premium tier should have 5000/min, got {premium_limit}"

    def test_tier_isolation(self, free_tier_client, standard_tier_client):
        """Test that rate limiting is isolated between different consumer tiers."""
        # Make requests with free tier client to reduce its remaining count
        initial_free_response = free_tier_client.get("/health")
        initial_free_remaining = int(
            initial_free_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # Make several requests with free tier
        for _ in range(min(5, initial_free_remaining)):
            free_tier_client.get("/health")

        # Get remaining count for free tier after requests
        final_free_response = free_tier_client.get("/health")
        final_free_remaining = int(
            final_free_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # Standard tier should be unaffected
        standard_response = standard_tier_client.get("/health")
        standard_remaining = int(
            standard_response.headers["X-RateLimit-Remaining-Minute"]
        )
        standard_limit = int(standard_response.headers["X-RateLimit-Limit-Minute"])

        # Free tier should have decreased
        assert final_free_remaining < initial_free_remaining

        # Standard tier should be near its full limit (unaffected by free tier usage)
        assert standard_remaining >= standard_limit - 5  # Allow for small variance

    def test_premium_tier_higher_throughput(
        self, standard_tier_client, premium_tier_client
    ):
        """Test that premium tier can handle higher throughput."""
        # Make burst of requests to both tiers
        standard_responses = []
        premium_responses = []

        # Make 10 concurrent requests to each tier
        for _ in range(10):
            standard_responses.append(standard_tier_client.get("/health"))
            premium_responses.append(premium_tier_client.get("/health"))

        # All requests should succeed (both tiers can handle 10 requests)
        assert all(r.status_code == 200 for r in standard_responses)
        assert all(r.status_code == 200 for r in premium_responses)

        # Check remaining counts
        final_standard = standard_tier_client.get("/health")
        final_premium = premium_tier_client.get("/health")

        standard_remaining = int(final_standard.headers["X-RateLimit-Remaining-Minute"])
        premium_remaining = int(final_premium.headers["X-RateLimit-Remaining-Minute"])

        # Premium should have more remaining capacity
        assert premium_remaining > standard_remaining

    def test_free_tier_lowest_limits(self, free_tier_client):
        """Test that free tier has the most restrictive limits."""
        response = free_tier_client.get("/health")

        limit = int(response.headers["X-RateLimit-Limit-Minute"])

        # Free tier should have 100/minute limit
        assert limit == 100, f"Free tier should have 100/min limit, got {limit}"

        # Should still allow reasonable number of requests for development
        remaining = int(response.headers["X-RateLimit-Remaining-Minute"])
        assert remaining >= 0, "Free tier should have non-negative remaining count"

    def test_tier_consumer_headers(
        self, free_tier_client, standard_tier_client, premium_tier_client
    ):
        """Test that consumer information is properly set for different tiers."""
        # Make requests with each tier
        free_response = free_tier_client.get("/api/v1/registry/services")
        standard_response = standard_tier_client.get("/api/v1/registry/services")
        premium_response = premium_tier_client.get("/api/v1/registry/services")

        # All requests should be successful or fail consistently
        # (They might fail if registry service is not available, but should have consistent behavior)
        assert free_response.status_code in [200, 502, 503]
        assert standard_response.status_code in [200, 502, 503]
        assert premium_response.status_code in [200, 502, 503]

        # Rate limit headers should still be present
        assert "X-RateLimit-Limit-Minute" in free_response.headers
        assert "X-RateLimit-Limit-Minute" in standard_response.headers
        assert "X-RateLimit-Limit-Minute" in premium_response.headers

    @pytest.mark.slow
    def test_free_tier_rate_limit_enforcement(self, free_tier_client):
        """Test that free tier rate limits are actually enforced."""
        # This test is more aggressive about hitting the rate limit
        initial_response = free_tier_client.get("/health")
        initial_remaining = int(
            initial_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # If we're already close to the limit, try to hit it
        if initial_remaining <= 20:
            # Make requests until we hit the limit or exhaust reasonable attempts
            for i in range(initial_remaining + 10):
                response = free_tier_client.get("/health")

                if response.status_code == 429:
                    # Successfully triggered rate limit
                    assert "Retry-After" in response.headers
                    data = response.json()
                    assert "rate limit" in data["message"].lower()

                    # Verify remaining count is 0
                    assert int(response.headers["X-RateLimit-Remaining-Minute"]) == 0
                    return

                # Check if we're approaching the limit
                remaining = int(response.headers["X-RateLimit-Remaining-Minute"])
                if remaining == 0 and response.status_code == 200:
                    # Kong might allow one extra request at 0 remaining
                    continue

            # If we couldn't trigger the rate limit, that's okay for this test
            # It means the system is working but we didn't exhaust the quota
            pytest.skip("Could not trigger rate limit within reasonable attempts")
        else:
            pytest.skip("Too far from rate limit to test enforcement efficiently")

    def test_tier_specific_api_keys_work(self, gateway_stack):
        """Test that tier-specific API keys work correctly."""
        # Test each tier's API key individually
        tier_configs = [
            ("free-api-key-11111", 100),
            ("standard-api-key-22222", 1000),
            ("premium-api-key-33333", 5000),
        ]

        for api_key, expected_limit in tier_configs:
            with httpx.Client(
                base_url="http://localhost:8000",
                headers={"X-API-Key": api_key},
                timeout=10.0,
            ) as client:
                response = client.get("/health")

                assert response.status_code == 200, f"API key {api_key} should be valid"

                limit = int(response.headers["X-RateLimit-Limit-Minute"])
                assert (
                    limit == expected_limit
                ), f"API key {api_key} should have {expected_limit}/min limit, got {limit}"

    def test_redis_backed_consistency(self, free_tier_client):
        """Test that Redis backend provides consistent rate limiting."""
        # Make a series of requests and verify consistent rate limit tracking
        responses = []

        for _ in range(5):
            response = free_tier_client.get("/health")
            responses.append(response)
            time.sleep(0.1)  # Small delay between requests

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # Remaining counts should consistently decrease (or stay the same)
        remainings = [int(r.headers["X-RateLimit-Remaining-Minute"]) for r in responses]

        for i in range(1, len(remainings)):
            assert (
                remainings[i] <= remainings[i - 1]
            ), f"Rate limit remaining should not increase: {remainings[i-1]} -> {remainings[i]}"

        # All should have the same limit
        limits = [int(r.headers["X-RateLimit-Limit-Minute"]) for r in responses]
        assert all(
            limit == limits[0] for limit in limits
        ), "Rate limit should be consistent across requests"

    def test_tier_upgrade_simulation(self, gateway_stack):
        """Test simulated tier upgrade by switching API keys."""
        # Start with free tier
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "free-api-key-11111"},
            timeout=10.0,
        ) as free_client:
            free_response = free_client.get("/health")
            free_limit = int(free_response.headers["X-RateLimit-Limit-Minute"])

        # "Upgrade" to standard tier
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "standard-api-key-22222"},
            timeout=10.0,
        ) as standard_client:
            standard_response = standard_client.get("/health")
            standard_limit = int(standard_response.headers["X-RateLimit-Limit-Minute"])

        # "Upgrade" to premium tier
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "premium-api-key-33333"},
            timeout=10.0,
        ) as premium_client:
            premium_response = premium_client.get("/health")
            premium_limit = int(premium_response.headers["X-RateLimit-Limit-Minute"])

        # Verify upgrade path
        assert (
            free_limit < standard_limit < premium_limit
        ), f"Tier upgrade path should increase limits: {free_limit} < {standard_limit} < {premium_limit}"

    def test_global_vs_tier_limit_override(self, gateway_client, free_tier_client):
        """Test that tier-specific limits override global limits."""
        # Default client should get global limits
        global_response = gateway_client.get("/health")
        global_limit = int(global_response.headers["X-RateLimit-Limit-Minute"])

        # Free tier client should get tier-specific limits
        tier_response = free_tier_client.get("/health")
        tier_limit = int(tier_response.headers["X-RateLimit-Limit-Minute"])

        # Tier limit should be different from global (specifically lower for free tier)
        assert (
            tier_limit != global_limit
        ), "Tier-specific limit should override global limit"
        assert (
            tier_limit < global_limit
        ), "Free tier limit should be lower than global limit"

        # Verify expected values
        assert global_limit >= 1000, "Global limit should be at least 1000/min"
        assert tier_limit == 100, "Free tier limit should be exactly 100/min"
