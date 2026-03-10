"""
Unit tests for Task 4.4: Verify only healthy instances receive traffic.

These tests validate that Kong configuration is set up correctly
to ensure only healthy instances receive traffic through health-aware routing.

Task 4.4: Verify: only healthy instances receive traffic
"""

import pytest
import yaml
from pathlib import Path


class TestTask44HealthyInstancesConfiguration:
    """Unit tests for health-aware routing configuration."""

    @pytest.fixture
    def kong_config(self):
        """Load Kong configuration for testing."""
        config_path = Path(__file__).parent.parent.parent / "kong.yaml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_upstream_has_health_checks_configured(self, kong_config):
        """Test that upstream has proper health check configuration for traffic routing."""
        upstreams = kong_config.get("upstreams", [])

        # Find registry service upstream
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        assert registry_upstream is not None, "registry-service.upstream must be configured"
        assert (
            registry_upstream is not None
        ), "registry-service.upstream must be configured"
        assert (
            "healthchecks" in registry_upstream
        ), "Upstream must have health checks for instance exclusion"

        healthchecks = registry_upstream["healthchecks"]
        assert (
            "active" in healthchecks
        ), "Active health checks required for healthy instance detection"
        assert (
            "passive" in healthchecks
        ), "Passive health checks required for unhealthy instance detection"

    def test_active_health_checks_configuration_for_healthy_instance_routing(
        self, kong_config
    ):
        """Test active health checks are configured to detect healthy instances."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        active_healthcheck = registry_upstream["healthchecks"]["active"]

        # Verify health check settings that determine healthy instance routing
        assert (
            active_healthcheck["type"] == "http"
        ), "HTTP health checks required to detect service health"
        assert (
            active_healthcheck["http_path"] == "/health/ready"
        ), "Health check path must validate service readiness"

        # Verify healthy thresholds - determines when instances receive traffic
        healthy = active_healthcheck["healthy"]
        assert (
            healthy["interval"] > 0
        ), "Health check interval must be configured for continuous monitoring"
        assert (
            healthy["successes"] >= 1
        ), "Must require successes to mark instance healthy for traffic"

        # Verify unhealthy thresholds - determines when instances are excluded from traffic
        unhealthy = active_healthcheck["unhealthy"]
        assert unhealthy["interval"] > 0, "Unhealthy check interval must monitor for failures"
        assert (
            unhealthy["http_failures"] >= 1
        ), "Must detect HTTP failures to exclude unhealthy instances"
        assert unhealthy["timeouts"] >= 1, "Must detect timeouts to exclude unresponsive instances"
        assert (
            unhealthy["interval"] > 0
        ), "Unhealthy check interval must monitor for failures"
        assert (
            unhealthy["http_failures"] >= 1
        ), "Must detect HTTP failures to exclude unhealthy instances"
        assert (
            unhealthy["timeouts"] >= 1
        ), "Must detect timeouts to exclude unresponsive instances"
        assert (
            unhealthy["tcp_failures"] >= 1
        ), "Must detect TCP failures to exclude unreachable instances"

    def test_passive_health_checks_configuration_for_instance_exclusion(
        self, kong_config
    ):
        """Test passive health checks are configured to exclude unhealthy instances."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        passive_healthcheck = registry_upstream["healthchecks"]["passive"]

        # Verify passive health check settings
        assert (
            passive_healthcheck["type"] == "http"
        ), "HTTP passive checks required for response-based health detection"

        # Verify healthy status codes - determines when instances continue receiving traffic
        healthy = passive_healthcheck["healthy"]
        healthy_codes = healthy["http_statuses"]
        assert (
            200 in healthy_codes
        ), "200 OK must be considered healthy for traffic routing"
        assert 201 in healthy_codes, "201 Created must be considered healthy"
        assert (
            healthy["successes"] >= 1
        ), "Must require successes to maintain healthy status"

        # Verify unhealthy status codes - determines when instances are excluded from traffic
        unhealthy = passive_healthcheck["unhealthy"]
        unhealthy_codes = unhealthy["http_statuses"]

        # Critical error codes that should exclude instances from traffic
        assert (
            500 in unhealthy_codes
        ), "500 Internal Server Error must exclude instance from traffic"
        assert 502 in unhealthy_codes, "502 Bad Gateway must exclude instance from traffic"
        assert 503 in unhealthy_codes, "503 Service Unavailable must exclude instance from traffic"
        assert 504 in unhealthy_codes, "504 Gateway Timeout must exclude instance from traffic"
        assert (
            502 in unhealthy_codes
        ), "502 Bad Gateway must exclude instance from traffic"
        assert (
            503 in unhealthy_codes
        ), "503 Service Unavailable must exclude instance from traffic"
        assert (
            504 in unhealthy_codes
        ), "504 Gateway Timeout must exclude instance from traffic"

        # Verification thresholds
        assert (
            unhealthy["tcp_failures"] >= 1
        ), "TCP failures must exclude instances from traffic"
        assert (
            unhealthy["timeouts"] >= 1
        ), "Timeouts must exclude instances from traffic"
        assert (
            unhealthy["http_failures"] >= 1
        ), "HTTP failures must exclude instances from traffic"

    def test_upstream_load_balancing_algorithm_supports_health_awareness(
        self, kong_config
    ):
        """Test that upstream load balancing algorithm supports health-aware routing."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        # Check load balancing algorithm
        algorithm = registry_upstream.get("algorithm", "round-robin")
        supported_algorithms = [
            "round-robin",
            "consistent-hashing",
            "least-connections",
            "ring-hash",
        ]

        assert (
            algorithm in supported_algorithms
        ), f"Algorithm '{algorithm}' must support health-aware routing"

        # Verify slots configuration if present
        if "slots" in registry_upstream:
            assert (
                registry_upstream["slots"] > 0
            ), "Slots must be positive for load balancing"

    def test_service_routing_configuration_supports_healthy_instances(
        self, kong_config
    ):
        """Test that service routing is configured to work with healthy instances."""
        services = kong_config.get("services", [])

        # Find registry service
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )

        assert (
            registry_service is not None
        ), "Registry service must be configured for routing"

        # Verify service points to upstream (not direct host)
        if "host" in registry_service:
            host = registry_service["host"]
            assert (
                host == "registry-service.upstream"
            ), "Service must use upstream for health-aware routing, not direct host"

        # Verify service configuration supports health checks
        assert registry_service.get("protocol") in [
            "http",
            "https",
        ], "Service protocol must support HTTP health checks"

        # Check for routes
        routes = registry_service.get("routes", [])
        assert (
            len(routes) > 0
        ), "Service must have routes configured for traffic routing"

        # Verify route paths
        registry_route = routes[0]  # Primary route
        paths = registry_route.get("paths", [])
        assert len(paths) > 0, "Route must have paths for traffic routing"
        assert any(
            "/api/v1/registry" in path for path in paths
        ), "Registry route must be configured for expected path"

    def test_health_check_timing_configuration_for_responsive_failover(
        self, kong_config
    ):
        """Test that health check timing enables responsive failover to healthy instances."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        healthchecks = registry_upstream["healthchecks"]

        # Active health check timing
        active = healthchecks["active"]
        healthy_interval = active["healthy"]["interval"]
        unhealthy_interval = active["unhealthy"]["interval"]

        # Intervals should be reasonable for responsive failover
        assert (
            1 <= healthy_interval <= 60
        ), f"Healthy check interval ({healthy_interval}s) should be responsive but not overwhelming"
        assert (
            1 <= unhealthy_interval <= 60
        ), f"Unhealthy check interval ({unhealthy_interval}s) should detect failures quickly"

        # Success/failure thresholds should be reasonable
        healthy_successes = active["healthy"]["successes"]
        unhealthy_failures = active["unhealthy"]["http_failures"]

        assert (
            1 <= healthy_successes <= 10
        ), f"Healthy successes threshold ({healthy_successes}) should be reasonable"
        assert (
            1 <= unhealthy_failures <= 10
        ), f"Unhealthy failures threshold ({unhealthy_failures}) should be reasonable"

        # Passive health check thresholds
        passive = healthchecks["passive"]
        passive_healthy_successes = passive["healthy"]["successes"]
        passive_unhealthy_failures = passive["unhealthy"]["http_failures"]

        assert (
            1 <= passive_healthy_successes <= 10
        ), f"Passive healthy successes ({passive_healthy_successes}) should be reasonable"
        assert (
            1 <= passive_unhealthy_failures <= 10
        ), f"Passive unhealthy failures ({passive_unhealthy_failures}) should be reasonable"

    def test_upstream_targets_configuration_for_health_monitoring(self, kong_config):
        """Test that upstream targets are configured properly for health monitoring."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        # Check if targets are configured
        targets = registry_upstream.get("targets", [])

        if targets:
            # If targets are configured, verify they support health checks
            for target in targets:
                assert "target" in target, "Target must specify target address"

                # Weight should be configured for load balancing
                weight = target.get("weight", 100)
                assert (
                    0 <= weight <= 1000
                ), f"Target weight ({weight}) must be in valid range"

                # Target address should be reachable for health checks
                target_addr = target["target"]
                assert ":" in target_addr or target_addr.endswith(
                    ".consul"
                assert (
                    ":" in target_addr or target_addr.endswith(".consul")
                ), f"Target ({target_addr}) should specify port or use service discovery"

    def test_configuration_enables_only_healthy_instances_receive_traffic(
        self, kong_config
    ):
        """Master test verifying complete configuration for health-aware traffic routing."""

        # 1. Verify upstream exists with health checks
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )
        assert (
            registry_upstream is not None
        ), "Upstream must exist for health-aware routing"
        assert "healthchecks" in registry_upstream, "Health checks must be configured"

        # 2. Verify service routes through upstream
        services = kong_config.get("services", [])
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )
        assert registry_service is not None, "Service must exist for routing"
        assert (
            registry_service.get("host") == "registry-service.upstream"
        ), "Service must route through health-checked upstream"

        # 3. Verify health checks can detect healthy/unhealthy states
        healthchecks = registry_upstream["healthchecks"]

        active = healthchecks["active"]
        assert active["type"] == "http", "Must use HTTP health checks"
        assert active["http_path"] == "/health/ready", "Must check service readiness"

        passive = healthchecks["passive"]
        assert 500 in passive["unhealthy"]["http_statuses"], "Must detect server errors"
        assert (
            200 in passive["healthy"]["http_statuses"]
        ), "Must recognize healthy responses"

        # 4. Verify timing allows responsive failover
        assert (
            active["healthy"]["interval"] <= 30
        ), "Health checks must be frequent enough"
        assert (
            active["unhealthy"]["interval"] <= 30
        ), "Failure detection must be responsive"

        print(
            "✓ Configuration verified: Kong will only route traffic to healthy instances"
        )


class TestTask44ValidationScenarios:
    """Test validation scenarios for health-aware routing."""

    @pytest.fixture
    def kong_config(self):
        """Load Kong configuration for testing."""
        config_path = Path(__file__).parent.parent.parent / "kong.yaml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_healthy_instance_scenario_configuration(self, kong_config):
        """Test configuration handles healthy instance scenario correctly."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        healthchecks = registry_upstream["healthchecks"]

        # When instance responds with 200 to /health/ready
        active_healthy = healthchecks["active"]["healthy"]
        passive_healthy = healthchecks["passive"]["healthy"]

        # Should be marked healthy after configured successes
        assert (
            active_healthy["successes"] >= 1
        ), "Must require at least 1 success for healthy status"
        assert 200 in passive_healthy["http_statuses"], "200 responses must be considered healthy"

        # Instance should receive traffic
        assert (
            "algorithm" in registry_upstream or registry_upstream.get("algorithm") == "round-robin"
        assert (
            200 in passive_healthy["http_statuses"]
        ), "200 responses must be considered healthy"

        # Instance should receive traffic
        assert (
            "algorithm" in registry_upstream
            or registry_upstream.get("algorithm") == "round-robin"
        ), "Load balancing algorithm must distribute traffic to healthy instances"

    def test_unhealthy_instance_scenario_configuration(self, kong_config):
        """Test configuration handles unhealthy instance scenario correctly."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        healthchecks = registry_upstream["healthchecks"]

        # When instance responds with 500 or times out
        active_unhealthy = healthchecks["active"]["unhealthy"]
        passive_unhealthy = healthchecks["passive"]["unhealthy"]

        # Should be marked unhealthy after configured failures
        assert active_unhealthy["http_failures"] >= 1, "Must detect HTTP failures"
        assert active_unhealthy["timeouts"] >= 1, "Must detect timeouts"
        assert active_unhealthy["tcp_failures"] >= 1, "Must detect TCP failures"

        # Instance should be excluded from traffic
        assert (
            500 in passive_unhealthy["http_statuses"]
        ), "500 errors must exclude instance"
        assert (
            502 in passive_unhealthy["http_statuses"]
        ), "502 errors must exclude instance"
        assert (
            503 in passive_unhealthy["http_statuses"]
        ), "503 errors must exclude instance"

    def test_mixed_health_scenario_configuration(self, kong_config):
        """Test configuration handles mixed healthy/unhealthy instances correctly."""
        upstreams = kong_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        # Load balancing should only include healthy instances
        algorithm = registry_upstream.get("algorithm", "round-robin")
        supported_algorithms = [
            "round-robin",
            "consistent-hashing",
            "least-connections",
        ]
        assert (
            algorithm in supported_algorithms
        ), f"Algorithm {algorithm} must support health-aware load balancing"

        # Health checks must be able to differentiate
        healthchecks = registry_upstream["healthchecks"]
        healthchecks["active"]
        passive = healthchecks["passive"]

        # Clear distinction between healthy and unhealthy
        healthy_codes = set(passive["healthy"]["http_statuses"])
        unhealthy_codes = set(passive["unhealthy"]["http_statuses"])

        # No overlap in status codes
        assert not (
            healthy_codes & unhealthy_codes
        ), "Healthy and unhealthy status codes must not overlap"

        # Must include key status codes
        assert 200 in healthy_codes, "200 must be healthy"
        assert 500 in unhealthy_codes, "500 must be unhealthy"
