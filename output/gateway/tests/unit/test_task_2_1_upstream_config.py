"""
Unit tests specifically for Task 2.1 - upstream configuration for registry-service.

Tests the upstream design and path stripping configuration.
"""

import pytest
from typing import Dict, Any


@pytest.mark.unit
class TestTask21UpstreamConfig:
    """Test suite for Task 2.1 - upstream configuration design."""

    def test_registry_service_upstream_exists(self, gateway_config: Dict[str, Any]):
        """Test that registry-service upstream is properly configured."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        assert registry_upstream is not None, "registry-service.upstream not found"

    def test_registry_upstream_has_proper_targets(self, gateway_config: Dict[str, Any]):
        """Test that registry upstream points to correct service."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        assert registry_upstream is not None
        targets = registry_upstream.get("targets", [])
        assert len(targets) > 0, "Registry upstream should have targets"

        # Should point to registry-service (direct or Consul DNS format), not httpbin.org
        target_hosts = [t.get("target", "").split(":")[0] for t in targets]
        valid_registry_targets = ["registry-service", "registry-service.service.consul"]
        assert any(
            target in target_hosts for target in valid_registry_targets
        ), "Should target registry-service (direct or Consul format)"
        assert "httpbin.org" not in target_hosts, "Should not target httpbin.org anymore"
        assert (
            "httpbin.org" not in target_hosts
        ), "Should not target httpbin.org anymore"

    def test_registry_upstream_health_checks(self, gateway_config: Dict[str, Any]):
        """Test that registry upstream has proper health check configuration."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        assert registry_upstream is not None
        healthchecks = registry_upstream.get("healthchecks", {})
        assert "active" in healthchecks, "Should have active health checks"

        active = healthchecks["active"]
        assert active.get("type") == "http", "Should use HTTP health checks"
        assert (
            active.get("http_path") == "/health/ready"
        ), "Should check /health/ready endpoint"

    def test_registry_service_configuration(self, gateway_config: Dict[str, Any]):
        """Test that registry service is properly configured."""
        services = gateway_config.get("services", [])
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )

        assert registry_service is not None, "registry-service not found"
        assert (
            registry_service.get("host") == "registry-service.upstream"
        ), "Should use upstream"
        assert registry_service.get("protocol") == "http", "Should use HTTP protocol"

    def test_registry_route_path_stripping(self, gateway_config: Dict[str, Any]):
        """Test that registry route is configured for proper path stripping."""
        services = gateway_config.get("services", [])
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)

        assert registry_service is not None
        routes = registry_service.get("routes", [])
        registry_route = next((r for r in routes if r.get("name") == "registry-rest"), None)
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )

        assert registry_service is not None
        routes = registry_service.get("routes", [])
        registry_route = next(
            (r for r in routes if r.get("name") == "registry-rest"), None
        )

        assert registry_route is not None, "registry-rest route not found"
        assert "/api/v1/registry" in registry_route.get(
            "paths", []
        ), "Should route /api/v1/registry"
        assert registry_route.get("strip_path") is True, "Should strip path prefix"

    def test_registry_route_protocols(self, gateway_config: Dict[str, Any]):
        """Test that registry route supports both HTTP and HTTPS."""
        services = gateway_config.get("services", [])
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)

        assert registry_service is not None
        routes = registry_service.get("routes", [])
        registry_route = next((r for r in routes if r.get("name") == "registry-rest"), None)
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )

        assert registry_service is not None
        routes = registry_service.get("routes", [])
        registry_route = next(
            (r for r in routes if r.get("name") == "registry-rest"), None
        )

        assert registry_route is not None
        protocols = registry_route.get("protocols", [])
        assert "http" in protocols, "Should support HTTP"
        assert "https" in protocols, "Should support HTTPS"

    def test_registry_route_priority(self, gateway_config: Dict[str, Any]):
        """Test that registry route has proper priority configuration."""
        services = gateway_config.get("services", [])
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)

        assert registry_service is not None
        routes = registry_service.get("routes", [])
        registry_route = next((r for r in routes if r.get("name") == "registry-rest"), None)
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )

        assert registry_service is not None
        routes = registry_service.get("routes", [])
        registry_route = next(
            (r for r in routes if r.get("name") == "registry-rest"), None
        )

        assert registry_route is not None
        # Should have reasonable priority (lower number = higher priority)
        priority = registry_route.get("regex_priority", 0)
        assert 0 <= priority <= 200, "Should have reasonable priority"

    def test_upstream_load_balancing(self, gateway_config: Dict[str, Any]):
        """Test that upstream is configured for proper load balancing."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        assert registry_upstream is not None
        assert (
            registry_upstream.get("algorithm") == "round-robin"
        ), "Should use round-robin"

    def test_upstream_prepared_for_consul(self, gateway_config: Dict[str, Any]):
        """Test that upstream is prepared for Wave 2 Consul integration."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        assert registry_upstream is not None

        # Should have slots configured for dynamic targets
        assert "slots" in registry_upstream, "Should have slots for dynamic targets"
        slots = registry_upstream.get("slots")
        assert (
            isinstance(slots, int) and slots > 0
        ), "Should have positive number of slots"

    def test_service_timeouts_configured(self, gateway_config: Dict[str, Any]):
        """Test that registry service has proper timeout configuration."""
        services = gateway_config.get("services", [])
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )

        assert registry_service is not None

        # Check timeout configuration
        connect_timeout = registry_service.get("connect_timeout")
        if connect_timeout:
            assert (
                1000 <= connect_timeout <= 30000
            ), "Connect timeout should be reasonable"

        read_timeout = registry_service.get("read_timeout")
        if read_timeout:
            assert 5000 <= read_timeout <= 300000, "Read timeout should be reasonable"
