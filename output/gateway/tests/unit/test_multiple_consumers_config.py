"""
Unit tests for multiple consumers configuration.

Tests that the Kong configuration properly defines multiple consumers with
different tiers, API keys, and rate limiting configurations.
This verifies task 6.1: Write tests for multiple consumers.
"""

import pytest
from typing import Dict, Any


@pytest.mark.unit
class TestMultipleConsumersConfiguration:
    """Test multiple consumer configuration in Kong YAML."""

    def test_all_expected_consumers_are_defined(self, gateway_config: Dict[str, Any]):
        """Test that all expected consumers are properly defined."""
        consumers = gateway_config.get("consumers", [])

        # Extract consumer usernames
        consumer_names = [consumer.get("username") for consumer in consumers]

        expected_consumers = [
            "default-consumer",
            "test-consumer",
            "free-tier-consumer",
            "standard-tier-consumer",
            "premium-tier-consumer",
        ]

        for expected_consumer in expected_consumers:
            assert (
                expected_consumer in consumer_names
            ), f"Consumer '{expected_consumer}' not found in configuration"

    def test_consumers_have_unique_api_keys(self, gateway_config: Dict[str, Any]):
        """Test that each consumer has unique API keys."""
        consumers = gateway_config.get("consumers", [])

        all_api_keys = []
        for consumer in consumers:
            keyauth_creds = consumer.get("keyauth_credentials", [])
            for cred in keyauth_creds:
                api_key = cred.get("key")
                if api_key:
                    all_api_keys.append(api_key)

        # Check that we have the expected number of unique keys
        assert (
            len(all_api_keys) >= 5
        ), f"Expected at least 5 API keys, found {len(all_api_keys)}"
        assert len(set(all_api_keys)) == len(all_api_keys), "Duplicate API keys found"

    def test_consumer_api_key_assignments(self, gateway_config: Dict[str, Any]):
        """Test that consumers have their expected API keys assigned."""
        consumers = gateway_config.get("consumers", [])

        expected_mappings = {
            "default-consumer": "dev-api-key-12345",
            "test-consumer": "test-api-key-67890",
            "free-tier-consumer": "free-api-key-11111",
            "standard-tier-consumer": "standard-api-key-22222",
            "premium-tier-consumer": "premium-api-key-33333",
        }

        for consumer in consumers:
            username = consumer.get("username")
            if username in expected_mappings:
                keyauth_creds = consumer.get("keyauth_credentials", [])
                assert (
                    len(keyauth_creds) >= 1
                ), f"Consumer '{username}' has no keyauth credentials"

                api_key = keyauth_creds[0].get("key")
                expected_key = expected_mappings[username]
                assert (
                    api_key == expected_key
                ), f"Consumer '{username}' expected key '{expected_key}', got '{api_key}'"

    def test_consumer_tier_tagging(self, gateway_config: Dict[str, Any]):
        """Test that consumers are properly tagged by tier."""
        consumers = gateway_config.get("consumers", [])

        expected_tier_mappings = {
            "default-consumer": ["dev", "default"],
            "test-consumer": ["test", "integration"],
            "free-tier-consumer": ["free-tier", "external"],
            "standard-tier-consumer": ["standard-tier", "external"],
            "premium-tier-consumer": ["premium-tier", "external", "priority"],
        }

        for consumer in consumers:
            username = consumer.get("username")
            if username in expected_tier_mappings:
                consumer_tags = consumer.get("tags", [])
                expected_tags = expected_tier_mappings[username]

                for expected_tag in expected_tags:
                    assert (
                        expected_tag in consumer_tags
                    ), f"Consumer '{username}' missing expected tag '{expected_tag}'. Tags: {consumer_tags}"

    def test_consumer_custom_ids(self, gateway_config: Dict[str, Any]):
        """Test that consumers have proper custom IDs for identification."""
        consumers = gateway_config.get("consumers", [])

        expected_custom_ids = {
            "default-consumer": "default-dev-consumer",
            "test-consumer": "test-integration-consumer",
            "free-tier-consumer": "free-tier",
            "standard-tier-consumer": "standard-tier",
            "premium-tier-consumer": "premium-tier",
        }

        for consumer in consumers:
            username = consumer.get("username")
            if username in expected_custom_ids:
                custom_id = consumer.get("custom_id")
                expected_custom_id = expected_custom_ids[username]
                assert (
                    custom_id == expected_custom_id
                ), f"Consumer '{username}' expected custom_id '{expected_custom_id}', got '{custom_id}'"

    def test_tiered_consumer_rate_limiting(self, gateway_config: Dict[str, Any]):
        """Test that tiered consumers have appropriate rate limiting configuration."""
        consumers = gateway_config.get("consumers", [])

        # Find consumers with plugins (rate limiting)
        free_tier_consumer = next(
            (c for c in consumers if c.get("username") == "free-tier-consumer"), None
        )
        standard_tier_consumer = next(
            (c for c in consumers if c.get("username") == "standard-tier-consumer"),
            None,
        )
        premium_tier_consumer = next(
            (c for c in consumers if c.get("username") == "premium-tier-consumer"), None
        )

        assert free_tier_consumer, "Free tier consumer not found"
        assert standard_tier_consumer, "Standard tier consumer not found"
        assert premium_tier_consumer, "Premium tier consumer not found"

        # Check free tier rate limiting
        free_tier_plugins = free_tier_consumer.get("plugins", [])
        free_rate_limit = next(
            (p for p in free_tier_plugins if p.get("name") == "rate-limiting"), None
        )
        assert free_rate_limit, "Free tier consumer missing rate-limiting plugin"

        free_config = free_rate_limit.get("config", {})
        assert (
            free_config.get("minute") == 100
        ), f"Free tier should have 100/minute limit, got {free_config.get('minute')}"
        assert (
            free_config.get("hour") == 1000
        ), f"Free tier should have 1000/hour limit, got {free_config.get('hour')}"
        assert (
            free_config.get("day") == 2500
        ), f"Free tier should have 2500/day limit, got {free_config.get('day')}"

        # Check standard tier rate limiting
        standard_tier_plugins = standard_tier_consumer.get("plugins", [])
        standard_rate_limit = next(
            (p for p in standard_tier_plugins if p.get("name") == "rate-limiting"), None
        )
        assert (
            standard_rate_limit
        ), "Standard tier consumer missing rate-limiting plugin"

        standard_config = standard_rate_limit.get("config", {})
        assert (
            standard_config.get("minute") == 1000
        ), f"Standard tier should have 1000/minute limit, got {standard_config.get('minute')}"
        assert (
            standard_config.get("hour") == 10000
        ), f"Standard tier should have 10000/hour limit, got {standard_config.get('hour')}"
        assert (
            standard_config.get("day") == 50000
        ), f"Standard tier should have 50000/day limit, got {standard_config.get('day')}"

        # Check premium tier rate limiting
        premium_tier_plugins = premium_tier_consumer.get("plugins", [])
        premium_rate_limit = next(
            (p for p in premium_tier_plugins if p.get("name") == "rate-limiting"), None
        )
        assert premium_rate_limit, "Premium tier consumer missing rate-limiting plugin"

        premium_config = premium_rate_limit.get("config", {})
        assert (
            premium_config.get("minute") == 5000
        ), f"Premium tier should have 5000/minute limit, got {premium_config.get('minute')}"
        assert (
            premium_config.get("hour") == 100000
        ), f"Premium tier should have 100000/hour limit, got {premium_config.get('hour')}"
        assert (
            premium_config.get("day") == 500000
        ), f"Premium tier should have 500000/day limit, got {premium_config.get('day')}"

    def test_default_consumers_use_global_rate_limits(
        self, gateway_config: Dict[str, Any]
    ):
        """Test that default consumers rely on global rate limiting."""
        consumers = gateway_config.get("consumers", [])

        default_consumers = ["default-consumer", "test-consumer"]

        for consumer_name in default_consumers:
            consumer = next((c for c in consumers if c.get("username") == consumer_name), None)
            consumer = next(
                (c for c in consumers if c.get("username") == consumer_name), None
            )
            assert consumer, f"Consumer '{consumer_name}' not found"

            # These consumers should NOT have rate-limiting plugins (use global)
            consumer_plugins = consumer.get("plugins", [])
            rate_limit_plugins = [p for p in consumer_plugins if p.get("name") == "rate-limiting"]
            rate_limit_plugins = [
                p for p in consumer_plugins if p.get("name") == "rate-limiting"
            ]
            assert (
                len(rate_limit_plugins) == 0
            ), f"Consumer '{consumer_name}' should use global rate limits, but has rate-limiting plugin"

    def test_consumer_rate_limit_policy_consistency(
        self, gateway_config: Dict[str, Any]
    ):
        """Test that consumer-specific rate limits use consistent Redis policy."""
        consumers = gateway_config.get("consumers", [])

        for consumer in consumers:
            consumer_plugins = consumer.get("plugins", [])
            for plugin in consumer_plugins:
                if plugin.get("name") == "rate-limiting":
                    plugin_config = plugin.get("config", {})

                    # Should use Redis policy for consistency
                    assert (
                        plugin_config.get("policy") == "redis"
                    ), f"Consumer '{consumer.get('username')}' rate limiting should use Redis policy"

                    # Should use same Redis configuration as global
                    assert (
                        plugin_config.get("redis_host") == "redis"
                    ), f"Consumer '{consumer.get('username')}' should use 'redis' host"
                    assert (
                        plugin_config.get("redis_port") == 6379
                    ), f"Consumer '{consumer.get('username')}' should use port 6379"

    def test_api_key_format_consistency(self, gateway_config: Dict[str, Any]):
        """Test that all API keys follow consistent naming format."""
        consumers = gateway_config.get("consumers", [])

        api_key_patterns = {
            "dev": r"dev-api-key-\d{5}",
            "test": r"test-api-key-\d{5}",
            "free": r"free-api-key-\d{5}",
            "standard": r"standard-api-key-\d{5}",
        }

        import re

        for consumer in consumers:
            username = consumer.get("username")
            keyauth_creds = consumer.get("keyauth_credentials", [])

            for cred in keyauth_creds:
                api_key = cred.get("key")
                if api_key:
                    # Determine expected pattern based on key content
                    if "dev" in api_key:
                        pattern = api_key_patterns["dev"]
                    elif "test" in api_key:
                        pattern = api_key_patterns["test"]
                    elif "free" in api_key:
                        pattern = api_key_patterns["free"]
                    elif "standard" in api_key:
                        pattern = api_key_patterns["standard"]
                    elif "premium" in api_key:
                        pattern = api_key_patterns.get(
                            "premium", r"premium-api-key-\d{5}"
                        )
                    else:
                        continue

                    assert re.match(
                        pattern, api_key
                    ), f"Consumer '{username}' API key '{api_key}' doesn't match expected pattern '{pattern}'"

    def test_consumer_isolation_configuration(self, gateway_config: Dict[str, Any]):
        """Test that consumer configuration enables proper isolation."""
        consumers = gateway_config.get("consumers", [])

        assert (
            len(consumers) >= 5
        ), "Should have at least 5 consumers for multi-consumer testing"

        # Each consumer should have exactly one API key credential
        for consumer in consumers:
            username = consumer.get("username")
            keyauth_creds = consumer.get("keyauth_credentials", [])

            assert (
                len(keyauth_creds) == 1
            ), f"Consumer '{username}' should have exactly one API key credential, has {len(keyauth_creds)}"

            # API key should be non-empty and have proper tags
            api_key = keyauth_creds[0].get("key")
            assert (
                api_key and len(api_key) > 10
            ), f"Consumer '{username}' API key should be non-empty and sufficiently long"

            # Credential should have tags for identification
            cred_tags = keyauth_creds[0].get("tags", [])
            assert (
                len(cred_tags) > 0
            ), f"Consumer '{username}' API key credential should have tags for identification"

    def test_consumer_username_header_configuration(
        self, gateway_config: Dict[str, Any]
    ):
        """Test that Kong is configured to add consumer username to upstream headers."""
        plugins = gateway_config.get("plugins", [])

        # Find global request-transformer plugin
        global_request_transformer = None
        for plugin in plugins:
            if (
                plugin.get("name") == "request-transformer"
                and "service" not in plugin
                and "route" not in plugin
                and "consumer" not in plugin
            ):
                global_request_transformer = plugin
                break

        assert (
            global_request_transformer is not None
        ), "Global request-transformer plugin should be configured"

        config = global_request_transformer.get("config", {})
        add_headers = config.get("add", {}).get("headers", [])

        # Check that X-Consumer-Username header is configured
        username_header_found = False
        consumer_id_header_found = False

        for header in add_headers:
            if "X-Consumer-Username:" in header and "$(consumer.username)" in header:
                username_header_found = True
            if "X-Consumer-ID:" in header and "$(consumer.id)" in header:
                consumer_id_header_found = True

        assert username_header_found, "Global request-transformer should add X-Consumer-Username header with consumer.username variable"
        assert (
            consumer_id_header_found
        ), "Global request-transformer should add X-Consumer-ID header with consumer.id variable"
        assert consumer_id_header_found, "Global request-transformer should add X-Consumer-ID header with consumer.id variable"

    def test_external_vs_internal_consumer_classification(
        self, gateway_config: Dict[str, Any]
    ):
        """Test that consumers are properly classified as external vs internal."""
        consumers = gateway_config.get("consumers", [])

        external_consumers = [
            "free-tier-consumer",
            "standard-tier-consumer",
            "premium-tier-consumer",
        ]
        internal_consumers = ["default-consumer", "test-consumer"]

        for consumer in consumers:
            username = consumer.get("username")
            consumer_tags = consumer.get("tags", [])

            if username in external_consumers:
                assert (
                    "external" in consumer_tags
                ), f"External consumer '{username}' should have 'external' tag"
            elif username in internal_consumers:
                assert (
                    "external" not in consumer_tags
                ), f"Internal consumer '{username}' should not have 'external' tag"
                # Should have dev or test tags instead
                has_internal_tag = any(
                    tag in ["dev", "test", "default", "integration"] for tag in consumer_tags
                )
                assert (
                    has_internal_tag
                ), f"Internal consumer '{username}' should have dev/test/default/integration tags"
                    tag in ["dev", "test", "default", "integration"]
                    for tag in consumer_tags
                )
                assert has_internal_tag, f"Internal consumer '{username}' should have dev/test/default/integration tags"
