"""
Unit tests for route path stripping configuration (Task 2.2).

Tests that Kong is correctly configured to strip paths when routing requests
to backend services. This is critical for maintaining clean service APIs
while providing a unified external interface.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any


class TestRoutePathStripping:
    """Test Kong configuration for route path stripping functionality."""

    @pytest.fixture
    def kong_config(self) -> Dict[str, Any]:
        """Load Kong configuration from kong.yaml."""
        config_path = Path(__file__).parent.parent.parent / "kong.yaml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_registry_service_route_has_strip_path(self, kong_config: Dict[str, Any]):
        """Test that registry service route is configured with strip_path: true."""
        # Find registry service configuration
        services = kong_config.get("services", [])
        registry_service = None

        for service in services:
            if service.get("name") == "registry-service":
                registry_service = service
                break

        assert registry_service is not None, "registry-service not found in kong.yaml"

        # Check routes configuration
        routes = registry_service.get("routes", [])
        assert len(routes) > 0, "registry-service has no routes configured"

        # Find the REST route
        rest_route = None
        for route in routes:
            if route.get("name") == "registry-rest":
                rest_route = route
                break

        assert rest_route is not None, "registry-rest route not found"

        # Verify strip_path is configured correctly
        assert (
            rest_route.get("strip_path") is True
        ), "registry-rest route must have strip_path: true"

    def test_registry_route_path_configuration(self, kong_config: Dict[str, Any]):
        """Test that registry route has correct path configuration."""
        services = kong_config.get("services", [])
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )

        assert registry_service is not None

        rest_route = next(
            (r for r in registry_service.get("routes", []) if r.get("name") == "registry-rest"),
            (
                r
                for r in registry_service.get("routes", [])
                if r.get("name") == "registry-rest"
            ),
            None,
        )

        assert rest_route is not None

        # Check path configuration
        paths = rest_route.get("paths", [])
        assert len(paths) > 0, "registry-rest route must have paths configured"
        assert "/api/v1/registry" in paths, "registry-rest route must include /api/v1/registry path"
        assert (
            "/api/v1/registry" in paths
        ), "registry-rest route must include /api/v1/registry path"

    def test_health_route_strip_path_configuration(self, kong_config: Dict[str, Any]):
        """Test that health route is configured correctly for path stripping."""
        services = kong_config.get("services", [])
        health_service = next((s for s in services if s.get("name") == "health-service"), None)
        health_service = next(
            (s for s in services if s.get("name") == "health-service"), None
        )

        assert health_service is not None, "health-service not found in kong.yaml"

        health_route = next(
            (r for r in health_service.get("routes", []) if r.get("name") == "health-check"),
            (
                r
                for r in health_service.get("routes", [])
                if r.get("name") == "health-check"
            ),
            None,
        )

        assert health_route is not None, "health-check route not found"

        # Health route should NOT strip path since it's an exact match
        strip_path = health_route.get("strip_path")
        assert strip_path is False, "health-check route should have strip_path: false"

    def test_all_service_routes_have_strip_path_configured(
        self, kong_config: Dict[str, Any]
    ):
        """Test that all service routes explicitly configure strip_path."""
        services = kong_config.get("services", [])

        for service in services:
            service_name = service.get("name")
            routes = service.get("routes", [])

            for route in routes:
                route_name = route.get("name")
                strip_path = route.get("strip_path")

                assert (
                    strip_path is not None
                ), f"Route {route_name} in service {service_name} must explicitly configure strip_path"
                assert isinstance(
                    strip_path, bool
                ), f"strip_path for route {route_name} must be boolean, got {type(strip_path)}"

    def test_path_stripping_semantics_for_registry(self, kong_config: Dict[str, Any]):
        """Test that registry service path stripping semantics are correct."""
        services = kong_config.get("services", [])
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)

        rest_route = next(
            (r for r in registry_service.get("routes", []) if r.get("name") == "registry-rest"),
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )

        rest_route = next(
            (
                r
                for r in registry_service.get("routes", [])
                if r.get("name") == "registry-rest"
            ),
            None,
        )

        # With strip_path: true and path: /api/v1/registry
        # Request to: /api/v1/registry/services
        # Should forward to backend as: /services

        paths = rest_route.get("paths", [])
        strip_path = rest_route.get("strip_path")

        assert "/api/v1/registry" in paths
        assert strip_path is True

        # This configuration means:
        # External path: /api/v1/registry/services
        # Backend receives: /services (after stripping /api/v1/registry)

    def test_route_protocols_support_http_and_https(self, kong_config: Dict[str, Any]):
        """Test that routes support both HTTP and HTTPS protocols."""
        services = kong_config.get("services", [])

        for service in services:
            service_name = service.get("name")
            routes = service.get("routes", [])

            for route in routes:
                route_name = route.get("name")
                protocols = route.get("protocols", [])

                assert (
                    "http" in protocols
                ), f"Route {route_name} in service {service_name} must support http protocol"
                assert (
                    "https" in protocols
                ), f"Route {route_name} in service {service_name} must support https protocol"

    def test_route_priority_configuration(self, kong_config: Dict[str, Any]):
        """Test that routes have appropriate regex_priority values."""
        services = kong_config.get("services", [])

        # Collect all routes with their priorities
        routes_with_priority = []

        for service in services:
            for route in service.get("routes", []):
                priority = route.get("regex_priority", 0)
                routes_with_priority.append(
                    {
                        "service": service.get("name"),
                        "route": route.get("name"),
                        "priority": priority,
                        "paths": route.get("paths", []),
                    }
                )

        # Health route should have higher priority than service routes
        health_route_priority = None
        registry_route_priority = None

        for route_info in routes_with_priority:
            if route_info["route"] == "health-check":
                health_route_priority = route_info["priority"]
            elif route_info["route"] == "registry-rest":
                registry_route_priority = route_info["priority"]

        assert health_route_priority is not None, "health-check route not found"
        assert registry_route_priority is not None, "registry-rest route not found"

        # Health should have higher priority (larger number = higher priority in Kong)
        assert health_route_priority > registry_route_priority, (
            f"Health route priority ({health_route_priority}) should be higher than "
            f"registry route priority ({registry_route_priority})"
        )

    def test_path_matching_patterns(self, kong_config: Dict[str, Any]):
        """Test that path matching patterns are correctly configured."""
        services = kong_config.get("services", [])
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)

        rest_route = next(
            (r for r in registry_service.get("routes", []) if r.get("name") == "registry-rest"),
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )

        rest_route = next(
            (
                r
                for r in registry_service.get("routes", [])
                if r.get("name") == "registry-rest"
            ),
            None,
        )

        paths = rest_route.get("paths", [])

        # Registry route should match /api/v1/registry prefix
        # This allows for sub-paths like /api/v1/registry/services
        registry_path = "/api/v1/registry"
        assert registry_path in paths, f"Registry route should include {registry_path} path"
        assert (
            registry_path in paths
        ), f"Registry route should include {registry_path} path"

        # Path should be prefix-based (no trailing slash in configuration)
        # Kong treats "/api/v1/registry" as a prefix match by default when strip_path is true

    def test_route_configuration_completeness(self, kong_config: Dict[str, Any]):
        """Test that routes have all required configuration fields."""
        services = kong_config.get("services", [])

        required_route_fields = ["name", "paths", "strip_path", "protocols"]

        for service in services:
            service_name = service.get("name")
            routes = service.get("routes", [])

            for route in routes:
                route_name = route.get("name")

                for field in required_route_fields:
                    assert (
                        field in route
                    ), f"Route {route_name} in service {service_name} missing required field: {field}"

                # Validate field types
                assert isinstance(route["name"], str)
                assert isinstance(route["paths"], list) and len(route["paths"]) > 0
                assert isinstance(route["strip_path"], bool)
                assert (
                    isinstance(route["protocols"], list) and len(route["protocols"]) > 0
                )

    def test_no_conflicting_path_patterns(self, kong_config: Dict[str, Any]):
        """Test that route paths don't create conflicts."""
        services = kong_config.get("services", [])

        # Collect all route paths and their priorities
        route_configs = []

        for service in services:
            for route in service.get("routes", []):
                for path in route.get("paths", []):
                    route_configs.append(
                        {
                            "service": service.get("name"),
                            "route": route.get("name"),
                            "path": path,
                            "priority": route.get("regex_priority", 0),
                            "strip_path": route.get("strip_path"),
                        }
                    )

        # Sort by priority (descending) to check precedence
        route_configs.sort(key=lambda x: x["priority"], reverse=True)

        # Check for path conflicts
        # Exact paths should have higher priority than prefix paths
        exact_paths = [r for r in route_configs if not r["strip_path"]]
        prefix_paths = [r for r in route_configs if r["strip_path"]]

        # Health check (/health) should be exact and highest priority
        health_routes = [r for r in exact_paths if r["path"] == "/health"]
        assert len(health_routes) == 1, "Should have exactly one /health route"

        health_priority = health_routes[0]["priority"]

        # All prefix routes should have lower priority than health
        for prefix_route in prefix_paths:
            assert (
                prefix_route["priority"] < health_priority
            ), f"Prefix route {prefix_route['route']} should have lower priority than health route"
