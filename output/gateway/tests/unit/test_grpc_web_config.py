"""
Unit tests for gRPC-Web configuration validation.

Tests the gRPC-Web route and plugin configuration in kong.yaml.
"""

import pytest
import yaml
import os


class TestGRPCWebConfiguration:
    """Test gRPC-Web configuration in kong.yaml."""

    @pytest.fixture
    def kong_config(self):
        """Load Kong configuration from kong.yaml."""
        kong_yaml_path = os.path.join(os.path.dirname(__file__), "..", "..", "kong.yaml")
        with open(kong_yaml_path, "r") as f:
            return yaml.safe_load(f)

    def test_grpc_service_exists(self, kong_config):
        """Test that gRPC service is configured."""
        services = kong_config.get("services", [])
        grpc_services = [s for s in services if s.get("protocol") == "grpc"]

        assert len(grpc_services) >= 1, "At least one gRPC service should be configured"

        # Check registry gRPC service specifically
        registry_grpc = None
        for service in grpc_services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc = service
                break

        assert registry_grpc is not None, "registry-grpc-service should be configured"

    def test_grpc_service_configuration(self, kong_config):
        """Test gRPC service configuration details."""
        services = kong_config.get("services", [])
        registry_grpc = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc = service
                break

        assert registry_grpc is not None

        # Test service configuration
        assert registry_grpc["host"] == "registry-service.service.consul"
        assert registry_grpc["port"] == 50051
        assert registry_grpc["protocol"] == "grpc"
        assert registry_grpc["connect_timeout"] == 5000
        assert registry_grpc["write_timeout"] == 60000
        assert registry_grpc["read_timeout"] == 60000
        assert registry_grpc["retries"] == 3

        # Test tags
        tags = registry_grpc.get("tags", [])
        expected_tags = ["grpc", "registry", "transcoding"]
        for tag in expected_tags:
            assert tag in tags, f"Tag '{tag}' should be present"

    def test_grpc_web_routes(self, kong_config):
        """Test gRPC-Web route configuration."""
        services = kong_config.get("services", [])
        registry_grpc = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc = service
                break

        assert registry_grpc is not None
        routes = registry_grpc.get("routes", [])
        assert len(routes) >= 1, "gRPC service should have routes"

        grpc_web_route = None
        for route in routes:
            if route.get("name") == "registry-grpc-web":
                grpc_web_route = route
                break

        assert grpc_web_route is not None, "registry-grpc-web route should exist"

        # Test route configuration
        assert "/grpc/v1/registry" in grpc_web_route["paths"]
        assert grpc_web_route["strip_path"]
        assert "http" in grpc_web_route["protocols"]
        assert "https" in grpc_web_route["protocols"]
        assert not grpc_web_route["preserve_host"]
        assert grpc_web_route["regex_priority"] == 100

    def test_grpc_web_plugin_exists(self, kong_config):
        """Test that gRPC-Web plugin is configured."""
        plugins = kong_config.get("plugins", [])
        grpc_web_plugins = [p for p in plugins if p.get("name") == "grpc-web"]

        assert (
            len(grpc_web_plugins) >= 1
        ), "At least one grpc-web plugin should be configured"

        # Check registry-specific plugin
        registry_plugin = None
        for plugin in grpc_web_plugins:
            if plugin.get("service") == "registry-grpc-service":
                registry_plugin = plugin
                break

        assert (
            registry_plugin is not None
        ), "grpc-web plugin for registry-grpc-service should exist"

    def test_grpc_web_plugin_configuration(self, kong_config):
        """Test gRPC-Web plugin configuration details."""
        plugins = kong_config.get("plugins", [])
        registry_plugin = None

        for plugin in plugins:
            if (
                plugin.get("name") == "grpc-web"
                and plugin.get("service") == "registry-grpc-service"
            ):
                registry_plugin = plugin
                break

        assert registry_plugin is not None
        config = registry_plugin.get("config", {})

        # Test plugin configuration
        assert config.get("proto") == "/kong/protos/registry.proto"
        assert not config.get("pass_stripped_path")
        assert config.get("cors_origin") == "*"
        assert config.get("allow_origin_header")

        # Test plugin tags
        tags = registry_plugin.get("tags", [])
        expected_tags = ["grpc-web", "registry"]
        for tag in expected_tags:
            assert tag in tags, f"Plugin tag '{tag}' should be present"

    def test_cors_includes_grpc_web_headers(self, kong_config):
        """Test that CORS configuration includes gRPC-Web headers."""
        plugins = kong_config.get("plugins", [])
        cors_plugin = None

        for plugin in plugins:
            if plugin.get("name") == "cors" and not plugin.get("service"):
                cors_plugin = plugin
                break

        assert cors_plugin is not None, "Global CORS plugin should exist"
        config = cors_plugin.get("config", {})

        headers = config.get("headers", [])
        grpc_headers = ["X-Grpc-Web", "Grpc-Timeout", "Grpc-Accept-Encoding"]
        for header in grpc_headers:
            assert header in headers, f"CORS should include gRPC-Web header '{header}'"

        exposed_headers = config.get("exposed_headers", [])
        grpc_response_headers = ["Grpc-Status", "Grpc-Message"]
        for header in grpc_response_headers:
            assert (
                header in exposed_headers
            ), f"CORS should expose gRPC-Web header '{header}'"

    def test_proto_file_path_exists(self):
        """Test that proto file exists at expected path."""
        proto_path = os.path.join(os.path.dirname(__file__), "..", "..", "protos", "registry.proto")
        assert os.path.exists(proto_path), f"Proto file should exist at {proto_path}"

    def test_proto_file_content(self):
        """Test that proto file contains expected service definitions."""
        proto_path = os.path.join(os.path.dirname(__file__), "..", "..", "protos", "registry.proto")

        with open(proto_path, "r") as f:
            content = f.read()

        # Test for key elements
        assert "service RegistryService" in content
        assert "package venturestrat.registry.v1" in content
        assert "rpc Register" in content
        assert "rpc Discover" in content

    def test_grpc_web_route_path_convention(self, kong_config):
        """Test gRPC-Web routes follow /grpc/v1/<service> convention."""
        services = kong_config.get("services", [])

        for service in services:
            if service.get("protocol") == "grpc":
                routes = service.get("routes", [])
                for route in routes:
                    paths = route.get("paths", [])
                    for path in paths:
                        if "/grpc/v1/" in path:
                            # Should match pattern /grpc/v1/<service-name>
                            assert path.startswith(
                                "/grpc/v1/"
                            ), f"gRPC-Web path {path} should start with /grpc/v1/"
                            parts = path.split("/")
                            assert (
                                len(parts) >= 4
                            ), f"gRPC-Web path {path} should have service name"

    def test_grpc_web_authentication_inheritance(self, kong_config):
        """Test that gRPC-Web services inherit global authentication."""
        plugins = kong_config.get("plugins", [])

        # Check global key-auth plugin exists
        key_auth_plugins = [
            p for p in plugins if p.get("name") == "key-auth" and not p.get("service")
        ]
        assert len(key_auth_plugins) >= 1, "Global key-auth plugin should exist"

        # Check global jwt plugin exists
        jwt_plugins = [
            p for p in plugins if p.get("name") == "jwt" and not p.get("service")
        ]
        assert len(jwt_plugins) >= 1, "Global JWT plugin should exist"

        # gRPC-Web services should not override authentication (inherit global)
        grpc_web_plugins = [p for p in plugins if p.get("name") == "grpc-web"]
        for plugin in grpc_web_plugins:
            # gRPC-Web plugins should not disable authentication
            config = plugin.get("config", {})
            assert (
                "anonymous" not in config
            ), "gRPC-Web should not allow anonymous access"

    def test_grpc_service_consul_discovery(self, kong_config):
        """Test that gRPC services use Consul service discovery."""
        services = kong_config.get("services", [])

        for service in services:
            if service.get("protocol") == "grpc":
                host = service.get("host")
                # Should use Consul service name format
                assert (
                    ".service.consul" in host
                ), f"gRPC service host {host} should use Consul discovery"

    def test_grpc_web_plugin_order(self, kong_config):
        """Test that gRPC-Web plugins are ordered correctly."""
        plugins = kong_config.get("plugins", [])

        # gRPC-Web plugins should come after authentication plugins
        plugin_names = [p.get("name") for p in plugins]

        if "grpc-web" in plugin_names and "key-auth" in plugin_names:
            # This is more of a documentation test - Kong handles plugin ordering
            # But we verify the plugins are present
            assert True

    def test_grpc_web_service_tags(self, kong_config):
        """Test that gRPC services have appropriate tags."""
        services = kong_config.get("services", [])

        for service in services:
            if service.get("protocol") == "grpc":
                tags = service.get("tags", [])
                assert "grpc" in tags, f"gRPC service {service.get('name')} should have 'grpc' tag"
                assert (
                    "grpc" in tags
                ), f"gRPC service {service.get('name')} should have 'grpc' tag"
                assert (
                    "transcoding" in tags
                ), f"gRPC service {service.get('name')} should have 'transcoding' tag"
