"""
Integration tests for Task 10.4: Verify premium tier has higher limits than free tier.

These tests specifically focus on comparing premium tier and free tier rate limits
to ensure the premium tier has demonstrably higher limits as configured in kong.yaml.
"""

import pytest
import time
import httpx


@pytest.mark.integration
class TestPremiumVsFreeTierLimits:
    """Test that premium tier has higher rate limits than free tier."""

    def test_premium_has_higher_limits_than_free(
        self, free_tier_client, premium_tier_client
    ):
        """
        Task 10.4: Verify premium tier has higher limits than free tier.

        This test directly compares the rate limits of premium vs free tiers
        to ensure premium customers get higher quotas.
        """
        # Get rate limits for both tiers
        free_response = free_tier_client.get("/health")
        premium_response = premium_tier_client.get("/health")

        assert free_response.status_code == 200, "Free tier client should work"
        assert premium_response.status_code == 200, "Premium tier client should work"

        # Extract rate limits from headers
        free_limit_minute = int(free_response.headers["X-RateLimit-Limit-Minute"])
        premium_limit_minute = int(premium_response.headers["X-RateLimit-Limit-Minute"])

        # Premium should have higher limits than free
        assert (
            premium_limit_minute > free_limit_minute
        ), f"Premium tier minute limit ({premium_limit_minute}) should be higher than free tier ({free_limit_minute})"

        # Verify specific expected values from configuration
        assert (
            free_limit_minute == 100
        ), f"Free tier should have 100/min limit, got {free_limit_minute}"
        assert (
            premium_limit_minute == 5000
        ), f"Premium tier should have 5000/min limit, got {premium_limit_minute}"

        # Premium should be 50x higher than free
        ratio = premium_limit_minute / free_limit_minute
        assert (
            ratio == 50.0
        ), f"Premium should be 50x free tier limit, actual ratio: {ratio}"

    def test_premium_vs_free_remaining_capacity(
        self, free_tier_client, premium_tier_client
    ):
        """
        Test that premium tier starts with higher remaining capacity than free tier.

        This verifies that premium customers can make more requests from the start.
        """
        # Get initial remaining counts
        free_response = free_tier_client.get("/health")
        premium_response = premium_tier_client.get("/health")

        free_remaining = int(free_response.headers["X-RateLimit-Remaining-Minute"])
        premium_remaining = int(
            premium_response.headers["X-RateLimit-Remaining-Minute"]
        )

        # Premium should have more remaining capacity (unless very close to window reset)
        assert (
            premium_remaining > free_remaining
        ), f"Premium tier remaining ({premium_remaining}) should be higher than free tier ({free_remaining})"

        # Premium should have significantly more capacity
        assert (
            premium_remaining >= 4900
        ), f"Premium tier should have at least 4900 remaining, got {premium_remaining}"
        assert (
            free_remaining <= 100
        ), f"Free tier should have at most 100 remaining, got {free_remaining}"

    def test_premium_vs_free_sustained_usage(
        self, free_tier_client, premium_tier_client
    ):
        """
        Test that premium tier can sustain higher request volumes than free tier.

        This demonstrates the practical difference between tiers.
        """
        # Make multiple requests to demonstrate capacity difference
        free_requests = 0
        premium_requests = 0

        # Count how many requests each tier can make (limited to avoid exhaustion)
        max_test_requests = 50

        # Test free tier capacity
        for i in range(max_test_requests):
            response = free_tier_client.get("/health")
            if response.status_code == 200:
                free_requests += 1
            else:
                break  # Stop on rate limit
            time.sleep(0.01)  # Small delay

        # Test premium tier capacity (same number of requests)
        for i in range(max_test_requests):
            response = premium_tier_client.get("/health")
            if response.status_code == 200:
                premium_requests += 1
            else:
                break  # Stop on rate limit
            time.sleep(0.01)  # Small delay

        # Premium should be able to handle the same number of requests without hitting limits
        # (Since 50 << 5000, premium should handle all requests)
        assert (
            premium_requests >= free_requests
        ), f"Premium tier should handle at least as many requests as free tier: {premium_requests} vs {free_requests}"

        # Premium should likely handle all test requests since 50 << 5000
        assert (
            premium_requests == max_test_requests
        ), f"Premium tier should handle all {max_test_requests} test requests, handled {premium_requests}"

    def test_premium_vs_free_api_key_validation(self, gateway_stack):
        """
        Test that the correct API keys map to the correct tier limits.

        This ensures premium and free API keys are correctly configured.
        """
        # Test free tier API key
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "free-api-key-11111"},
            timeout=10.0,
        ) as free_client:
            free_response = free_client.get("/health")
            assert free_response.status_code == 200
            free_limit = int(free_response.headers["X-RateLimit-Limit-Minute"])

        # Test premium tier API key
        with httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "premium-api-key-33333"},
            timeout=10.0,
        ) as premium_client:
            premium_response = premium_client.get("/health")
            assert premium_response.status_code == 200
            premium_limit = int(premium_response.headers["X-RateLimit-Limit-Minute"])

        # Verify the mapping
        assert free_limit == 100, f"Free API key should map to 100/min limit, got {free_limit}"
        assert (
            free_limit == 100
        ), f"Free API key should map to 100/min limit, got {free_limit}"
        assert (
            premium_limit == 5000
        ), f"Premium API key should map to 5000/min limit, got {premium_limit}"

        # Premium should be higher
        assert (
            premium_limit > free_limit
        ), "Premium API key should have higher limits than free API key"

    def test_premium_vs_free_tier_configuration_validation(self, gateway_config):
        """
        Test that premium tier configuration has higher limits than free tier in kong.yaml.

        This validates the configuration at the source.
        """
        consumers = gateway_config.get("consumers", [])

        # Find free and premium tier consumers
        free_consumer = None
        premium_consumer = None

        for consumer in consumers:
            if consumer.get("username") == "free-tier-consumer":
                free_consumer = consumer
            elif consumer.get("username") == "premium-tier-consumer":
                premium_consumer = consumer

        # Ensure both consumers exist
        assert free_consumer is not None, "Free tier consumer should be configured"
        assert (
            premium_consumer is not None
        ), "Premium tier consumer should be configured"

        # Extract rate limiting configurations
        free_rate_config = None
        premium_rate_config = None

        for plugin in free_consumer.get("plugins", []):
            if plugin.get("name") == "rate-limiting":
                free_rate_config = plugin["config"]
                break

        for plugin in premium_consumer.get("plugins", []):
            if plugin.get("name") == "rate-limiting":
                premium_rate_config = plugin["config"]
                break

        # Ensure rate limiting is configured for both
        assert (
            free_rate_config is not None
        ), "Free tier should have rate limiting configured"
        assert (
            premium_rate_config is not None
        ), "Premium tier should have rate limiting configured"

        # Compare limits across all time windows
        time_windows = ["minute", "hour", "day"]

        for window in time_windows:
            if window in free_rate_config and window in premium_rate_config:
                free_limit = free_rate_config[window]
                premium_limit = premium_rate_config[window]

                assert (
                    premium_limit > free_limit
                ), f"Premium {window} limit ({premium_limit}) should be higher than free {window} limit ({free_limit})"

        # Verify specific expected values
        assert free_rate_config["minute"] == 100, "Free tier should have 100/min in config"
        assert premium_rate_config["minute"] == 5000, "Premium tier should have 5000/min in config"
        assert free_rate_config["hour"] == 1000, "Free tier should have 1000/hour in config"
        assert (
            premium_rate_config["hour"] == 100000
        ), "Premium tier should have 100000/hour in config"
        assert free_rate_config["day"] == 2500, "Free tier should have 2500/day in config"
        assert premium_rate_config["day"] == 500000, "Premium tier should have 500000/day in config"
        assert (
            free_rate_config["minute"] == 100
        ), "Free tier should have 100/min in config"
        assert (
            premium_rate_config["minute"] == 5000
        ), "Premium tier should have 5000/min in config"
        assert (
            free_rate_config["hour"] == 1000
        ), "Free tier should have 1000/hour in config"
        assert (
            premium_rate_config["hour"] == 100000
        ), "Premium tier should have 100000/hour in config"
        assert (
            free_rate_config["day"] == 2500
        ), "Free tier should have 2500/day in config"
        assert (
            premium_rate_config["day"] == 500000
        ), "Premium tier should have 500000/day in config"

    def test_premium_vs_free_isolation(self, free_tier_client, premium_tier_client):
        """
        Test that premium and free tier rate limits are completely isolated.

        Premium customer usage should not affect free customer quotas and vice versa.
        """
        # Get initial state for both tiers
        free_initial = free_tier_client.get("/health")
        premium_initial = premium_tier_client.get("/health")

        free_remaining_before = int(
            free_initial.headers["X-RateLimit-Remaining-Minute"]
        )
        premium_remaining_before = int(
            premium_initial.headers["X-RateLimit-Remaining-Minute"]
        )

        # Make several requests with premium tier only
        premium_requests = min(20, premium_remaining_before)  # Don't exhaust premium
        for _ in range(premium_requests):
            response = premium_tier_client.get("/health")
            assert response.status_code == 200, "Premium requests should succeed"
            time.sleep(0.01)

        # Check state after premium tier usage
        free_after = free_tier_client.get("/health")
        premium_after = premium_tier_client.get("/health")

        free_remaining_after = int(free_after.headers["X-RateLimit-Remaining-Minute"])
        premium_remaining_after = int(
            premium_after.headers["X-RateLimit-Remaining-Minute"]
        )

        # Free tier should be completely unaffected
        assert (
            abs(free_remaining_after - free_remaining_before) <= 1
        ), "Free tier should be unaffected by premium tier usage"

        # Premium tier should have decreased
        assert (
            premium_remaining_after < premium_remaining_before
        ), "Premium tier should decrease after requests"

        # The decrease should be approximately equal to the requests made
        premium_decrease = premium_remaining_before - premium_remaining_after
        assert (
            abs(premium_decrease - premium_requests) <= 2
        ), f"Premium tier decrease ({premium_decrease}) should approximately match requests made ({premium_requests})"

    def test_premium_vs_free_tier_multiplier(
        self, free_tier_client, premium_tier_client
    ):
        """
        Test that premium tier provides a significant multiplier over free tier.

        This verifies the business value proposition of premium tier.
        """
        free_response = free_tier_client.get("/health")
        premium_response = premium_tier_client.get("/health")

        free_limit = int(free_response.headers["X-RateLimit-Limit-Minute"])
        premium_limit = int(premium_response.headers["X-RateLimit-Limit-Minute"])

        # Calculate the multiplier
        multiplier = premium_limit / free_limit

        # Premium should provide substantial improvement
        assert (
            multiplier >= 10
        ), f"Premium should provide at least 10x improvement, got {multiplier}x"
        assert (
            multiplier == 50
        ), f"Premium should provide exactly 50x improvement, got {multiplier}x"

        # Verify this makes business sense
        assert (
            premium_limit >= 1000
        ), "Premium tier should allow at least 1000 requests/minute"
        assert free_limit <= 200, "Free tier should be limited to reasonable free usage"


