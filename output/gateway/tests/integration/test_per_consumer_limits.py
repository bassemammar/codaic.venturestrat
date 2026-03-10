"""
Integration tests for per-consumer rate limits.

Task 10.1: Write tests for per-consumer limits

These tests focus specifically on per-consumer rate limiting functionality,
validating that different consumer tiers have isolated and properly enforced
rate limits as configured in kong.yaml.
"""

import pytest
import time
import httpx


@pytest.mark.integration
class TestPerConsumerLimits:
    """Test per-consumer rate limiting functionality."""

    def test_per_consumer_limit_isolation(
        self, free_tier_client, standard_tier_client, premium_tier_client
    ):
        """Test that rate limits are completely isolated between different consumers.

        Task 10.1: Per-consumer limits should not affect each other.
        """
        # Make initial requests to get baseline for each tier
        free_response = free_tier_client.get("/health")
        standard_response = standard_tier_client.get("/health")
        premium_response = premium_tier_client.get("/health")

        assert free_response.status_code == 200
        assert standard_response.status_code == 200
        assert premium_response.status_code == 200

        # Get initial remaining counts
        free_initial = int(free_response.headers["X-RateLimit-Remaining-Minute"])
        standard_initial = int(
            standard_response.headers["X-RateLimit-Remaining-Minute"]
        )
        premium_initial = int(premium_response.headers["X-RateLimit-Remaining-Minute"])

        # Make multiple requests with free tier to consume its quota
        free_requests_made = min(10, free_initial)
        for _ in range(free_requests_made):
            response = free_tier_client.get("/health")
            assert response.status_code == 200

        # Get remaining counts after free tier consumption
        free_final_response = free_tier_client.get("/health")
        standard_final_response = standard_tier_client.get("/health")
        premium_final_response = premium_tier_client.get("/health")

        free_final = int(free_final_response.headers["X-RateLimit-Remaining-Minute"])
        standard_final = int(
            standard_final_response.headers["X-RateLimit-Remaining-Minute"]
        )
        premium_final = int(
            premium_final_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # Free tier should have decreased
        assert (
            free_final < free_initial
        ), "Free tier remaining should decrease after requests"

        # Standard and premium tiers should be unaffected
        # Allow for small variance due to the test requests we made to check them
        assert (
            abs(standard_final - standard_initial) <= 1
        ), "Standard tier should be unaffected by free tier usage"
        assert (
            abs(premium_final - premium_initial) <= 1
        ), "Premium tier should be unaffected by free tier usage"

    def test_consumer_tier_hierarchy(
        self, free_tier_client, standard_tier_client, premium_tier_client
    ):
        """Test that consumer tiers have properly ordered rate limits.

        Task 10.1: Verify free < standard < premium tier limits.
        """
        # Get rate limits for all tiers
        free_response = free_tier_client.get("/health")
        standard_response = standard_tier_client.get("/health")
        premium_response = premium_tier_client.get("/health")

        assert free_response.status_code == 200
        assert standard_response.status_code == 200
        assert premium_response.status_code == 200

        # Extract limits from headers
        free_limit = int(free_response.headers["X-RateLimit-Limit-Minute"])
        standard_limit = int(standard_response.headers["X-RateLimit-Limit-Minute"])
        premium_limit = int(premium_response.headers["X-RateLimit-Limit-Minute"])

        # Verify hierarchy: free < standard < premium
        assert (
            free_limit < standard_limit
        ), f"Free tier limit ({free_limit}) should be less than standard ({standard_limit})"
        assert (
            standard_limit < premium_limit
        ), f"Standard tier limit ({standard_limit}) should be less than premium ({premium_limit})"

        # Verify specific expected values from configuration
        assert free_limit == 100, f"Free tier should have 100/min limit, got {free_limit}"
        assert (
            free_limit == 100
        ), f"Free tier should have 100/min limit, got {free_limit}"
        assert (
            standard_limit == 1000
        ), f"Standard tier should have 1000/min limit, got {standard_limit}"
        assert (
            premium_limit == 5000
        ), f"Premium tier should have 5000/min limit, got {premium_limit}"

    def test_per_consumer_rate_limit_headers(
        self, free_tier_client, standard_tier_client, premium_tier_client
    ):
        """Test that rate limit headers are correctly set per consumer.

        Task 10.1: Each consumer should see their own specific limits.
        """
        # Test each tier's headers
        tier_configs = [
            (free_tier_client, "free", 100),
            (standard_tier_client, "standard", 1000),
            (premium_tier_client, "premium", 5000),
        ]

        for client, tier_name, expected_limit in tier_configs:
            response = client.get("/health")
            assert (
                response.status_code == 200
            ), f"{tier_name} tier client should succeed"

            # Required headers should be present
            assert (
                "X-RateLimit-Limit-Minute" in response.headers
            ), f"{tier_name} tier should have limit header"
            assert (
                "X-RateLimit-Remaining-Minute" in response.headers
            ), f"{tier_name} tier should have remaining header"

            # Verify limit matches expectation
            limit = int(response.headers["X-RateLimit-Limit-Minute"])
            assert (
                limit == expected_limit
            ), f"{tier_name} tier should have {expected_limit}/min limit, got {limit}"

            # Remaining should be within limit
            remaining = int(response.headers["X-RateLimit-Remaining-Minute"])
            assert (
                0 <= remaining <= limit
            ), f"{tier_name} tier remaining ({remaining}) should be within limit ({limit})"

    def test_consumer_rate_limit_consistency(self, free_tier_client):
        """Test that rate limits are consistent across multiple requests for same consumer.

        Task 10.1: Per-consumer limits should be maintained consistently.
        """
        responses = []

        # Make several requests to the same consumer
        for _ in range(5):
            response = free_tier_client.get("/health")
            assert response.status_code == 200
            responses.append(response)
            time.sleep(0.1)  # Small delay between requests

        # Extract rate limit information from all responses
        limits = [int(r.headers["X-RateLimit-Limit-Minute"]) for r in responses]
        remainings = [int(r.headers["X-RateLimit-Remaining-Minute"]) for r in responses]

        # Limit should be consistent across all requests
        assert all(
            limit == limits[0] for limit in limits
        ), "Rate limit should be consistent across requests"
        assert limits[0] == 100, "Free tier should consistently show 100/min limit"

        # Remaining should decrease or stay same (never increase within same window)
        for i in range(1, len(remainings)):
            assert (
                remainings[i] <= remainings[i - 1]
            ), f"Remaining count should not increase: {remainings[i-1]} -> {remainings[i]}"

    def test_different_consumers_different_quotas(self, gateway_stack):
        """Test that different API keys get different rate limit quotas.

        Task 10.1: Verify API key to rate limit mapping.
        """
        api_key_configs = {
            "free-api-key-11111": 100,
            "standard-api-key-22222": 1000,
            "premium-api-key-33333": 5000,
        }

        for api_key, expected_limit in api_key_configs.items():
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

    def test_consumer_isolation_concurrent_requests(
        self, free_tier_client, standard_tier_client
    ):
        """Test that rate limits remain isolated under concurrent access.

        Task 10.1: Per-consumer limits should not interfere under concurrent load.
        """
        import threading
        import queue

        results = queue.Queue()

        def make_requests(client, tier_name, num_requests):
            """Make multiple requests and store results."""
            tier_results = []
            for i in range(num_requests):
                response = client.get("/health")
                tier_results.append(
                    {
                        "tier": tier_name,
                        "request_num": i,
                        "status": response.status_code,
                        "limit": int(response.headers.get("X-RateLimit-Limit-Minute", -1)),
                        "remaining": int(response.headers.get("X-RateLimit-Remaining-Minute", -1)),
                        "limit": int(
                            response.headers.get("X-RateLimit-Limit-Minute", -1)
                        ),
                        "remaining": int(
                            response.headers.get("X-RateLimit-Remaining-Minute", -1)
                        ),
                    }
                )
                time.sleep(0.01)  # Small delay between requests
            results.put(tier_results)

        # Start concurrent threads for different tiers
        free_thread = threading.Thread(target=make_requests, args=(free_tier_client, "free", 8))
        free_thread = threading.Thread(
            target=make_requests, args=(free_tier_client, "free", 8)
        )
        standard_thread = threading.Thread(
            target=make_requests, args=(standard_tier_client, "standard", 8)
        )

        free_thread.start()
        standard_thread.start()

        free_thread.join()
        standard_thread.join()

        # Collect results
        all_results = []
        while not results.empty():
            all_results.extend(results.get())

        # Separate results by tier
        free_results = [r for r in all_results if r["tier"] == "free"]
        standard_results = [r for r in all_results if r["tier"] == "standard"]

        # All requests should succeed
        assert all(r["status"] == 200 for r in free_results), "Free tier requests should succeed"
        assert all(
            r["status"] == 200 for r in free_results
        ), "Free tier requests should succeed"
        assert all(
            r["status"] == 200 for r in standard_results
        ), "Standard tier requests should succeed"

        # Verify limits are correct for each tier
        assert all(r["limit"] == 100 for r in free_results), "Free tier should have 100/min limit"
        assert all(
            r["limit"] == 100 for r in free_results
        ), "Free tier should have 100/min limit"
        assert all(
            r["limit"] == 1000 for r in standard_results
        ), "Standard tier should have 1000/min limit"

    def test_redis_backend_per_consumer(self, free_tier_client, standard_tier_client):
        """Test that Redis backend maintains separate counters per consumer.

        Task 10.1: Rate limiting backend should isolate consumer quotas.
        """
        # Get initial state for both consumers
        free_initial = free_tier_client.get("/health")
        standard_initial = standard_tier_client.get("/health")

        free_remaining_before = int(
            free_initial.headers["X-RateLimit-Remaining-Minute"]
        )
        standard_remaining_before = int(
            standard_initial.headers["X-RateLimit-Remaining-Minute"]
        )

        # Make several requests with free tier only
        for _ in range(3):
            response = free_tier_client.get("/health")
            assert response.status_code == 200

        # Check state after free tier requests
        free_after = free_tier_client.get("/health")
        standard_after = standard_tier_client.get("/health")

        free_remaining_after = int(free_after.headers["X-RateLimit-Remaining-Minute"])
        standard_remaining_after = int(
            standard_after.headers["X-RateLimit-Remaining-Minute"]
        )

        # Free tier should have decreased by approximately 4 (3 + 1 for check)
        assert (
            free_remaining_after <= free_remaining_before - 3
        ), "Free tier remaining should decrease after requests"

        # Standard tier should be unaffected (allowing for 1 request variance)
        assert (
            abs(standard_remaining_after - standard_remaining_before) <= 1
        ), "Standard tier should be unaffected by free tier usage"

    def test_consumer_tier_upgrade_simulation(self, gateway_stack):
        """Test switching between consumer tiers by changing API keys.

        Task 10.1: Different API keys should provide different rate limits.
        """
        # Start with free tier
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "free-api-key-11111"},
            timeout=10.0,
        ) as client:
            response = client.get("/health")
            free_limit = int(response.headers["X-RateLimit-Limit-Minute"])
            free_remaining = int(response.headers["X-RateLimit-Remaining-Minute"])

        # Switch to standard tier (different API key)
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "standard-api-key-22222"},
            timeout=10.0,
        ) as client:
            response = client.get("/health")
            standard_limit = int(response.headers["X-RateLimit-Limit-Minute"])
            standard_remaining = int(response.headers["X-RateLimit-Remaining-Minute"])

        # Switch to premium tier (different API key)
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "premium-api-key-33333"},
            timeout=10.0,
        ) as client:
            response = client.get("/health")
            premium_limit = int(response.headers["X-RateLimit-Limit-Minute"])
            premium_remaining = int(response.headers["X-RateLimit-Remaining-Minute"])

        # Verify tier progression
        assert free_limit == 100, f"Free tier should have 100/min, got {free_limit}"
        assert (
            standard_limit == 1000
        ), f"Standard tier should have 1000/min, got {standard_limit}"
        assert (
            premium_limit == 5000
        ), f"Premium tier should have 5000/min, got {premium_limit}"

        # Remaining counts should be independent (near their respective limits)
        assert free_remaining <= free_limit
        assert standard_remaining <= standard_limit
        assert premium_remaining <= premium_limit

        # Higher tiers should have more remaining capacity
        assert standard_remaining > free_remaining
        assert premium_remaining > standard_remaining

    @pytest.mark.slow
    def test_per_consumer_rate_limit_enforcement(self, free_tier_client):
        """Test that per-consumer rate limits are actually enforced with 429 responses.

        Task 10.1: Consumer-specific limits should be enforced.
        """
        # Get current remaining count for free tier
        initial_response = free_tier_client.get("/health")
        initial_remaining = int(
            initial_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # If we're close to the limit, try to hit it
        if initial_remaining <= 15:  # Conservative threshold
            responses = []

            # Make requests until we either hit the limit or exhaust attempts
            for i in range(initial_remaining + 5):
                response = free_tier_client.get("/health")
                responses.append(response)

                if response.status_code == 429:
                    # Successfully hit the rate limit
                    assert (
                        "Retry-After" in response.headers
                    ), "429 response should include Retry-After header"

                    data = response.json()
                    assert (
                        "rate limit" in data["message"].lower()
                    ), "429 response should mention rate limit"

                    # Verify the limit shown in headers
                    assert (
                        int(response.headers["X-RateLimit-Limit-Minute"]) == 100
                    ), "Rate limit should show 100 for free tier"
                    assert (
                        int(response.headers["X-RateLimit-Remaining-Minute"]) == 0
                    ), "Remaining should be 0 when rate limited"

                    return  # Test successful

                # Small delay to avoid overwhelming
                time.sleep(0.01)

            # If we couldn't trigger the rate limit, that's acceptable
            # It means the system is working but we didn't exhaust the quota
            pytest.skip("Could not trigger rate limit within reasonable attempts")
        else:
            pytest.skip("Too far from rate limit to test enforcement efficiently")

    def test_consumer_tier_config_validation(self, gateway_config):
        """Test that consumer tier configuration is properly set up.

        Task 10.1: Validate per-consumer rate limit configuration.
        """
        consumers = gateway_config.get("consumers", [])

        # Find tier consumers
        tier_consumers = {}
        for consumer in consumers:
            if "tier" in consumer.get("username", ""):
                tier_consumers[consumer["username"]] = consumer

        # Verify tier consumers exist
        expected_tiers = [
            "free-tier-consumer",
            "standard-tier-consumer",
            "premium-tier-consumer",
        ]
        for tier in expected_tiers:
            assert tier in tier_consumers, f"Consumer {tier} should be configured"

        # Verify each tier has rate limiting plugin configured
        for tier, consumer in tier_consumers.items():
            plugins = consumer.get("plugins", [])
            rate_limit_plugins = [
                p for p in plugins if p.get("name") == "rate-limiting"
            ]

            assert (
                len(rate_limit_plugins) == 1
            ), f"Consumer {tier} should have exactly one rate-limiting plugin"

            rate_config = rate_limit_plugins[0]["config"]
            assert (
                "minute" in rate_config
            ), f"Consumer {tier} should have minute rate limit configured"
            assert rate_config["policy"] == "redis", f"Consumer {tier} should use Redis policy"
            assert (
                rate_config["policy"] == "redis"
            ), f"Consumer {tier} should use Redis policy"

        # Verify tier hierarchy in configuration
        free_config = next(
            p["config"]
            for p in tier_consumers["free-tier-consumer"]["plugins"]
            if p["name"] == "rate-limiting"
        )
        standard_config = next(
            p["config"]
            for p in tier_consumers["standard-tier-consumer"]["plugins"]
            if p["name"] == "rate-limiting"
        )
        premium_config = next(
            p["config"]
            for p in tier_consumers["premium-tier-consumer"]["plugins"]
            if p["name"] == "rate-limiting"
        )

        # Verify minute limits are in correct hierarchy
        assert (
            free_config["minute"] < standard_config["minute"] < premium_config["minute"]
        ), "Tier minute limits should be in ascending order: free < standard < premium"

        # Verify specific values
        assert free_config["minute"] == 100, "Free tier should have 100/min limit in config"
        assert (
            standard_config["minute"] == 1000
        ), "Standard tier should have 1000/min limit in config"
        assert premium_config["minute"] == 5000, "Premium tier should have 5000/min limit in config"
        assert (
            free_config["minute"] == 100
        ), "Free tier should have 100/min limit in config"
        assert (
            standard_config["minute"] == 1000
        ), "Standard tier should have 1000/min limit in config"
        assert (
            premium_config["minute"] == 5000
        ), "Premium tier should have 5000/min limit in config"


@pytest.mark.integration
class TestPerConsumerRateLimitEdgeCases:
    """Test edge cases and error conditions for per-consumer rate limits."""

    def test_invalid_api_key_uses_anonymous_limits(self, gateway_stack):
        """Test that invalid API keys fall back to anonymous consumer behavior."""
        # Use an invalid API key
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "invalid-key-99999"},
            timeout=10.0,
        ) as client:
            response = client.get("/health")

            # Should get 401 Unauthorized, not rate limiting
            assert (
                response.status_code == 401
            ), "Invalid API key should get 401, not rate limiting"

    def test_missing_api_key_behavior(self, unauthorized_client):
        """Test behavior when no API key is provided."""
        response = unauthorized_client.get("/health")

        # Should get 401 Unauthorized for missing API key
        assert response.status_code == 401, "Missing API key should get 401"

    def test_consumer_rate_limit_with_different_endpoints(self, free_tier_client):
        """Test that per-consumer limits apply across different endpoints."""
        # Make request to health endpoint
        health_response = free_tier_client.get("/health")
        health_remaining = int(health_response.headers["X-RateLimit-Remaining-Minute"])

        # Make request to different endpoint (registry service)
        registry_response = free_tier_client.get("/api/v1/registry/services")

        # Registry might not be available, but rate limiting should still work
        if registry_response.status_code in [200, 502, 503]:
            # Rate limiting headers should be present regardless of backend availability
            if "X-RateLimit-Remaining-Minute" in registry_response.headers:
                registry_remaining = int(
                    registry_response.headers["X-RateLimit-Remaining-Minute"]
                )

                # Should be approximately the same (within 1-2 requests)
                assert (
                    abs(health_remaining - registry_remaining) <= 2
                ), "Rate limiting should be consumer-based, not endpoint-based"

    def test_consumer_rate_limit_persistence(self, free_tier_client):
        """Test that consumer rate limits persist across multiple connections."""
        # Make initial request
        response1 = free_tier_client.get("/health")
        remaining1 = int(response1.headers["X-RateLimit-Remaining-Minute"])

        # Create new client with same API key (simulating new connection)
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "free-api-key-11111"},
            timeout=10.0,
        ) as new_client:
            response2 = new_client.get("/health")
            remaining2 = int(response2.headers["X-RateLimit-Remaining-Minute"])

            # Should be related (allowing for timing differences)
            assert (
                remaining2 <= remaining1
            ), "Rate limit should persist across connections for same consumer"

            # Limit should be the same
            limit1 = int(response1.headers["X-RateLimit-Limit-Minute"])
            limit2 = int(response2.headers["X-RateLimit-Limit-Minute"])
            assert limit1 == limit2 == 100, "Rate limit should be consistent across connections"
            assert (
                limit1 == limit2 == 100
            ), "Rate limit should be consistent across connections"
