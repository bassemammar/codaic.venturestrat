"""
Unit tests for health check configuration validation.

Tests the Kong configuration for proper health check setup
without requiring running infrastructure.

Task 4.1: Write tests for unhealthy instance exclusion (Unit tests)
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any


class TestHealthCheckConfiguration:
    """Unit tests for health check configuration in kong.yaml."""

    @pytest.fixture
    def kong_config(self) -> Dict[str, Any]:
        """Load kong.yaml configuration for testing."""
        config_path = Path(__file__).parent.parent.parent / "kong.yaml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_upstream_has_health_checks(self, kong_config):
        """Test that registry-service upstream has health check configuration."""
        upstreams = kong_config.get("upstreams", [])

        # Find the registry-service upstream
        registry_upstream = None
        for upstream in upstreams:
            if upstream.get("name") == "registry-service.upstream":
                registry_upstream = upstream
                break

        assert registry_upstream is not None, "registry-service.upstream not found"
        assert (
            "healthchecks" in registry_upstream
        ), "No healthchecks configured for registry-service"

    def test_active_health_check_complete_configuration(self, kong_config):
        """Test active health check configuration is complete."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        healthchecks = registry_upstream["healthchecks"]
        assert "active" in healthchecks, "Active health checks not configured"

        active = healthchecks["active"]

        # Required fields
        assert active["type"] == "http", "Active health check must be HTTP"
        assert (
            active["http_path"] == "/health/ready"
        ), "Health check path must be /health/ready"

        # Healthy configuration
        assert "healthy" in active, "Healthy configuration missing"
        healthy = active["healthy"]
        assert "interval" in healthy, "Healthy interval not configured"
        assert "successes" in healthy, "Healthy successes threshold not configured"
        assert isinstance(healthy["interval"], int), "Healthy interval must be integer"
        assert isinstance(
            healthy["successes"], int
        ), "Healthy successes must be integer"
        assert healthy["interval"] > 0, "Healthy interval must be positive"
        assert healthy["successes"] > 0, "Healthy successes must be positive"

        # Unhealthy configuration
        assert "unhealthy" in active, "Unhealthy configuration missing"
        unhealthy = active["unhealthy"]
        assert "interval" in unhealthy, "Unhealthy interval not configured"
        assert "http_failures" in unhealthy, "HTTP failures threshold not configured"
        assert "timeouts" in unhealthy, "Timeouts threshold not configured"
        assert "tcp_failures" in unhealthy, "TCP failures threshold not configured"

        # Validate types and values
        assert isinstance(
            unhealthy["interval"], int
        ), "Unhealthy interval must be integer"
        assert isinstance(
            unhealthy["http_failures"], int
        ), "HTTP failures must be integer"
        assert isinstance(unhealthy["timeouts"], int), "Timeouts must be integer"
        assert isinstance(
            unhealthy["tcp_failures"], int
        ), "TCP failures must be integer"

        assert unhealthy["interval"] > 0, "Unhealthy interval must be positive"
        assert (
            unhealthy["http_failures"] > 0
        ), "HTTP failures threshold must be positive"
        assert unhealthy["timeouts"] > 0, "Timeouts threshold must be positive"
        assert unhealthy["tcp_failures"] > 0, "TCP failures threshold must be positive"

    def test_passive_health_check_complete_configuration(self, kong_config):
        """Test passive health check configuration is complete."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        healthchecks = registry_upstream["healthchecks"]
        assert "passive" in healthchecks, "Passive health checks not configured"

        passive = healthchecks["passive"]

        # Required fields
        assert passive["type"] == "http", "Passive health check must be HTTP"

        # Healthy configuration
        assert "healthy" in passive, "Healthy configuration missing"
        healthy = passive["healthy"]
        assert "http_statuses" in healthy, "Healthy HTTP statuses not configured"
        assert "successes" in healthy, "Healthy successes threshold not configured"

        # Validate healthy status codes
        healthy_codes = healthy["http_statuses"]
        assert isinstance(healthy_codes, list), "Healthy HTTP statuses must be a list"
        assert len(healthy_codes) > 0, "Must have at least one healthy status code"
        for code in healthy_codes:
            assert isinstance(code, int), f"Status code must be integer: {code}"
            assert 200 <= code <= 399, f"Healthy code should be 2xx or 3xx: {code}"

        # Should include standard success codes
        assert 200 in healthy_codes, "Should include 200 as healthy status"

        # Unhealthy configuration
        assert "unhealthy" in passive, "Unhealthy configuration missing"
        unhealthy = passive["unhealthy"]
        assert "http_statuses" in unhealthy, "Unhealthy HTTP statuses not configured"
        assert "tcp_failures" in unhealthy, "TCP failures threshold not configured"
        assert "timeouts" in unhealthy, "Timeouts threshold not configured"
        assert "http_failures" in unhealthy, "HTTP failures threshold not configured"

        # Validate unhealthy status codes
        unhealthy_codes = unhealthy["http_statuses"]
        assert isinstance(
            unhealthy_codes, list
        ), "Unhealthy HTTP statuses must be a list"
        assert len(unhealthy_codes) > 0, "Must have at least one unhealthy status code"
        for code in unhealthy_codes:
            assert isinstance(code, int), f"Status code must be integer: {code}"
            assert 400 <= code <= 599, f"Unhealthy code should be 4xx or 5xx: {code}"

        # Should include standard error codes
        assert 500 in unhealthy_codes, "Should include 500 as unhealthy status"
        assert 502 in unhealthy_codes, "Should include 502 as unhealthy status"
        assert 503 in unhealthy_codes, "Should include 503 as unhealthy status"

    def test_health_check_timing_reasonable(self, kong_config):
        """Test that health check timings are reasonable."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        active = registry_upstream["healthchecks"]["active"]

        # Check intervals are reasonable
        healthy_interval = active["healthy"]["interval"]
        unhealthy_interval = active["unhealthy"]["interval"]

        assert (
            5 <= healthy_interval <= 60
        ), f"Healthy interval should be 5-60 seconds: {healthy_interval}"
        assert (
            5 <= unhealthy_interval <= 60
        ), f"Unhealthy interval should be 5-60 seconds: {unhealthy_interval}"

        # Check thresholds are reasonable
        healthy_successes = active["healthy"]["successes"]
        unhealthy_failures = active["unhealthy"]["http_failures"]
        unhealthy_timeouts = active["unhealthy"]["timeouts"]
        unhealthy_tcp_failures = active["unhealthy"]["tcp_failures"]

        assert (
            1 <= healthy_successes <= 10
        ), f"Healthy successes should be 1-10: {healthy_successes}"
        assert 1 <= unhealthy_failures <= 10, f"HTTP failures should be 1-10: {unhealthy_failures}"
        assert 1 <= unhealthy_timeouts <= 20, f"Timeouts should be 1-20: {unhealthy_timeouts}"
        assert (
            1 <= unhealthy_failures <= 10
        ), f"HTTP failures should be 1-10: {unhealthy_failures}"
        assert (
            1 <= unhealthy_timeouts <= 20
        ), f"Timeouts should be 1-20: {unhealthy_timeouts}"
        assert (
            1 <= unhealthy_tcp_failures <= 10
        ), f"TCP failures should be 1-10: {unhealthy_tcp_failures}"

    def test_health_check_path_validity(self, kong_config):
        """Test that health check path is valid."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        active = registry_upstream["healthchecks"]["active"]
        http_path = active["http_path"]

        # Path should be valid HTTP path
        assert http_path.startswith("/"), "Health check path must start with /"
        assert len(http_path) > 1, "Health check path cannot be just /"
        assert not http_path.endswith("/"), "Health check path should not end with /"
        assert " " not in http_path, "Health check path should not contain spaces"

        # Should be a standard health check path
        valid_paths = ["/health", "/health/ready", "/health/live", "/healthz", "/ready"]
        assert (
            http_path in valid_paths
        ), f"Health check path should be standard: {http_path}"

    def test_upstream_load_balancing_configuration(self, kong_config):
        """Test that upstream is configured for proper load balancing."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        # Check load balancing algorithm
        algorithm = registry_upstream.get("algorithm")
        valid_algorithms = [
            "round-robin",
            "least-connections",
            "ip-hash",
            "consistent-hashing",
        ]
        if algorithm:
            assert algorithm in valid_algorithms, f"Invalid algorithm: {algorithm}"

        # Check slots configuration (if present)
        slots = registry_upstream.get("slots")
        if slots:
            assert isinstance(slots, int), "Slots must be integer"
            assert 10 <= slots <= 65536, f"Slots should be 10-65536: {slots}"

        # Check hash configuration (if using hash-based algorithms)
        if algorithm in ["ip-hash", "consistent-hashing"]:
            assert (
                "hash_on" in registry_upstream
            ), "Hash-based algorithm requires hash_on"
            hash_on = registry_upstream["hash_on"]
            valid_hash_on = ["none", "consumer", "ip", "header", "cookie", "path"]
            assert hash_on in valid_hash_on, f"Invalid hash_on: {hash_on}"

    def test_upstream_targets_configuration(self, kong_config):
        """Test that upstream targets are properly configured."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        assert "targets" in registry_upstream, "Upstream must have targets"
        targets = registry_upstream["targets"]

        assert isinstance(targets, list), "Targets must be a list"
        assert len(targets) > 0, "Must have at least one target"

        for target in targets:
            assert "target" in target, "Each target must have target field"
            assert "weight" in target, "Each target must have weight field"

            target_address = target["target"]
            weight = target["weight"]

            # Validate target format
            assert isinstance(target_address, str), "Target address must be string"
            assert len(target_address) > 0, "Target address cannot be empty"

            # Should be Consul service format
            assert (
                ".service.consul" in target_address
            ), "Target should use Consul service discovery"

            # Validate weight
            assert isinstance(weight, int), "Weight must be integer"
            assert 0 <= weight <= 10000, f"Weight should be 0-10000: {weight}"

    def test_upstream_consul_service_format(self, kong_config):
        """Test that Consul service targets follow proper format."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        targets = registry_upstream["targets"]

        for target in targets:
            target_address = target["target"]

            if ".service.consul" in target_address:
                # Parse Consul service format: service-name.service.consul:port
                if ":" in target_address:
                    hostname, port = target_address.split(":", 1)
                    assert port.isdigit(), f"Port must be numeric: {port}"
                    port_num = int(port)
                    assert 1 <= port_num <= 65535, f"Port must be 1-65535: {port_num}"
                else:
                    hostname = target_address

                # Validate hostname format
                parts = hostname.split(".")
                assert len(parts) >= 3, f"Invalid Consul service format: {hostname}"
                assert (
                    parts[-2] == "service"
                ), f"Must include 'service' in DNS name: {hostname}"
                assert parts[-1] == "consul", f"Must end with 'consul': {hostname}"

                # Service name should be valid
                service_name = parts[0]
                assert (
                    service_name.replace("-", "").replace("_", "").isalnum()
                ), f"Invalid service name: {service_name}"

    def test_health_check_compatibility_with_service(self, kong_config):
        """Test that health check configuration is compatible with service setup."""
        # Get service configuration
        services = kong_config.get("services", [])
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )

        assert registry_service is not None, "registry-service not found"

        # Get upstream configuration
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        # Service should point to upstream
        service_host = registry_service.get("host")
        upstream_name = registry_upstream.get("name")
        assert (
            service_host == upstream_name
        ), f"Service host ({service_host}) should match upstream name ({upstream_name})"

        # Service timeouts should be compatible with health check intervals
        connect_timeout = registry_service.get("connect_timeout", 60000)  # Default 60s
        read_timeout = registry_service.get("read_timeout", 60000)
        write_timeout = registry_service.get("write_timeout", 60000)

        # Convert to seconds
        connect_timeout_s = connect_timeout / 1000
        read_timeout_s = read_timeout / 1000
        write_timeout / 1000

        # Health check intervals should be reasonable relative to service timeouts
        active = registry_upstream["healthchecks"]["active"]
        healthy_interval = active["healthy"]["interval"]
        unhealthy_interval = active["unhealthy"]["interval"]

        # Health check intervals can be longer than connect timeout (that's normal)
        # But they should be much shorter than read timeout to detect failures quickly
        assert (
            healthy_interval < read_timeout_s
        ), f"Health check interval ({healthy_interval}s) should be less than read timeout ({read_timeout_s}s)"
        assert (
            unhealthy_interval < read_timeout_s
        ), f"Unhealthy check interval ({unhealthy_interval}s) should be less than read timeout ({read_timeout_s}s)"

        # Connect timeout should be reasonable for health checks
        assert (
            connect_timeout_s >= 1
        ), "Connect timeout should be at least 1 second for health checks"
        assert connect_timeout_s <= 30, "Connect timeout should not be too long for health checks"
        assert (
            connect_timeout_s <= 30
        ), "Connect timeout should not be too long for health checks"

    def test_prometheus_metrics_includes_upstream_health(self, kong_config):
        """Test that Prometheus plugin is configured to collect upstream health metrics."""
        plugins = kong_config.get("plugins", [])

        # Find Prometheus plugin
        prometheus_plugin = None
        for plugin in plugins:
            if plugin.get("name") == "prometheus":
                prometheus_plugin = plugin
                break

        assert prometheus_plugin is not None, "Prometheus plugin not configured"

        config = prometheus_plugin.get("config", {})

        # Should collect upstream health metrics
        upstream_health_metrics = config.get("upstream_health_metrics")
        assert upstream_health_metrics is True, "Prometheus should collect upstream health metrics"
        assert (
            upstream_health_metrics is True
        ), "Prometheus should collect upstream health metrics"

        # Should also collect other relevant metrics
        assert config.get("latency_metrics") is True, "Should collect latency metrics"
        assert (
            config.get("status_code_metrics") is True
        ), "Should collect status code metrics"

    def test_no_conflicting_health_check_configurations(self, kong_config):
        """Test that there are no conflicting health check configurations."""
        upstreams = kong_config.get("upstreams", [])

        for upstream in upstreams:
            if "healthchecks" in upstream:
                healthchecks = upstream["healthchecks"]

                # Active and passive checks should not conflict
                if "active" in healthchecks and "passive" in healthchecks:
                    active = healthchecks["active"]
                    passive = healthchecks["passive"]

                    # Both should be HTTP type for consistency
                    assert active["type"] == "http", "Active checks should be HTTP type"
                    assert (
                        passive["type"] == "http"
                    ), "Passive checks should be HTTP type"

                    # Success thresholds should be reasonable relative to each other
                    active_successes = active["healthy"]["successes"]
                    passive_successes = passive["healthy"]["successes"]

                    # Active checks are more reliable, so can have lower threshold
                    assert (
                        active_successes <= passive_successes + 2
                    ), "Active check successes should not be much higher than passive"

                    # Failure thresholds should be consistent
                    active_failures = active["unhealthy"]["http_failures"]
                    passive_failures = passive["unhealthy"]["http_failures"]

                    assert (
                        abs(active_failures - passive_failures) <= 2
                    ), "Active and passive failure thresholds should be similar"

    def test_active_health_check_enhanced_configuration(self, kong_config):
        """Test enhanced active health check configuration parameters."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        active = registry_upstream["healthchecks"]["active"]

        # Test timeout configuration
        if "timeout" in active:
            timeout = active["timeout"]
            assert isinstance(timeout, int), "Timeout must be integer"
            assert 1 <= timeout <= 30, f"Timeout should be 1-30 seconds: {timeout}"

        # Test concurrency configuration
        if "concurrency" in active:
            concurrency = active["concurrency"]
            assert isinstance(concurrency, int), "Concurrency must be integer"
            assert 1 <= concurrency <= 10, f"Concurrency should be 1-10: {concurrency}"

        # Test HTTPS verification setting
        if "https_verify_certificate" in active:
            https_verify = active["https_verify_certificate"]
            assert isinstance(https_verify, bool), "HTTPS verify must be boolean"

        # Test healthy status codes if specified
        healthy = active.get("healthy", {})
        if "http_statuses" in healthy:
            healthy_codes = healthy["http_statuses"]
            assert isinstance(
                healthy_codes, list
            ), "Healthy HTTP statuses must be a list"
            for code in healthy_codes:
                assert isinstance(code, int), f"Status code must be integer: {code}"
                assert 200 <= code <= 399, f"Healthy code should be 2xx or 3xx: {code}"

        # Test unhealthy status codes if specified
        unhealthy = active.get("unhealthy", {})
        if "http_statuses" in unhealthy:
            unhealthy_codes = unhealthy["http_statuses"]
            assert isinstance(
                unhealthy_codes, list
            ), "Unhealthy HTTP statuses must be a list"
            for code in unhealthy_codes:
                assert isinstance(code, int), f"Status code must be integer: {code}"
                assert (
                    400 <= code <= 599
                ), f"Unhealthy code should be 4xx or 5xx: {code}"

    def test_health_check_performance_configuration(self, kong_config):
        """Test health check performance and reliability configuration."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        active = registry_upstream["healthchecks"]["active"]

        # Check performance-related settings
        timeout = active.get("timeout", 10)  # Default Kong timeout
        interval = active["healthy"]["interval"]

        # Timeout should be less than interval to prevent overlap
        assert (
            timeout < interval
        ), f"Timeout ({timeout}s) should be less than interval ({interval}s)"

        # Concurrency should be reasonable
        concurrency = active.get("concurrency", 1)  # Default Kong concurrency
        assert (
            1 <= concurrency <= 5
        ), f"Concurrency should be reasonable for health checks: {concurrency}"

        # Health check intervals should allow for service startup
        assert (
            interval >= 5
        ), f"Health check interval should allow for service startup: {interval}s"

    def test_health_check_failure_thresholds_consistency(self, kong_config):
        """Test that failure thresholds are consistent and reasonable."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        active = registry_upstream["healthchecks"]["active"]
        passive = registry_upstream["healthchecks"]["passive"]

        # Active health check thresholds
        active_http_failures = active["unhealthy"]["http_failures"]
        active_timeouts = active["unhealthy"]["timeouts"]
        active_tcp_failures = active["unhealthy"]["tcp_failures"]

        # Passive health check thresholds
        passive_http_failures = passive["unhealthy"]["http_failures"]
        passive_timeouts = passive["unhealthy"]["timeouts"]
        passive_tcp_failures = passive["unhealthy"]["tcp_failures"]

        # Active checks should be more sensitive (lower thresholds) since they're proactive
        assert (
            active_http_failures <= passive_http_failures + 2
        ), "Active HTTP failures threshold should not be much higher than passive"

        assert (
            active_tcp_failures <= passive_tcp_failures + 2
        ), "Active TCP failures threshold should not be much higher than passive"

        # Timeouts can be higher for active checks since they control the test
        assert (
            active_timeouts >= passive_timeouts
        ), "Active timeout threshold should be at least as high as passive"

        # All thresholds should be reasonable
        assert 1 <= active_http_failures <= 10, "Active HTTP failures should be 1-10"
        assert 1 <= active_timeouts <= 20, "Active timeouts should be 1-20"
        assert 1 <= active_tcp_failures <= 10, "Active TCP failures should be 1-10"

    def test_health_check_status_code_coverage(self, kong_config):
        """Test that health check status codes provide good coverage."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        passive = registry_upstream["healthchecks"]["passive"]

        # Get healthy and unhealthy status codes
        healthy_codes = passive["healthy"]["http_statuses"]
        unhealthy_codes = passive["unhealthy"]["http_statuses"]

        # Ensure good coverage of HTTP status codes
        # Healthy codes should cover main success codes
        assert 200 in healthy_codes, "Should include 200 (OK)"
        assert any(
            code in healthy_codes for code in [201, 202, 204]
        ), "Should include other 2xx codes"

        # Unhealthy codes should cover main error codes
        assert 500 in unhealthy_codes, "Should include 500 (Internal Server Error)"
        assert 502 in unhealthy_codes, "Should include 502 (Bad Gateway)"
        assert 503 in unhealthy_codes, "Should include 503 (Service Unavailable)"

        # No overlap between healthy and unhealthy codes
        overlapping_codes = set(healthy_codes) & set(unhealthy_codes)
        assert (
            len(overlapping_codes) == 0
        ), f"Status codes should not overlap: {overlapping_codes}"

        # Together they should cover most of the HTTP status range
        all_configured_codes = set(healthy_codes) | set(unhealthy_codes)
        assert len(all_configured_codes) >= 8, "Should configure at least 8 status codes total"
        assert (
            len(all_configured_codes) >= 8
        ), "Should configure at least 8 status codes total"
