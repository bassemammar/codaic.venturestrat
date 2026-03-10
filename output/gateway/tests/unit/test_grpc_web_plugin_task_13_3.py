"""
Task 13.3: Unit tests for gRPC-Web plugin configuration for registry-service.

This test file specifically verifies that the Kong gateway has correctly configured
the gRPC-Web plugin for the registry-service as required by task 13.3.
"""

import pytest
import yaml
import os


class TestGRPCWebPluginTask133:
    """Task 13.3 specific tests for gRPC-Web plugin configuration."""

    @pytest.fixture
    def kong_config(self):
        """Load Kong configuration from kong-test.yaml."""
        kong_yaml_path = os.path.join(os.path.dirname(__file__), "..", "..", "kong-test.yaml")
        with open(kong_yaml_path, "r") as f:
            return yaml.safe_load(f)

    def test_grpc_service_exists_for_registry(self, kong_config):
        """Test that gRPC service for registry is configured."""
        services = kong_config.get("services", [])
        registry_grpc_service = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc_service = service
                break

        assert (
            registry_grpc_service is not None
        ), "registry-grpc-service should be configured"
        assert (
            registry_grpc_service.get("protocol") == "grpc"
        ), "Should be a gRPC service"

    def test_grpc_service_upstream_configuration(self, kong_config):
        """Test that gRPC service uses correct upstream configuration."""
        services = kong_config.get("services", [])
        registry_grpc_service = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc_service = service
                break

        assert registry_grpc_service is not None

        # Should use the dedicated gRPC upstream
        assert registry_grpc_service.get("host") == "mock-registry-grpc-upstream"
        assert registry_grpc_service.get("port") == 80  # Kong upstream port
        assert registry_grpc_service.get("protocol") == "grpc"

    def test_grpc_upstream_exists(self, kong_config):
        """Test that dedicated gRPC upstream exists for registry service."""
        upstreams = kong_config.get("upstreams", [])
        grpc_upstream = None

        for upstream in upstreams:
            if upstream.get("name") == "mock-registry-grpc-upstream":
                grpc_upstream = upstream
                break

        assert (
            grpc_upstream is not None
        ), "mock-registry-grpc-upstream should be configured"

        targets = grpc_upstream.get("targets", [])
        assert len(targets) > 0, "gRPC upstream should have targets"

        # Should target port 50051 (gRPC port)
        grpc_target = targets[0]
        assert "50051" in grpc_target.get("target", ""), "Should target gRPC port 50051"

    def test_grpc_web_route_configuration(self, kong_config):
        """Test that gRPC-Web route is correctly configured."""
        services = kong_config.get("services", [])
        registry_grpc_service = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc_service = service
                break

        assert registry_grpc_service is not None

        routes = registry_grpc_service.get("routes", [])
        assert len(routes) > 0, "gRPC service should have routes"

        grpc_web_route = None
        for route in routes:
            if route.get("name") == "registry-grpc-web":
                grpc_web_route = route
                break

        assert grpc_web_route is not None, "registry-grpc-web route should exist"

        # Test route path
        paths = grpc_web_route.get("paths", [])
        assert "/grpc/v1/registry" in paths, "Should route /grpc/v1/registry path"

        # Test protocols
        protocols = grpc_web_route.get("protocols", [])
        assert "http" in protocols, "Should support HTTP protocol"
        assert "https" in protocols, "Should support HTTPS protocol"

    def test_grpc_web_plugin_configuration(self, kong_config):
        """Test that gRPC-Web plugin is correctly configured on the service."""
        services = kong_config.get("services", [])
        registry_grpc_service = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc_service = service
                break

        assert registry_grpc_service is not None

        plugins = registry_grpc_service.get("plugins", [])
        assert len(plugins) > 0, "gRPC service should have plugins"

        grpc_web_plugin = None
        for plugin in plugins:
            if plugin.get("name") == "grpc-web":
                grpc_web_plugin = plugin
                break

        assert grpc_web_plugin is not None, "grpc-web plugin should be configured"

        # Test plugin configuration
        config = grpc_web_plugin.get("config", {})
        assert (
            config.get("proto") == "/kong/protos/registry.proto"
        ), "Should point to registry proto file"

    def test_proto_file_exists(self):
        """Test that registry proto file exists in gateway protos directory."""
        proto_path = os.path.join(os.path.dirname(__file__), "..", "..", "protos", "registry.proto")
        assert os.path.exists(proto_path), f"Registry proto file should exist at {proto_path}"
        proto_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "protos", "registry.proto"
        )
        assert os.path.exists(
            proto_path
        ), f"Registry proto file should exist at {proto_path}"

    def test_proto_file_content(self):
        """Test that proto file contains expected registry service definition."""
        proto_path = os.path.join(os.path.dirname(__file__), "..", "..", "protos", "registry.proto")

        with open(proto_path, "r") as f:
            content = f.read()

        # Test for key registry service elements
        assert "service RegistryService" in content, "Should define RegistryService"
        assert (
            "package venturestrat.registry.v1" in content
        ), "Should have correct package"
        assert "rpc Register" in content, "Should have Register RPC method"
        assert "rpc Discover" in content, "Should have Discover RPC method"
        assert "rpc ListServices" in content, "Should have ListServices RPC method"

    def test_grpc_service_timeouts(self, kong_config):
        """Test that gRPC service has appropriate timeout configuration."""
        services = kong_config.get("services", [])
        registry_grpc_service = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc_service = service
                break

        assert registry_grpc_service is not None

        # Test timeout configurations
        assert registry_grpc_service.get("connect_timeout") == 5000
        assert registry_grpc_service.get("write_timeout") == 60000
        assert registry_grpc_service.get("read_timeout") == 60000
        assert registry_grpc_service.get("retries") == 3

    def test_grpc_web_path_convention(self, kong_config):
        """Test that gRPC-Web routes follow the /grpc/v1/<service> path convention."""
        services = kong_config.get("services", [])

        for service in services:
            if service.get("name") == "registry-grpc-service":
                routes = service.get("routes", [])
                for route in routes:
                    paths = route.get("paths", [])
                    for path in paths:
                        if path.startswith("/grpc/v1/"):
                            # Should follow /grpc/v1/registry pattern
                            assert (
                                path == "/grpc/v1/registry"
                            ), f"gRPC-Web path should be /grpc/v1/registry, got {path}"

    def test_grpc_service_does_not_interfere_with_rest(self, kong_config):
        """Test that gRPC service configuration doesn't interfere with REST service."""
        services = kong_config.get("services", [])

        # Find both REST and gRPC registry services
        rest_service = None
        grpc_service = None

        for service in services:
            if service.get("name") == "mock-registry-service":
                rest_service = service
            elif service.get("name") == "registry-grpc-service":
                grpc_service = service

        assert rest_service is not None, "REST registry service should still exist"
        assert grpc_service is not None, "gRPC registry service should exist"

        # They should use different protocols
        assert rest_service.get("protocol") == "http"
        assert grpc_service.get("protocol") == "grpc"

        # They should have different route paths
        rest_routes = rest_service.get("routes", [])
        grpc_routes = grpc_service.get("routes", [])

        rest_paths = []
        grpc_paths = []

        for route in rest_routes:
            rest_paths.extend(route.get("paths", []))

        for route in grpc_routes:
            grpc_paths.extend(route.get("paths", []))

        # Paths should not overlap
        for rest_path in rest_paths:
            for grpc_path in grpc_paths:
                assert (
                    rest_path != grpc_path
                ), f"REST and gRPC paths should not overlap: {rest_path} vs {grpc_path}"

    def test_yaml_configuration_is_valid(self, kong_config):
        """Test that the Kong configuration YAML is syntactically valid."""
        # If we can load it, it's valid YAML
        assert kong_config is not None, "Kong configuration should be valid YAML"
        assert "_format_version" in kong_config, "Should have format version"
        assert kong_config["_format_version"] == "3.0", "Should use Kong format version 3.0"
        assert (
            kong_config["_format_version"] == "3.0"
        ), "Should use Kong format version 3.0"