@pytest.mark.integration
class TestTierConfigurationIntegrity:
    """Test the integrity of tier configuration across the system."""

    def test_all_tier_consumers_have_correct_hierarchy(
        self, free_tier_client, standard_tier_client, premium_tier_client
    ):
        """
        Task 10.4: Test the complete tier hierarchy is correctly configured.

        Verify: Free < Standard < Premium for all time windows.
        """
        # Get limits for all tiers
        clients = {
            "free": free_tier_client,
            "standard": standard_tier_client,
            "premium": premium_tier_client,
        }

        limits = {}
        for tier_name, client in clients.items():
            response = client.get("/health")
            assert response.status_code == 200, f"{tier_name} tier should work"
            limits[tier_name] = int(response.headers["X-RateLimit-Limit-Minute"])

        # Verify hierarchy
        assert (
            limits["free"] < limits["standard"]
        ), f"Free ({limits['free']}) should be less than Standard ({limits['standard']})"
        assert (
            limits["standard"] < limits["premium"]
        ), f"Standard ({limits['standard']}) should be less than Premium ({limits['premium']})"
        assert (
            limits["free"] < limits["premium"]
        ), f"Free ({limits['free']}) should be less than Premium ({limits['premium']})"

        # Verify specific values
        expected_limits = {"free": 100, "standard": 1000, "premium": 5000}

        for tier_name, expected_limit in expected_limits.items():
            actual_limit = limits[tier_name]
            assert (
                actual_limit == expected_limit
            ), f"{tier_name.title()} tier should have {expected_limit}/min, got {actual_limit}/min"

        # Verify meaningful differences
        standard_multiplier = limits["standard"] / limits["free"]
        premium_multiplier = limits["premium"] / limits["free"]

        assert (
            standard_multiplier == 10
        ), f"Standard should be 10x free, got {standard_multiplier}x"
        assert (
            premium_multiplier == 50
        ), f"Premium should be 50x free, got {premium_multiplier}x"

    def test_premium_tier_justifies_cost_difference(
        self, free_tier_client, premium_tier_client
    ):
        """
        Task 10.4: Test that premium tier provides sufficient value over free tier.

        This simulates a business decision: does premium provide enough extra capacity
        to justify premium pricing?
        """
        free_response = free_tier_client.get("/health")
        premium_response = premium_tier_client.get("/health")

        free_limit = int(free_response.headers["X-RateLimit-Limit-Minute"])
        premium_limit = int(premium_response.headers["X-RateLimit-Limit-Minute"])

        # Business logic: Premium should provide substantial value
        improvement_factor = premium_limit / free_limit

        # At least 10x improvement to justify premium pricing
        assert (
            improvement_factor >= 10
        ), f"Premium should provide at least 10x improvement to justify cost, got {improvement_factor}x"

        # Check absolute values make sense for business usage
        assert free_limit >= 50, "Free tier should allow meaningful testing"
        assert free_limit <= 200, "Free tier should encourage upgrades"
        assert premium_limit >= 1000, "Premium tier should handle production workloads"

        # Demonstrate capacity difference in practical terms
        minutes_of_free_usage = free_limit  # requests per minute = minutes of 1 req/min
        minutes_of_premium_usage = premium_limit

        assert (
            minutes_of_premium_usage > minutes_of_free_usage * 10
        ), "Premium should provide at least 10x more sustained usage capacity"

        print(f"Free tier: {free_limit} requests/minute")
        print(f"Premium tier: {premium_limit} requests/minute")
        print(f"Premium provides {improvement_factor}x improvement")
        print(
            f"Premium can sustain 1 req/sec for {premium_limit/60:.0f} hours vs {free_limit/60:.1f} hours for free"
        )
