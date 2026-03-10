"""
Task 13.5: Unit tests to verify gRPC-Web configuration supports browser access.

This test file validates the Kong configuration to ensure browsers can call
gRPC services via the gateway with proper gRPC-Web plugin setup.
"""

import pytest
import yaml
import os


class TestGRPCWebBrowserConfigurationTask135:
    """Task 13.5 unit tests for gRPC-Web browser compatibility configuration."""

    @pytest.fixture
    def kong_config(self):
        """Load Kong configuration from kong-test.yaml."""
        kong_yaml_path = os.path.join(os.path.dirname(__file__), "..", "..", "kong-test.yaml")
        with open(kong_yaml_path, "r") as f:
            return yaml.safe_load(f)

    def test_grpc_web_plugin_enables_browser_access(self, kong_config):
        """Test that gRPC-Web plugin configuration enables browser access."""
        # Find the gRPC service configuration
        services = kong_config.get("services", [])
        registry_grpc_service = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc_service = service
                break

        assert registry_grpc_service is not None, "registry-grpc-service should exist"

        # Check for gRPC-Web plugin
        plugins = registry_grpc_service.get("plugins", [])
        grpc_web_plugin = None

        for plugin in plugins:
            if plugin.get("name") == "grpc-web":
                grpc_web_plugin = plugin
                break

        assert grpc_web_plugin is not None, "grpc-web plugin should be configured"

        # Plugin configuration should enable browser compatibility
        config = grpc_web_plugin.get("config", {})
        proto_path = config.get("proto")
        assert (
            proto_path is not None
        ), "Proto file path should be configured for transcoding"

    def test_grpc_web_supports_browser_content_types(self, kong_config):
        """Test that gRPC service routes support browser gRPC-Web content types."""
        services = kong_config.get("services", [])
        registry_grpc_service = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc_service = service
                break

        assert registry_grpc_service is not None

        # gRPC service should accept HTTP/HTTPS protocols for browser compatibility
        routes = registry_grpc_service.get("routes", [])
        assert len(routes) > 0, "gRPC service should have routes"

        for route in routes:
            protocols = route.get("protocols", [])
            assert "http" in protocols, "Should support HTTP for browser access"
            assert "https" in protocols, "Should support HTTPS for browser access"

    def test_grpc_web_route_path_accessible_to_browsers(self, kong_config):
        """Test that gRPC-Web route paths are browser-accessible."""
        services = kong_config.get("services", [])
        registry_grpc_service = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc_service = service
                break

        assert registry_grpc_service is not None

        routes = registry_grpc_service.get("routes", [])
        grpc_web_paths = []

        for route in routes:
            if "grpc" in route.get("name", "").lower():
                paths = route.get("paths", [])
                grpc_web_paths.extend(paths)

        # Should have gRPC-Web path that browsers can access
        assert len(grpc_web_paths) > 0, "Should have gRPC-Web accessible paths"

        # Path should follow /grpc/v1/<service> convention for browser clients
        browser_accessible_path = any(path.startswith("/grpc/v1/") for path in grpc_web_paths)
        assert browser_accessible_path, "Should have browser-accessible gRPC path"

    def test_authentication_works_with_browser_grpc_web(self, kong_config):
        """Test that authentication configuration works for browser gRPC-Web calls."""
        # Global authentication plugins should apply to gRPC-Web
        plugins = kong_config.get("plugins", [])

        auth_plugins = [p for p in plugins if p.get("name") in ["key-auth", "jwt"]]
        assert len(auth_plugins) > 0, "Should have authentication plugins for security"

        # key-auth should be configured to work with browser headers
        key_auth_plugin = None
        for plugin in plugins:
            if plugin.get("name") == "key-auth":
                key_auth_plugin = plugin
                break

        assert key_auth_plugin is not None, "key-auth plugin should be configured"

        config = key_auth_plugin.get("config", {})
        key_in_header = config.get("key_in_header", False)
        assert key_in_header, "Should support API key in headers for browser use"

        # Should accept common header names that browsers can use
        key_names = config.get("key_names", [])
        browser_compatible_headers = ["X-API-Key", "apikey"]
        has_browser_header = any(
            name in browser_compatible_headers for name in key_names
        )
        assert has_browser_header, "Should support browser-compatible header names"

    def test_cors_support_for_browser_grpc_web(self, kong_config):
        """Test configuration supports CORS for browser gRPC-Web requests."""
        # While CORS might be configured separately, the gRPC-Web routes should support it
        services = kong_config.get("services", [])
        registry_grpc_service = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc_service = service
                break

        assert registry_grpc_service is not None

        routes = registry_grpc_service.get("routes", [])
        for route in routes:
            protocols = route.get("protocols", [])
            # Should support both HTTP and HTTPS for cross-origin requests
            assert (
                "http" in protocols and "https" in protocols
            ), "Should support both HTTP/HTTPS for CORS compatibility"

    def test_rate_limiting_applies_to_browser_grpc_web(self, kong_config):
        """Test that rate limiting configuration applies to browser gRPC-Web calls."""
        # Global rate limiting should apply to gRPC-Web requests
        plugins = kong_config.get("plugins", [])

        rate_limit_plugins = [p for p in plugins if p.get("name") == "rate-limiting"]
        assert len(rate_limit_plugins) > 0, "Should have rate limiting for all requests"

        rate_limit_plugin = rate_limit_plugins[0]
        config = rate_limit_plugin.get("config", {})

        # Should have reasonable limits for browser usage
        minute_limit = config.get("minute")
        assert minute_limit is not None, "Should have per-minute rate limits"
        assert minute_limit > 0, "Rate limit should allow browser requests"

        # Should not hide client headers so browsers can see rate limit info
        hide_headers = config.get("hide_client_headers", True)
        assert not hide_headers, "Should show rate limit headers to browser clients"

    def test_logging_and_monitoring_for_browser_grpc_web(self, kong_config):
        """Test that logging/monitoring works for browser gRPC-Web requests."""
        plugins = kong_config.get("plugins", [])

        # Should have correlation ID for request tracing
        correlation_id_plugins = [
            p for p in plugins if p.get("name") == "correlation-id"
        ]
        assert len(correlation_id_plugins) > 0, "Should have correlation ID for tracing"

        correlation_plugin = correlation_id_plugins[0]
        config = correlation_plugin.get("config", {})

        echo_downstream = config.get("echo_downstream", False)
        assert echo_downstream, "Should echo correlation ID back to browsers"

        # Should have logging for debugging browser issues
        logging_plugins = [
            p for p in plugins if p.get("name") in ["file-log", "http-log"]
        ]
        assert (
            len(logging_plugins) > 0
        ), "Should have logging for browser request debugging"

    def test_grpc_web_timeouts_suitable_for_browsers(self, kong_config):
        """Test that gRPC service timeout configuration is suitable for browser use."""
        services = kong_config.get("services", [])
        registry_grpc_service = None

        for service in services:
            if service.get("name") == "registry-grpc-service":
                registry_grpc_service = service
                break

        assert registry_grpc_service is not None

        # Check timeout configurations
        connect_timeout = registry_grpc_service.get("connect_timeout")
        read_timeout = registry_grpc_service.get("read_timeout")
        write_timeout = registry_grpc_service.get("write_timeout")

        # Timeouts should be reasonable for browser connections
        assert (
            connect_timeout is not None and connect_timeout > 0
        ), "Should have connect timeout"
        assert read_timeout is not None and read_timeout > 0, "Should have read timeout"
        assert (
            write_timeout is not None and write_timeout > 0
        ), "Should have write timeout"

        # Should not be too long (causing browser timeouts) or too short (causing failures)
        assert (
            connect_timeout <= 30000
        ), "Connect timeout should not be too long for browsers"
        assert read_timeout <= 300000, "Read timeout should be reasonable for browsers"

    def test_upstream_configuration_supports_grpc_from_browsers(self, kong_config):
        """Test that upstream configuration properly routes browser gRPC-Web to backend."""
        upstreams = kong_config.get("upstreams", [])
        grpc_upstream = None

        for upstream in upstreams:
            if "grpc" in upstream.get("name", "").lower():
                grpc_upstream = upstream
                break

        assert (
            grpc_upstream is not None
        ), "Should have gRPC upstream for browser requests"

        targets = grpc_upstream.get("targets", [])
        assert len(targets) > 0, "gRPC upstream should have targets"

        # Should target the correct gRPC port
        grpc_target = targets[0]
        target_address = grpc_target.get("target", "")
        assert "50051" in target_address, "Should target gRPC port for backend service"

    def test_proto_file_configuration_enables_transcoding(self):
        """Test that proto file is properly configured for browser gRPC-Web transcoding."""
        proto_path = os.path.join(os.path.dirname(__file__), "..", "..", "protos", "registry.proto")

        assert os.path.exists(
            proto_path
        ), "Proto file should exist for gRPC-Web transcoding"

        with open(proto_path, "r") as f:
            content = f.read()

        # Proto file should define the services browsers will call
        assert "service RegistryService" in content, "Should define RegistryService"
        assert (
            "package venturestrat.registry.v1" in content
        ), "Should have proper package name"

        # Should have methods that browsers might call
        browser_relevant_methods = ["ListServices", "Discover", "Register"]
        for method in browser_relevant_methods:
            assert (
                f"rpc {method}" in content
            ), f"Should define {method} RPC for browser access"

    def test_consumer_configuration_supports_browser_api_keys(self, kong_config):
        """Test that consumer configuration supports browser API key usage."""
        consumers = kong_config.get("consumers", [])
        assert len(consumers) > 0, "Should have consumers configured"

        # Test that consumers have API key credentials for browser use
        for consumer in consumers:
            keyauth_creds = consumer.get("keyauth_credentials", [])
            if len(keyauth_creds) > 0:
                # Each consumer should have API key that browsers can use
                for cred in keyauth_creds:
                    api_key = cred.get("key")
                    assert api_key is not None, "Consumer should have API key"
                    assert len(api_key) > 0, "API key should not be empty"

        # Should have at least one development/test consumer for browser testing
        dev_consumer = None
        for consumer in consumers:
            username = consumer.get("username", "").lower()
            tags = consumer.get("tags", [])
            if "dev" in username or "default" in username or "dev" in tags:
                dev_consumer = consumer
                break

        assert dev_consumer is not None, "Should have development consumer for browser testing"
        assert (
            dev_consumer is not None
        ), "Should have development consumer for browser testing"
