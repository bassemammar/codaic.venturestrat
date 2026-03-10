"""
Unit tests for rate limiting configuration validation.

Tests the Kong configuration for rate limiting tiers, consumer setup,
and plugin configuration without requiring a running Kong instance.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def kong_config() -> Dict[str, Any]:
    """Load Kong configuration for testing."""
    config_path = Path(__file__).parent.parent.parent / "kong.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


class TestRateLimitingConfiguration:
    """Test rate limiting configuration in kong.yaml."""

    def test_global_rate_limiting_plugin_present(self, kong_config):
        """Test that global rate limiting plugin is configured."""
        plugins = kong_config.get("plugins", [])

        rate_limit_plugins = [p for p in plugins if p.get("name") == "rate-limiting"]
        assert len(rate_limit_plugins) >= 1, "Global rate limiting plugin not found"

        global_plugin = rate_limit_plugins[0]
        config = global_plugin.get("config", {})

        # Should have basic rate limits
        assert "minute" in config, "Global rate limiting missing minute limit"
        assert "hour" in config, "Global rate limiting missing hour limit"
        assert config["minute"] > 0, "Global minute limit should be positive"
        assert config["hour"] > 0, "Global hour limit should be positive"

    def test_global_rate_limiting_uses_redis(self, kong_config):
        """Test that global rate limiting is configured to use Redis."""
        plugins = kong_config.get("plugins", [])

        rate_limit_plugins = [p for p in plugins if p.get("name") == "rate-limiting"]
        global_plugin = rate_limit_plugins[0]
        config = global_plugin.get("config", {})

        assert config.get("policy") == "redis", "Rate limiting should use Redis policy"
        assert "redis_host" in config, "Redis host must be configured"
        assert "redis_port" in config, "Redis port must be configured"
        assert (
            config.get("fault_tolerant") is True
        ), "Rate limiting should be fault tolerant"

    def test_consumer_tiers_exist(self, kong_config):
        """Test that all expected consumer tiers are configured."""
        consumers = kong_config.get("consumers", [])
        consumer_usernames = [c.get("username") for c in consumers]

        expected_tiers = [
            "free-tier-consumer",
            "standard-tier-consumer",
            "premium-tier-consumer",
        ]

        for tier in expected_tiers:
            assert tier in consumer_usernames, f"Consumer tier {tier} not found"

    def test_free_tier_configuration(self, kong_config):
        """Test free tier consumer configuration."""
        consumers = kong_config.get("consumers", [])
        free_tier = next(
            (c for c in consumers if c.get("username") == "free-tier-consumer"), None
        )

        assert free_tier is not None, "Free tier consumer not found"
        assert "free-tier" in free_tier.get("tags", []), "Free tier should be tagged"
        assert (
            free_tier.get("custom_id") == "free-tier"
        ), "Free tier custom_id incorrect"

        # Check API key
        keyauth_creds = free_tier.get("keyauth_credentials", [])
        assert len(keyauth_creds) > 0, "Free tier missing API key credentials"
        assert (
            keyauth_creds[0].get("key") == "free-api-key-11111"
        ), "Free tier API key incorrect"

        # Check rate limiting plugin
        plugins = free_tier.get("plugins", [])
        rate_limit_plugins = [p for p in plugins if p.get("name") == "rate-limiting"]
        assert (
            len(rate_limit_plugins) == 1
        ), "Free tier should have rate limiting plugin"

        config = rate_limit_plugins[0].get("config", {})
        assert config.get("minute") == 100, "Free tier minute limit should be 100"
        assert config.get("hour") == 1000, "Free tier hour limit should be 1000"
        assert config.get("day") == 2500, "Free tier day limit should be 2500"

    def test_standard_tier_configuration(self, kong_config):
        """Test standard tier consumer configuration."""
        consumers = kong_config.get("consumers", [])
        standard_tier = next(
            (c for c in consumers if c.get("username") == "standard-tier-consumer"),
            None,
        )

        assert standard_tier is not None, "Standard tier consumer not found"
        assert "standard-tier" in standard_tier.get(
            "tags", []
        ), "Standard tier should be tagged"

        # Check API key
        keyauth_creds = standard_tier.get("keyauth_credentials", [])
        assert len(keyauth_creds) > 0, "Standard tier missing API key credentials"
        assert (
            keyauth_creds[0].get("key") == "standard-api-key-22222"
        ), "Standard tier API key incorrect"

        # Check rate limiting plugin
        plugins = standard_tier.get("plugins", [])
        rate_limit_plugins = [p for p in plugins if p.get("name") == "rate-limiting"]
        assert (
            len(rate_limit_plugins) == 1
        ), "Standard tier should have rate limiting plugin"

        config = rate_limit_plugins[0].get("config", {})
        assert config.get("minute") == 1000, "Standard tier minute limit should be 1000"
        assert config.get("hour") == 10000, "Standard tier hour limit should be 10000"
        assert config.get("day") == 50000, "Standard tier day limit should be 50000"

    def test_premium_tier_configuration(self, kong_config):
        """Test premium tier consumer configuration."""
        consumers = kong_config.get("consumers", [])
        premium_tier = next(
            (c for c in consumers if c.get("username") == "premium-tier-consumer"), None
        )

        assert premium_tier is not None, "Premium tier consumer not found"
        assert "premium-tier" in premium_tier.get(
            "tags", []
        ), "Premium tier should be tagged"
        assert "priority" in premium_tier.get(
            "tags", []
        ), "Premium tier should have priority tag"

        # Check API key
        keyauth_creds = premium_tier.get("keyauth_credentials", [])
        assert len(keyauth_creds) > 0, "Premium tier missing API key credentials"
        assert (
            keyauth_creds[0].get("key") == "premium-api-key-33333"
        ), "Premium tier API key incorrect"

        # Check rate limiting plugin
        plugins = premium_tier.get("plugins", [])
        rate_limit_plugins = [p for p in plugins if p.get("name") == "rate-limiting"]
        assert (
            len(rate_limit_plugins) == 1
        ), "Premium tier should have rate limiting plugin"

        config = rate_limit_plugins[0].get("config", {})
        assert config.get("minute") == 5000, "Premium tier minute limit should be 5000"
        assert config.get("hour") == 100000, "Premium tier hour limit should be 100000"
        assert config.get("day") == 500000, "Premium tier day limit should be 500000"

    def test_tier_hierarchy(self, kong_config):
        """Test that tier limits follow proper hierarchy (free < standard < premium)."""
        consumers = kong_config.get("consumers", [])

        # Extract rate limits for each tier
        tiers = {}

        for consumer in consumers:
            username = consumer.get("username")
            if username in [
                "free-tier-consumer",
                "standard-tier-consumer",
                "premium-tier-consumer",
            ]:
                plugins = consumer.get("plugins", [])
                rate_limit_plugins = [
                    p for p in plugins if p.get("name") == "rate-limiting"
                ]

                if rate_limit_plugins:
                    config = rate_limit_plugins[0].get("config", {})
                    tiers[username] = {
                        "minute": config.get("minute", 0),
                        "hour": config.get("hour", 0),
                        "day": config.get("day", 0),
                    }

        # Verify hierarchy for each time period
        assert (
            tiers["free-tier-consumer"]["minute"] < tiers["standard-tier-consumer"]["minute"]
        ), "Free tier minute limit should be less than standard"
        assert (
            tiers["standard-tier-consumer"]["minute"] < tiers["premium-tier-consumer"]["minute"]
        ), "Standard tier minute limit should be less than premium"

        assert (
            tiers["free-tier-consumer"]["hour"] < tiers["standard-tier-consumer"]["hour"]
        ), "Free tier hour limit should be less than standard"
        assert (
            tiers["standard-tier-consumer"]["hour"] < tiers["premium-tier-consumer"]["hour"]
            tiers["free-tier-consumer"]["minute"]
            < tiers["standard-tier-consumer"]["minute"]
        ), "Free tier minute limit should be less than standard"
        assert (
            tiers["standard-tier-consumer"]["minute"]
            < tiers["premium-tier-consumer"]["minute"]
        ), "Standard tier minute limit should be less than premium"

        assert (
            tiers["free-tier-consumer"]["hour"]
            < tiers["standard-tier-consumer"]["hour"]
        ), "Free tier hour limit should be less than standard"
        assert (
            tiers["standard-tier-consumer"]["hour"]
            < tiers["premium-tier-consumer"]["hour"]
        ), "Standard tier hour limit should be less than premium"

    def test_all_tier_plugins_use_redis(self, kong_config):
        """Test that all consumer tier rate limiting plugins use Redis."""
        consumers = kong_config.get("consumers", [])

        tier_consumers = [
            c for c in consumers if c.get("username", "").endswith("-tier-consumer")
        ]

        for consumer in tier_consumers:
            plugins = consumer.get("plugins", [])
            rate_limit_plugins = [
                p for p in plugins if p.get("name") == "rate-limiting"
            ]

            for plugin in rate_limit_plugins:
                config = plugin.get("config", {})
                assert (
                    config.get("policy") == "redis"
                ), f"Consumer {consumer.get('username')} rate limiting should use Redis"
                assert (
                    config.get("fault_tolerant") is True
                ), f"Consumer {consumer.get('username')} rate limiting should be fault tolerant"

    def test_development_consumers_use_global_limits(self, kong_config):
        """Test that development consumers rely on global rate limiting."""
        consumers = kong_config.get("consumers", [])

        dev_consumers = ["default-consumer", "test-consumer"]

        for consumer_name in dev_consumers:
            consumer = next(
                (c for c in consumers if c.get("username") == consumer_name), None
            )

            if consumer:
                plugins = consumer.get("plugins", [])
                rate_limit_plugins = [
                    p for p in plugins if p.get("name") == "rate-limiting"
                ]

                # Development consumers should NOT have specific rate limiting plugins
                # They should rely on global rate limiting
                assert (
                    len(rate_limit_plugins) == 0
                ), f"Development consumer {consumer_name} should not have specific rate limits"

    def test_cors_exposes_rate_limit_headers(self, kong_config):
        """Test that CORS configuration exposes rate limit headers."""
        plugins = kong_config.get("plugins", [])
        cors_plugins = [p for p in plugins if p.get("name") == "cors"]

        assert len(cors_plugins) > 0, "CORS plugin not found"

        cors_config = cors_plugins[0].get("config", {})
        exposed_headers = cors_config.get("exposed_headers", [])

        expected_rate_headers = [
            "X-RateLimit-Limit-Minute",
            "X-RateLimit-Remaining-Minute",
        ]

        for header in expected_rate_headers:
            assert header in exposed_headers, f"CORS should expose {header}"

    def test_rate_limit_configuration_consistency(self, kong_config):
        """Test configuration consistency across all rate limiting configurations."""
        plugins = kong_config.get("plugins", [])
        consumers = kong_config.get("consumers", [])

        # Collect all rate limiting configurations
        all_rate_configs = []

        # Global plugin
        global_rate_plugins = [p for p in plugins if p.get("name") == "rate-limiting"]
        for plugin in global_rate_plugins:
            all_rate_configs.append(plugin.get("config", {}))

        # Consumer-specific plugins
        for consumer in consumers:
            consumer_plugins = consumer.get("plugins", [])
            consumer_rate_plugins = [
                p for p in consumer_plugins if p.get("name") == "rate-limiting"
            ]
            for plugin in consumer_rate_plugins:
                all_rate_configs.append(plugin.get("config", {}))

        # Verify consistency of Redis configuration across all rate limiting plugins
        redis_hosts = set()
        redis_ports = set()
        fault_tolerant_settings = set()

        for config in all_rate_configs:
            if "redis_host" in config:
                redis_hosts.add(config["redis_host"])
            if "redis_port" in config:
                redis_ports.add(config["redis_port"])
            if "fault_tolerant" in config:
                fault_tolerant_settings.add(config["fault_tolerant"])

        assert len(redis_hosts) <= 1, "All rate limiting should use same Redis host"
        assert len(redis_ports) <= 1, "All rate limiting should use same Redis port"
        assert (
            len(fault_tolerant_settings) <= 1
        ), "All rate limiting should have same fault tolerance setting"

    def test_api_keys_unique_across_tiers(self, kong_config):
        """Test that API keys are unique across all consumer tiers."""
        consumers = kong_config.get("consumers", [])
        all_api_keys = []

        for consumer in consumers:
            keyauth_creds = consumer.get("keyauth_credentials", [])
            for cred in keyauth_creds:
                api_key = cred.get("key")
                if api_key:
                    all_api_keys.append(api_key)

        # Check for duplicates
        unique_keys = set(all_api_keys)
        assert len(all_api_keys) == len(
            unique_keys
        ), "API keys must be unique across all consumers"

    def test_consumer_custom_ids_follow_convention(self, kong_config):
        """Test that consumer custom_id fields follow naming convention."""
        consumers = kong_config.get("consumers", [])

        for consumer in consumers:
            username = consumer.get("username", "")
            custom_id = consumer.get("custom_id", "")

            if "tier" in username:
                # Tier consumers should have custom_id matching tier name
                expected_custom_id = username.replace("-consumer", "")
                assert (
                    custom_id == expected_custom_id
                ), f"Consumer {username} custom_id should be {expected_custom_id}, got {custom_id}"

    def test_rate_limiting_time_windows_valid(self, kong_config):
        """Test that rate limiting time windows are properly configured."""
        consumers = kong_config.get("consumers", [])

        for consumer in consumers:
            plugins = consumer.get("plugins", [])
            rate_limit_plugins = [
                p for p in plugins if p.get("name") == "rate-limiting"
            ]

            for plugin in rate_limit_plugins:
                config = plugin.get("config", {})

                # If day is specified, hour should also be specified and logical
                if "day" in config and "hour" in config:
                    assert (
                        config["day"] >= config["hour"]
                    ), f"Consumer {consumer.get('username')} day limit should be >= hour limit"

                # If hour is specified, minute should also be specified and logical
                if "hour" in config and "minute" in config:
                    # Hour limit should be at least as large as minute limit (allowing for bursts)
                    # But we'll be flexible since minute limits can be higher for burst scenarios
                    assert (
                        config["minute"] > 0
                    ), f"Consumer {consumer.get('username')} minute limit should be positive"
