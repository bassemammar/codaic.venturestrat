"""
Unit tests for per-consumer rate limit configuration validation.

Task 10.1: Write tests for per-consumer limits

These unit tests validate the Kong configuration for per-consumer rate limiting
without requiring a running Kong instance. They test the declarative configuration
structure and ensure proper setup of consumer-specific rate limits.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def gateway_config() -> Dict[str, Any]:
    """Load Kong configuration for testing."""
    config_path = Path(__file__).parent.parent.parent / "kong.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@pytest.mark.unit
class TestPerConsumerRateLimitConfig:
    """Test per-consumer rate limit configuration structure."""

    def test_consumer_tier_structure(self, gateway_config):
        """Test that all required consumer tiers are configured.

        Task 10.1: Verify consumer tier configuration structure.
        """
        consumers = gateway_config.get("consumers", [])
        assert isinstance(consumers, list), "Consumers should be a list"
        assert len(consumers) > 0, "Should have consumers configured"

        # Find tier consumers
        tier_consumers = {}
        for consumer in consumers:
            username = consumer.get("username", "")
            if "tier" in username:
                tier_consumers[username] = consumer

        # Verify all required tiers exist
        expected_tiers = [
            "free-tier-consumer",
            "standard-tier-consumer",
            "premium-tier-consumer",
        ]
        for tier in expected_tiers:
            assert tier in tier_consumers, f"Consumer {tier} should be configured"
            assert isinstance(
                tier_consumers[tier], dict
            ), f"Consumer {tier} should be a dict"

    def test_consumer_api_key_configuration(self, gateway_config):
        """Test that tier consumers have proper API key configuration.

        Task 10.1: Each tier should have unique API keys configured.
        """
        consumers = gateway_config.get("consumers", [])
        tier_consumers = [c for c in consumers if "tier" in c.get("username", "")]

        expected_configs = {
            "free-tier-consumer": "free-api-key-11111",
            "standard-tier-consumer": "standard-api-key-22222",
            "premium-tier-consumer": "premium-api-key-33333",
        }

        for consumer in tier_consumers:
            username = consumer["username"]
            if username in expected_configs:
                # Should have keyauth_credentials
                assert (
                    "keyauth_credentials" in consumer
                ), f"{username} should have API key credentials"

                credentials = consumer["keyauth_credentials"]
                assert isinstance(
                    credentials, list
                ), f"{username} credentials should be a list"
                assert (
                    len(credentials) > 0
                ), f"{username} should have at least one API key"

                # Check for expected API key
                api_keys = [cred["key"] for cred in credentials]
                expected_key = expected_configs[username]
                assert (
                    expected_key in api_keys
                ), f"{username} should have API key {expected_key}"

    def test_consumer_rate_limit_plugin_configuration(self, gateway_config):
        """Test that tier consumers have proper rate limiting plugin configuration.

        Task 10.1: Each tier should have consumer-specific rate limiting configured.
        """
        consumers = gateway_config.get("consumers", [])
        tier_consumers = {
            c["username"]: c for c in consumers if "tier" in c.get("username", "")
        }

        expected_tiers = [
            "free-tier-consumer",
            "standard-tier-consumer",
            "premium-tier-consumer",
        ]

        for tier_name in expected_tiers:
            assert tier_name in tier_consumers, f"Consumer {tier_name} should exist"

            consumer = tier_consumers[tier_name]
            assert "plugins" in consumer, f"{tier_name} should have plugins configured"

            plugins = consumer["plugins"]
            assert isinstance(plugins, list), f"{tier_name} plugins should be a list"

            # Find rate limiting plugin
            rate_limit_plugins = [p for p in plugins if p.get("name") == "rate-limiting"]
            rate_limit_plugins = [
                p for p in plugins if p.get("name") == "rate-limiting"
            ]
            assert (
                len(rate_limit_plugins) == 1
            ), f"{tier_name} should have exactly one rate-limiting plugin"

            rate_plugin = rate_limit_plugins[0]
            assert (
                "config" in rate_plugin
            ), f"{tier_name} rate limiting plugin should have config"

    def test_rate_limit_config_structure(self, gateway_config):
        """Test the structure of rate limiting configuration for each tier.

        Task 10.1: Rate limiting config should have proper structure.
        """
        consumers = gateway_config.get("consumers", [])
        tier_consumers = {
            c["username"]: c for c in consumers if "tier" in c.get("username", "")
        }

        for tier_name, consumer in tier_consumers.items():
            plugins = consumer.get("plugins", [])
            rate_plugin = next(
                (p for p in plugins if p["name"] == "rate-limiting"), None
            )

            assert (
                rate_plugin is not None
            ), f"{tier_name} should have rate limiting plugin"

            config = rate_plugin["config"]

            # Required fields
            assert (
                "minute" in config
            ), f"{tier_name} should have minute limit configured"
            assert "policy" in config, f"{tier_name} should have policy configured"
            assert config["policy"] == "redis", f"{tier_name} should use Redis policy"

            # Redis configuration
            assert (
                "redis_host" in config
            ), f"{tier_name} should have Redis host configured"
            assert (
                "redis_port" in config
            ), f"{tier_name} should have Redis port configured"
            assert (
                config["redis_port"] == 6379
            ), f"{tier_name} should use standard Redis port"

            # Fault tolerance
            assert (
                "fault_tolerant" in config
            ), f"{tier_name} should have fault tolerance configured"
            assert (
                config["fault_tolerant"] is True
            ), f"{tier_name} should enable fault tolerance"

    def test_rate_limit_tier_hierarchy(self, gateway_config):
        """Test that rate limiting tiers have proper hierarchy.

        Task 10.1: Rate limits should follow free < standard < premium hierarchy.
        """
        consumers = gateway_config.get("consumers", [])

        # Extract rate limits for each tier
        tier_limits = {}
        for consumer in consumers:
            username = consumer.get("username", "")
            if "tier" in username:
                plugins = consumer.get("plugins", [])
                rate_plugin = next(
                    (p for p in plugins if p["name"] == "rate-limiting"), None
                )
                if rate_plugin:
                    tier_limits[username] = rate_plugin["config"]["minute"]

        # Verify all tiers have limits
        assert "free-tier-consumer" in tier_limits, "Free tier should have rate limit"
        assert (
            "standard-tier-consumer" in tier_limits
        ), "Standard tier should have rate limit"
        assert (
            "premium-tier-consumer" in tier_limits
        ), "Premium tier should have rate limit"

        # Verify hierarchy
        free_limit = tier_limits["free-tier-consumer"]
        standard_limit = tier_limits["standard-tier-consumer"]
        premium_limit = tier_limits["premium-tier-consumer"]

        assert (
            free_limit < standard_limit
        ), f"Free tier ({free_limit}) should be less than standard ({standard_limit})"
        assert (
            standard_limit < premium_limit
        ), f"Standard tier ({standard_limit}) should be less than premium ({premium_limit})"

    def test_specific_rate_limit_values(self, gateway_config):
        """Test that rate limits match expected values from design specification.

        Task 10.1: Rate limits should match design specification.
        """
        consumers = gateway_config.get("consumers", [])

        expected_limits = {
            "free-tier-consumer": {"minute": 100, "hour": 1000, "day": 2500},
            "standard-tier-consumer": {"minute": 1000, "hour": 10000, "day": 50000},
            "premium-tier-consumer": {"minute": 5000, "hour": 100000, "day": 500000},
        }

        for consumer in consumers:
            username = consumer.get("username", "")
            if username in expected_limits:
                plugins = consumer.get("plugins", [])
                rate_plugin = next(
                    (p for p in plugins if p["name"] == "rate-limiting"), None
                )

                assert (
                    rate_plugin is not None
                ), f"{username} should have rate limiting plugin"

                config = rate_plugin["config"]
                expected = expected_limits[username]

                # Check minute limit (always required)
                assert (
                    config["minute"] == expected["minute"]
                ), f"{username} should have {expected['minute']}/min, got {config['minute']}"

                # Check hour limit if configured
                if "hour" in config:
                    assert (
                        config["hour"] == expected["hour"]
                    ), f"{username} should have {expected['hour']}/hour, got {config['hour']}"

                # Check day limit if configured
                if "day" in config:
                    assert (
                        config["day"] == expected["day"]
                    ), f"{username} should have {expected['day']}/day, got {config['day']}"

    def test_global_rate_limit_fallback(self, gateway_config):
        """Test that global rate limiting is configured as fallback.

        Task 10.1: Global rate limiting should provide fallback for consumers without specific limits.
        """
        plugins = gateway_config.get("plugins", [])

        # Find global rate limiting plugin
        global_rate_plugins = [p for p in plugins if p.get("name") == "rate-limiting"]
        assert len(global_rate_plugins) >= 1, "Should have global rate limiting plugin"

        global_rate_plugin = global_rate_plugins[
            0
        ]  # Take first one (main global plugin)
        assert "config" in global_rate_plugin, "Global rate limiting should have config"

        config = global_rate_plugin["config"]

        # Should have minute and hour limits
        assert "minute" in config, "Global rate limiting should have minute limit"
        assert "hour" in config, "Global rate limiting should have hour limit"

        # Should use Redis policy
        assert config["policy"] == "redis", "Global rate limiting should use Redis"

        # Should have Redis configuration
        assert "redis_host" in config, "Global rate limiting should have Redis host"
        assert "redis_port" in config, "Global rate limiting should have Redis port"

    def test_consumer_tags_for_organization(self, gateway_config):
        """Test that tier consumers have appropriate tags for organization.

        Task 10.1: Consumers should be properly tagged for management.
        """
        consumers = gateway_config.get("consumers", [])
        tier_consumers = [c for c in consumers if "tier" in c.get("username", "")]

        for consumer in tier_consumers:
            username = consumer["username"]

            # Should have tags
            assert "tags" in consumer, f"{username} should have tags for organization"
            tags = consumer["tags"]
            assert isinstance(tags, list), f"{username} tags should be a list"
            assert len(tags) > 0, f"{username} should have at least one tag"

            # Tags should indicate tier type
            tier_tag_found = False
            for tag in tags:
                if "tier" in tag:
                    tier_tag_found = True
                    break
            assert tier_tag_found, f"{username} should have a tier-related tag"

    def test_consumer_custom_ids(self, gateway_config):
        """Test that tier consumers have proper custom IDs.

        Task 10.1: Consumers should have meaningful custom IDs.
        """
        consumers = gateway_config.get("consumers", [])
        tier_consumers = [c for c in consumers if "tier" in c.get("username", "")]

        for consumer in tier_consumers:
            username = consumer["username"]

            # Should have custom_id
            assert "custom_id" in consumer, f"{username} should have custom_id"
            custom_id = consumer["custom_id"]
            assert isinstance(
                custom_id, str
            ), f"{username} custom_id should be a string"
            assert len(custom_id) > 0, f"{username} custom_id should not be empty"

    def test_rate_limit_redis_consistency(self, gateway_config):
        """Test that all rate limiting configurations use same Redis settings.

        Task 10.1: All rate limiting should use consistent Redis configuration.
        """
        consumers = gateway_config.get("consumers", [])
        plugins = gateway_config.get("plugins", [])

        # Collect all rate limiting configurations
        rate_configs = []

        # Global rate limiting
        global_rate_plugins = [p for p in plugins if p.get("name") == "rate-limiting"]
        for plugin in global_rate_plugins:
            rate_configs.append(plugin["config"])

        # Consumer-specific rate limiting
        for consumer in consumers:
            if "plugins" in consumer:
                consumer_rate_plugins = [
                    p for p in consumer["plugins"] if p.get("name") == "rate-limiting"
                ]
                for plugin in consumer_rate_plugins:
                    rate_configs.append(plugin["config"])

        # All should use same Redis settings
        assert len(rate_configs) > 0, "Should have rate limiting configurations"

        redis_hosts = set()
        redis_ports = set()
        policies = set()

        for config in rate_configs:
            if "redis_host" in config:
                redis_hosts.add(config["redis_host"])
            if "redis_port" in config:
                redis_ports.add(config["redis_port"])
            if "policy" in config:
                policies.add(config["policy"])

        # Should all use same Redis instance
        assert (
            len(redis_ports) <= 1
        ), f"All rate limiting should use same Redis port, got: {redis_ports}"
        assert len(policies) == 1, f"All rate limiting should use same policy, got: {policies}"
        assert (
            len(policies) == 1
        ), f"All rate limiting should use same policy, got: {policies}"
        assert "redis" in policies, "All rate limiting should use Redis policy"

        if redis_ports:
            assert 6379 in redis_ports, "Redis should use standard port 6379"


@pytest.mark.unit
class TestConsumerRateLimitValidation:
    """Test validation of consumer rate limit configuration."""

    def test_no_duplicate_api_keys(self, gateway_config):
        """Test that API keys are unique across all consumers.

        Task 10.1: API keys should be unique to prevent conflicts.
        """
        consumers = gateway_config.get("consumers", [])
        all_api_keys = []

        for consumer in consumers:
            if "keyauth_credentials" in consumer:
                for cred in consumer["keyauth_credentials"]:
                    if "key" in cred:
                        all_api_keys.append(cred["key"])

        # Check for duplicates
        unique_keys = set(all_api_keys)
        assert (
            len(all_api_keys) == len(unique_keys)
        ), f"API keys should be unique. Duplicates found: {set([k for k in all_api_keys if all_api_keys.count(k) > 1])}"

    def test_no_duplicate_consumer_usernames(self, gateway_config):
        """Test that consumer usernames are unique.

        Task 10.1: Consumer usernames should be unique.
        """
        consumers = gateway_config.get("consumers", [])
        usernames = [c.get("username") for c in consumers if "username" in c]

        unique_usernames = set(usernames)
        assert (
            len(usernames) == len(unique_usernames)
        ), f"Usernames should be unique. Duplicates: {set([u for u in usernames if usernames.count(u) > 1])}"

    def test_rate_limit_values_are_positive(self, gateway_config):
        """Test that all rate limit values are positive integers.

        Task 10.1: Rate limits should be positive integers.
        """
        consumers = gateway_config.get("consumers", [])

        for consumer in consumers:
            username = consumer.get("username", "")
            if "plugins" in consumer:
                for plugin in consumer["plugins"]:
                    if plugin.get("name") == "rate-limiting":
                        config = plugin["config"]

                        for period in ["minute", "hour", "day"]:
                            if period in config:
                                value = config[period]
                                assert isinstance(
                                    value, int
                                ), f"{username} {period} limit should be integer, got {type(value)}"
                                assert (
                                    value > 0
                                ), f"{username} {period} limit should be positive, got {value}"

    def test_required_rate_limit_fields(self, gateway_config):
        """Test that required rate limiting fields are present.

        Task 10.1: Rate limiting config should have required fields.
        """
        consumers = gateway_config.get("consumers", [])
        tier_consumers = [c for c in consumers if "tier" in c.get("username", "")]

        required_fields = [
            "minute",
            "policy",
            "redis_host",
            "redis_port",
            "fault_tolerant",
        ]

        for consumer in tier_consumers:
            username = consumer["username"]
            plugins = consumer.get("plugins", [])
            rate_plugin = next(
                (p for p in plugins if p["name"] == "rate-limiting"), None
            )

            assert (
                rate_plugin is not None
            ), f"{username} should have rate limiting plugin"

            config = rate_plugin["config"]

            for field in required_fields:
                assert (
                    field in config
                ), f"{username} rate limiting should have {field} configured"

    def test_fault_tolerant_enabled(self, gateway_config):
        """Test that fault tolerance is enabled for all rate limiting.

        Task 10.1: Rate limiting should be fault tolerant.
        """
        consumers = gateway_config.get("consumers", [])
        plugins = gateway_config.get("plugins", [])

        # Check global rate limiting
        global_rate_plugins = [p for p in plugins if p.get("name") == "rate-limiting"]
        for plugin in global_rate_plugins:
            config = plugin["config"]
            assert (
                config.get("fault_tolerant") is True
            ), "Global rate limiting should be fault tolerant"

        # Check consumer rate limiting
        for consumer in consumers:
            if "plugins" in consumer:
                for plugin in consumer["plugins"]:
                    if plugin.get("name") == "rate-limiting":
                        config = plugin["config"]
                        username = consumer.get("username", "unknown")
                        assert (
                            config.get("fault_tolerant") is True
                        ), f"{username} rate limiting should be fault tolerant"
