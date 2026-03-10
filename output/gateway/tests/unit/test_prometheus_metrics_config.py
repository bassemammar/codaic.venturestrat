"""
Unit tests for Prometheus metrics configuration validation.

Tests the Prometheus plugin configuration in kong.yaml.
"""

import pytest
from typing import Dict, Any


@pytest.mark.unit
class TestPrometheusMetricsConfiguration:
    """Test suite for Prometheus metrics plugin configuration."""

    def test_prometheus_plugin_present(self, gateway_config: Dict[str, Any]):
        """Test that Prometheus plugin is configured."""
        plugins = gateway_config.get("plugins", [])
        prometheus_plugin = next((p for p in plugins if p.get("name") == "prometheus"), None)
        prometheus_plugin = next(
            (p for p in plugins if p.get("name") == "prometheus"), None
        )

        assert prometheus_plugin is not None, "Prometheus plugin should be configured"

    def test_prometheus_plugin_config(self, gateway_config: Dict[str, Any]):
        """Test that Prometheus plugin has correct configuration."""
        plugins = gateway_config.get("plugins", [])
        prometheus_plugin = next((p for p in plugins if p.get("name") == "prometheus"), None)
        prometheus_plugin = next(
            (p for p in plugins if p.get("name") == "prometheus"), None
        )

        assert prometheus_plugin is not None, "Prometheus plugin should be configured"

        config = prometheus_plugin.get("config", {})

        # Test per-consumer metrics are enabled
        assert (
            config.get("per_consumer") is True
        ), "Per-consumer metrics should be enabled"

        # Test status code metrics are enabled
        assert (
            config.get("status_code_metrics") is True
        ), "Status code metrics should be enabled"

        # Test latency metrics are enabled
        assert (
            config.get("latency_metrics") is True
        ), "Latency metrics should be enabled"

    def test_prometheus_plugin_optional_configs(self, gateway_config: Dict[str, Any]):
        """Test optional Prometheus plugin configurations."""
        plugins = gateway_config.get("plugins", [])
        prometheus_plugin = next((p for p in plugins if p.get("name") == "prometheus"), None)
        prometheus_plugin = next(
            (p for p in plugins if p.get("name") == "prometheus"), None
        )

        assert prometheus_plugin is not None, "Prometheus plugin should be configured"

        config = prometheus_plugin.get("config", {})

        # Test bandwidth metrics (if configured)
        if "bandwidth_metrics" in config:
            assert isinstance(
                config["bandwidth_metrics"], bool
            ), "Bandwidth metrics should be boolean"

        # Test upstream health metrics (if configured)
        if "upstream_health_metrics" in config:
            assert isinstance(
                config["upstream_health_metrics"], bool
            ), "Upstream health metrics should be boolean"

    def test_prometheus_plugin_is_global(self, gateway_config: Dict[str, Any]):
        """Test that Prometheus plugin is configured globally."""
        plugins = gateway_config.get("plugins", [])
        prometheus_plugin = next((p for p in plugins if p.get("name") == "prometheus"), None)
        prometheus_plugin = next(
            (p for p in plugins if p.get("name") == "prometheus"), None
        )

        assert prometheus_plugin is not None, "Prometheus plugin should be configured"

        # Global plugins should not have service, route, or consumer scope
        assert (
            "service" not in prometheus_plugin
        ), "Prometheus plugin should be global (no service scope)"
        assert (
            "route" not in prometheus_plugin
        ), "Prometheus plugin should be global (no route scope)"
        assert (
            "consumer" not in prometheus_plugin
        ), "Prometheus plugin should be global (no consumer scope)"

    def test_prometheus_plugin_metrics_types(self, gateway_config: Dict[str, Any]):
        """Test that required metrics types are enabled."""
        plugins = gateway_config.get("plugins", [])
        prometheus_plugin = next((p for p in plugins if p.get("name") == "prometheus"), None)
        prometheus_plugin = next(
            (p for p in plugins if p.get("name") == "prometheus"), None
        )

        assert prometheus_plugin is not None, "Prometheus plugin should be configured"

        config = prometheus_plugin.get("config", {})

        # These are the core metrics that should be enabled for observability
        required_metrics = {
            "per_consumer": True,
            "status_code_metrics": True,
            "latency_metrics": True,
        }

        for metric_name, expected_value in required_metrics.items():
            assert (
                config.get(metric_name) == expected_value
            ), f"Required metric '{metric_name}' should be {expected_value}"

    def test_prometheus_plugin_no_conflicting_config(
        self, gateway_config: Dict[str, Any]
    ):
        """Test that Prometheus plugin configuration doesn't have conflicts."""
        plugins = gateway_config.get("plugins", [])
        prometheus_plugins = [p for p in plugins if p.get("name") == "prometheus"]

        # Should only have one prometheus plugin configured
        assert (
            len(prometheus_plugins) == 1
        ), f"Should have exactly one Prometheus plugin, found {len(prometheus_plugins)}"

    def test_prometheus_plugin_config_structure(self, gateway_config: Dict[str, Any]):
        """Test that Prometheus plugin configuration has proper structure."""
        plugins = gateway_config.get("plugins", [])
        prometheus_plugin = next((p for p in plugins if p.get("name") == "prometheus"), None)
        prometheus_plugin = next(
            (p for p in plugins if p.get("name") == "prometheus"), None
        )

        assert prometheus_plugin is not None, "Prometheus plugin should be configured"

        # Plugin should have name and config sections
        assert "name" in prometheus_plugin, "Plugin should have name"
        assert (
            prometheus_plugin["name"] == "prometheus"
        ), "Plugin name should be 'prometheus'"
        assert "config" in prometheus_plugin, "Plugin should have config section"

        config = prometheus_plugin["config"]
        assert isinstance(config, dict), "Plugin config should be a dictionary"
        assert len(config) > 0, "Plugin config should not be empty"
