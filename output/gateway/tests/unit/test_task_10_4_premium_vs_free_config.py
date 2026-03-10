"""
Unit tests for Task 10.4: Verify premium tier has higher limits than free tier.

These tests validate the configuration in kong.yaml to ensure premium tier
has higher rate limits than free tier without requiring a running gateway.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def kong_config() -> Dict[str, Any]:
    """Load kong.yaml configuration for testing."""
    config_path = Path(__file__).parent.parent.parent / "kong.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@pytest.mark.unit
class TestTask104PremiumVsFreeConfig:
    """Unit tests for Task 10.4: Premium tier has higher limits than free tier."""

    def test_premium_tier_has_higher_limits_than_free_tier_config(self, kong_config):
        """
        Task 10.4: Verify premium tier has higher limits than free tier in configuration.

        This test validates that the premium tier consumer is configured with
        higher rate limits than the free tier consumer in all time windows.
        """
        consumers = kong_config.get("consumers", [])

        # Find free and premium tier consumers
        free_consumer = None
        premium_consumer = None

        for consumer in consumers:
            if consumer.get("username") == "free-tier-consumer":
                free_consumer = consumer
            elif consumer.get("username") == "premium-tier-consumer":
                premium_consumer = consumer

        # Ensure both consumers exist
        assert free_consumer is not None, "Free tier consumer should be configured in kong.yaml"
        assert (
            free_consumer is not None
        ), "Free tier consumer should be configured in kong.yaml"
        assert (
            premium_consumer is not None
        ), "Premium tier consumer should be configured in kong.yaml"

        # Extract rate limiting plugin configurations
        free_rate_config = None
        premium_rate_config = None

        for plugin in free_consumer.get("plugins", []):
            if plugin.get("name") == "rate-limiting":
                free_rate_config = plugin.get("config", {})
                break

        for plugin in premium_consumer.get("plugins", []):
            if plugin.get("name") == "rate-limiting":
                premium_rate_config = plugin.get("config", {})
                break

        # Ensure rate limiting is configured for both tiers
        assert free_rate_config is not None, "Free tier should have rate limiting plugin configured"
        assert (
            free_rate_config is not None
        ), "Free tier should have rate limiting plugin configured"
        assert (
            premium_rate_config is not None
        ), "Premium tier should have rate limiting plugin configured"

        # Compare rate limits across all time windows
        time_windows = ["minute", "hour", "day"]

        for window in time_windows:
            assert window in free_rate_config, f"Free tier should have {window} limit configured"
            assert (
                window in free_rate_config
            ), f"Free tier should have {window} limit configured"
            assert (
                window in premium_rate_config
            ), f"Premium tier should have {window} limit configured"

            free_limit = free_rate_config[window]
            premium_limit = premium_rate_config[window]

            assert (
                premium_limit > free_limit
            ), f"Premium {window} limit ({premium_limit}) should be higher than free {window} limit ({free_limit})"

        # Verify specific expected values for Task 10.4
        assert free_rate_config["minute"] == 100, "Free tier should have 100 requests per minute"
        assert (
            free_rate_config["minute"] == 100
        ), "Free tier should have 100 requests per minute"
        assert (
            premium_rate_config["minute"] == 5000
        ), "Premium tier should have 5000 requests per minute"

        # Premium should be 50x higher than free for minute window
        minute_ratio = premium_rate_config["minute"] / free_rate_config["minute"]
        assert (
            minute_ratio == 50.0
        ), f"Premium should be 50x free tier per minute, got {minute_ratio}x"

        # Verify hour limits
        assert free_rate_config["hour"] == 1000, "Free tier should have 1000 requests per hour"
        assert (
            free_rate_config["hour"] == 1000
        ), "Free tier should have 1000 requests per hour"
        assert (
            premium_rate_config["hour"] == 100000
        ), "Premium tier should have 100000 requests per hour"

        # Premium should be 100x higher than free for hour window
        hour_ratio = premium_rate_config["hour"] / free_rate_config["hour"]
        assert (
            hour_ratio == 100.0
        ), f"Premium should be 100x free tier per hour, got {hour_ratio}x"

        # Verify day limits
        assert free_rate_config["day"] == 2500, "Free tier should have 2500 requests per day"
        assert (
            free_rate_config["day"] == 2500
        ), "Free tier should have 2500 requests per day"
        assert (
            premium_rate_config["day"] == 500000
        ), "Premium tier should have 500000 requests per day"

        # Premium should be 200x higher than free for day window
        day_ratio = premium_rate_config["day"] / free_rate_config["day"]
        assert (
            day_ratio == 200.0
        ), f"Premium should be 200x free tier per day, got {day_ratio}x"

    def test_premium_vs_free_api_key_configuration(self, kong_config):
        """
        Test that premium and free tier API keys are correctly configured.

        This ensures the API key mapping is correct for each tier.
        """
        consumers = kong_config.get("consumers", [])

        # Find tier consumers and their API keys
        tier_api_keys = {}

        for consumer in consumers:
            username = consumer.get("username", "")
            if "tier" in username:
                keyauth_credentials = consumer.get("keyauth_credentials", [])
                if keyauth_credentials:
                    api_key = keyauth_credentials[0].get("key")
                    tier_api_keys[username] = api_key

        # Verify API keys exist for both tiers
        assert "free-tier-consumer" in tier_api_keys, "Free tier should have API key configured"
        assert (
            "free-tier-consumer" in tier_api_keys
        ), "Free tier should have API key configured"
        assert (
            "premium-tier-consumer" in tier_api_keys
        ), "Premium tier should have API key configured"

        # Verify expected API key values
        assert (
            tier_api_keys["free-tier-consumer"] == "free-api-key-11111"
        ), f"Free tier API key should be 'free-api-key-11111', got '{tier_api_keys['free-tier-consumer']}'"

        assert (
            tier_api_keys["premium-tier-consumer"] == "premium-api-key-33333"
        ), f"Premium tier API key should be 'premium-api-key-33333', got '{tier_api_keys['premium-tier-consumer']}'"

        # API keys should be different
        assert (
            tier_api_keys["free-tier-consumer"] != tier_api_keys["premium-tier-consumer"]
            tier_api_keys["free-tier-consumer"]
            != tier_api_keys["premium-tier-consumer"]
        ), "Free and premium tier should have different API keys"

    def test_tier_hierarchy_configuration(self, kong_config):
        """
        Test that all tier consumers form a proper hierarchy: Free < Standard < Premium.

        This verifies the complete tier system configuration.
        """
        consumers = kong_config.get("consumers", [])

        # Extract rate limits for all tier consumers
        tier_limits = {}
        expected_tiers = [
            "free-tier-consumer",
            "standard-tier-consumer",
            "premium-tier-consumer",
        ]

        for tier in expected_tiers:
            tier_consumer = next(
                (c for c in consumers if c.get("username") == tier), None
            )
            assert tier_consumer is not None, f"{tier} should be configured"

            rate_limit_plugin = next(
                (p for p in tier_consumer.get("plugins", []) if p.get("name") == "rate-limiting"),
                (
                    p
                    for p in tier_consumer.get("plugins", [])
                    if p.get("name") == "rate-limiting"
                ),
                None,
            )
            assert (
                rate_limit_plugin is not None
            ), f"{tier} should have rate limiting configured"

            rate_config = rate_limit_plugin.get("config", {})
            tier_limits[tier] = rate_config.get("minute", 0)

        # Verify hierarchy: free < standard < premium
        free_limit = tier_limits["free-tier-consumer"]
        standard_limit = tier_limits["standard-tier-consumer"]
        premium_limit = tier_limits["premium-tier-consumer"]

        assert (
            free_limit < standard_limit
        ), f"Free ({free_limit}) should be less than Standard ({standard_limit})"
        assert (
            standard_limit < premium_limit
        ), f"Standard ({standard_limit}) should be less than Premium ({premium_limit})"
        assert (
            free_limit < premium_limit
        ), f"Free ({free_limit}) should be less than Premium ({premium_limit})"

        # Verify specific expected values
        assert free_limit == 100, f"Free tier should have 100/min, got {free_limit}"
        assert (
            standard_limit == 1000
        ), f"Standard tier should have 1000/min, got {standard_limit}"
        assert (
            premium_limit == 5000
        ), f"Premium tier should have 5000/min, got {premium_limit}"

        # Verify meaningful multipliers
        assert standard_limit / free_limit == 10, "Standard should be 10x free"
        assert premium_limit / free_limit == 50, "Premium should be 50x free"
        assert premium_limit / standard_limit == 5, "Premium should be 5x standard"

    def test_premium_tier_redis_backend_config(self, kong_config):
        """
        Test that premium tier uses Redis backend for rate limiting consistency.

        This ensures premium tier rate limits are properly stored and enforced.
        """
        consumers = kong_config.get("consumers", [])

        premium_consumer = next(
            (c for c in consumers if c.get("username") == "premium-tier-consumer"), None
        )
        assert (
            premium_consumer is not None
        ), "Premium tier consumer should be configured"

        rate_limit_plugin = next(
            (p for p in premium_consumer.get("plugins", []) if p.get("name") == "rate-limiting"),
            (
                p
                for p in premium_consumer.get("plugins", [])
                if p.get("name") == "rate-limiting"
            ),
            None,
        )
        assert (
            rate_limit_plugin is not None
        ), "Premium tier should have rate limiting plugin"

        rate_config = rate_limit_plugin.get("config", {})

        # Verify Redis backend configuration
        assert (
            rate_config.get("policy") == "redis"
        ), "Premium tier should use Redis policy for rate limiting"
        assert "redis_host" in rate_config, "Premium tier should have Redis host configured"
        assert "redis_port" in rate_config, "Premium tier should have Redis port configured"
        assert (
            "redis_host" in rate_config
        ), "Premium tier should have Redis host configured"
        assert (
            "redis_port" in rate_config
        ), "Premium tier should have Redis port configured"

        # Verify fault tolerance
        assert (
            rate_config.get("fault_tolerant") is True
        ), "Premium tier should have fault tolerant rate limiting"

        # Verify headers are not hidden (for monitoring)
        assert (
            rate_config.get("hide_client_headers") is False
        ), "Premium tier should expose rate limit headers"

    def test_premium_tier_tags_configuration(self, kong_config):
        """
        Test that premium tier consumer has appropriate tags for identification.

        This enables proper monitoring and management of premium customers.
        """
        consumers = kong_config.get("consumers", [])

        premium_consumer = next(
            (c for c in consumers if c.get("username") == "premium-tier-consumer"), None
        )
        assert (
            premium_consumer is not None
        ), "Premium tier consumer should be configured"

        # Check consumer tags
        consumer_tags = premium_consumer.get("tags", [])
        assert (
            "premium-tier" in consumer_tags
        ), "Premium consumer should have 'premium-tier' tag"
        assert (
            "external" in consumer_tags
        ), "Premium consumer should have 'external' tag"
        assert (
            "priority" in consumer_tags
        ), "Premium consumer should have 'priority' tag"

        # Check API key tags
        keyauth_credentials = premium_consumer.get("keyauth_credentials", [])
        assert (
            len(keyauth_credentials) > 0
        ), "Premium consumer should have API key credentials"

        api_key_tags = keyauth_credentials[0].get("tags", [])
        assert (
            "premium-tier" in api_key_tags
        ), "Premium API key should have 'premium-tier' tag"

        # Compare with free tier tags
        free_consumer = next(
            (c for c in consumers if c.get("username") == "free-tier-consumer"), None
        )
        assert free_consumer is not None, "Free tier consumer should be configured"

        free_tags = free_consumer.get("tags", [])
        assert "free-tier" in free_tags, "Free consumer should have 'free-tier' tag"
        assert "external" in free_tags, "Free consumer should have 'external' tag"
        assert (
            "priority" not in free_tags
        ), "Free consumer should NOT have 'priority' tag"

    def test_rate_limit_configuration_completeness(self, kong_config):
        """
        Test that both free and premium tiers have complete rate limiting configuration.

        This ensures no critical configuration is missing that could affect enforcement.
        """
        consumers = kong_config.get("consumers", [])
        tier_consumers = ["free-tier-consumer", "premium-tier-consumer"]

        for tier_name in tier_consumers:
            consumer = next((c for c in consumers if c.get("username") == tier_name), None)
            consumer = next(
                (c for c in consumers if c.get("username") == tier_name), None
            )
            assert consumer is not None, f"{tier_name} should be configured"

            # Find rate limiting plugin
            rate_plugin = next(
                (p for p in consumer.get("plugins", []) if p.get("name") == "rate-limiting"),
                (
                    p
                    for p in consumer.get("plugins", [])
                    if p.get("name") == "rate-limiting"
                ),
                None,
            )
            assert (
                rate_plugin is not None
            ), f"{tier_name} should have rate limiting plugin"

            config = rate_plugin.get("config", {})

            # Required configuration fields
            required_fields = [
                "minute",
                "hour",
                "day",
                "policy",
                "redis_host",
                "redis_port",
            ]
            for field in required_fields:
                assert (
                    field in config
                ), f"{tier_name} rate limiting should have '{field}' configured"

            # Verify time window limits are positive
            for window in ["minute", "hour", "day"]:
                limit = config.get(window, 0)
                assert (
                    limit > 0
                ), f"{tier_name} {window} limit should be positive, got {limit}"

            # Verify Redis configuration
            assert config["policy"] == "redis", f"{tier_name} should use Redis policy"
            assert isinstance(
                config["redis_port"], int
            ), f"{tier_name} Redis port should be integer"
            assert config["redis_port"] > 0, f"{tier_name} Redis port should be positive"

            # Verify operational settings
            assert "fault_tolerant" in config, f"{tier_name} should have fault_tolerant setting"
            assert (
                config["redis_port"] > 0
            ), f"{tier_name} Redis port should be positive"

            # Verify operational settings
            assert (
                "fault_tolerant" in config
            ), f"{tier_name} should have fault_tolerant setting"
            assert (
                "hide_client_headers" in config
            ), f"{tier_name} should have hide_client_headers setting"


@pytest.mark.unit
def test_task_10_4_verification_summary(kong_config):
    """
    Task 10.4 Summary: Verify premium tier has higher limits than free tier.

    This test provides a comprehensive verification of Task 10.4 requirements.
    """
    consumers = kong_config.get("consumers", [])

    # Extract configurations
    free_consumer = next((c for c in consumers if c.get("username") == "free-tier-consumer"), None)
    free_consumer = next(
        (c for c in consumers if c.get("username") == "free-tier-consumer"), None
    )
    premium_consumer = next(
        (c for c in consumers if c.get("username") == "premium-tier-consumer"), None
    )

    assert (
        free_consumer is not None and premium_consumer is not None
    ), "Both free and premium tier consumers must be configured"

    # Get rate limiting configs
    free_rate = next(p["config"] for p in free_consumer["plugins"] if p["name"] == "rate-limiting")
    free_rate = next(
        p["config"] for p in free_consumer["plugins"] if p["name"] == "rate-limiting"
    )
    premium_rate = next(
        p["config"] for p in premium_consumer["plugins"] if p["name"] == "rate-limiting"
    )

    # Task 10.4 verification: Premium has higher limits
    verification_results = {
        "minute_limits": (free_rate["minute"], premium_rate["minute"]),
        "hour_limits": (free_rate["hour"], premium_rate["hour"]),
        "day_limits": (free_rate["day"], premium_rate["day"]),
        "minute_ratio": premium_rate["minute"] / free_rate["minute"],
        "hour_ratio": premium_rate["hour"] / free_rate["hour"],
        "day_ratio": premium_rate["day"] / free_rate["day"],
        "all_windows_higher": all(
            [
                premium_rate["minute"] > free_rate["minute"],
                premium_rate["hour"] > free_rate["hour"],
                premium_rate["day"] > free_rate["day"],
            ]
        ),
    }

    # Assertions for Task 10.4
    assert verification_results[
        "all_windows_higher"
    ], "Premium tier must have higher limits than free tier in ALL time windows"

    assert (
        verification_results["minute_ratio"] >= 10
    ), f"Premium should provide at least 10x improvement per minute, got {verification_results['minute_ratio']}x"

    assert (
        verification_results["hour_ratio"] >= 10
    ), f"Premium should provide at least 10x improvement per hour, got {verification_results['hour_ratio']}x"

    assert (
        verification_results["day_ratio"] >= 10
    ), f"Premium should provide at least 10x improvement per day, got {verification_results['day_ratio']}x"

    # Print verification summary for Task 10.4
    print("\n=== Task 10.4 Verification Summary ===")
    print(
        f"Free tier limits: {free_rate['minute']}/min, {free_rate['hour']}/hour, {free_rate['day']}/day"
    )
    print(
        f"Premium tier limits: {premium_rate['minute']}/min, {premium_rate['hour']}/hour, {premium_rate['day']}/day"
    )
    print(
        f"Premium improvement ratios: {verification_results['minute_ratio']}x minute, {verification_results['hour_ratio']}x hour, {verification_results['day_ratio']}x day"
    )
    print("✅ Task 10.4: Premium tier has higher limits than free tier - VERIFIED")

    return verification_results
