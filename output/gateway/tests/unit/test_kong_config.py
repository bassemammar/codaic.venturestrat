"""
Unit tests for Kong configuration validation.

Tests the kong.yaml file for syntax, structure, and logical consistency.
"""

import pytest
from typing import Dict, Any


@pytest.mark.unit
class TestKongConfiguration:
    """Test suite for Kong declarative configuration."""

    def test_kong_yaml_valid_syntax(self, gateway_config: Dict[str, Any]):
        """Test that kong.yaml parses as valid YAML."""
        assert gateway_config is not None
        assert isinstance(gateway_config, dict)

    def test_kong_yaml_format_version(self, gateway_config: Dict[str, Any]):
        """Test that kong.yaml has correct format version."""
        assert gateway_config.get("_format_version") == "3.0"

    def test_transform_enabled(self, gateway_config: Dict[str, Any]):
        """Test that transformation is enabled."""
        assert gateway_config.get("_transform") is True

    def test_services_have_routes(self, gateway_config: Dict[str, Any]):
        """Test that all services have at least one route."""
        services = gateway_config.get("services", [])
        assert len(services) > 0, "At least one service should be configured"

        for service in services:
            assert (
                "routes" in service
            ), f"Service '{service.get('name')}' missing routes"
            assert (
                len(service["routes"]) > 0
            ), f"Service '{service.get('name')}' has no routes"

    def test_routes_have_paths(self, gateway_config: Dict[str, Any]):
        """Test that all routes have path configuration."""
        services = gateway_config.get("services", [])

        for service in services:
            for route in service.get("routes", []):
                assert "paths" in route, f"Route '{route.get('name')}' missing paths"
                paths = route["paths"]
                assert isinstance(
                    paths, list
                ), f"Route '{route.get('name')}' paths should be a list"
                assert len(paths) > 0, f"Route '{route.get('name')}' has no paths"

    def test_plugins_valid_names(self, gateway_config: Dict[str, Any]):
        """Test that all plugin names are valid Kong plugins."""
        # Known Kong plugins used in our configuration
        valid_plugins = {
            "key-auth",
            "rate-limiting",
            "file-log",
            "prometheus",
            "correlation-id",
            "cors",
            "grpc-web",
            "request-transformer",
            "jwt",
        }

        plugins = gateway_config.get("plugins", [])
        for plugin in plugins:
            plugin_name = plugin.get("name")
            assert plugin_name in valid_plugins, f"Unknown plugin: {plugin_name}"

    def test_consumers_have_credentials(self, gateway_config: Dict[str, Any]):
        """Test that all consumers have authentication credentials."""
        consumers = gateway_config.get("consumers", [])
        assert len(consumers) > 0, "At least one consumer should be configured"

        for consumer in consumers:
            username = consumer.get("username")
            assert username, f"Consumer missing username: {consumer}"

            # Check for at least one type of credential
            # Anonymous consumers don't need credentials
            if "anonymous" in consumer.get("tags", []):
                continue

            has_credentials = any(
                [
                    "keyauth_credentials" in consumer,
                    "jwt_secrets" in consumer,  # Updated from jwt_credentials to jwt_secrets
                    "jwt_secrets"
                    in consumer,  # Updated from jwt_credentials to jwt_secrets
                    "basic_credentials" in consumer,
                ]
            )
            assert has_credentials, f"Consumer '{username}' has no credentials"

    def test_upstreams_have_targets(self, gateway_config: Dict[str, Any]):
        """Test that all upstreams have at least one target."""
        upstreams = gateway_config.get("upstreams", [])

        for upstream in upstreams:
            upstream_name = upstream.get("name")
            assert "targets" in upstream, f"Upstream '{upstream_name}' missing targets"

            targets = upstream["targets"]
            assert len(targets) > 0, f"Upstream '{upstream_name}' has no targets"

            for target in targets:
                assert (
                    "target" in target
                ), f"Target in '{upstream_name}' missing target field"
                assert "weight" in target, f"Target in '{upstream_name}' missing weight"

    def test_required_services_present(self, gateway_config: Dict[str, Any]):
        """Test that required services are configured."""
        services = gateway_config.get("services", [])
        service_names = [service.get("name") for service in services]

        required_services = ["registry-service"]
        for required in required_services:
            assert required in service_names, f"Required service '{required}' not found"

    def test_required_routes_present(self, gateway_config: Dict[str, Any]):
        """Test that required routes are configured."""
        services = gateway_config.get("services", [])
        all_routes = []

        for service in services:
            for route in service.get("routes", []):
                all_routes.append(route.get("name"))

        required_routes = ["registry-rest", "health-check"]
        for required in required_routes:
            assert required in all_routes, f"Required route '{required}' not found"

    def test_consumer_api_keys_format(self, gateway_config: Dict[str, Any]):
        """Test that consumer API keys follow expected format."""
        consumers = gateway_config.get("consumers", [])

        for consumer in consumers:
            if "keyauth_credentials" in consumer:
                credentials = consumer["keyauth_credentials"]
                for cred in credentials:
                    api_key = cred.get("key")
                    assert (
                        api_key
                    ), f"Consumer '{consumer.get('username')}' has empty API key"
                    assert len(api_key) >= 10, f"API key too short: {api_key}"

    def test_health_check_configuration(self, gateway_config: Dict[str, Any]):
        """Test that health check service is properly configured."""
        services = gateway_config.get("services", [])
        health_service = next((s for s in services if s.get("name") == "health-service"), None)
        health_service = next(
            (s for s in services if s.get("name") == "health-service"), None
        )

        assert health_service, "Health check service not found"
        assert "url" in health_service, "Health service missing URL"

        # Check health route
        routes = health_service.get("routes", [])
        health_route = next((r for r in routes if r.get("name") == "health-check"), None)
        health_route = next(
            (r for r in routes if r.get("name") == "health-check"), None
        )

        assert health_route, "Health check route not found"
        assert "/health" in health_route.get("paths", []), "Health path not configured"

    def test_cors_configuration(self, gateway_config: Dict[str, Any]):
        """Test that CORS is properly configured."""
        plugins = gateway_config.get("plugins", [])
        cors_plugin = next((p for p in plugins if p.get("name") == "cors"), None)

        assert cors_plugin, "CORS plugin not found"

        config = cors_plugin.get("config", {})
        assert "origins" in config, "CORS origins not configured"
        assert "methods" in config, "CORS methods not configured"
        assert "headers" in config, "CORS headers not configured"

        # Verify essential headers are allowed
        headers = config.get("headers", [])
        essential_headers = ["Content-Type", "Authorization", "X-API-Key"]
        for header in essential_headers:
            assert header in headers, f"Essential CORS header missing: {header}"

    def test_rate_limiting_configuration(self, gateway_config: Dict[str, Any]):
        """Test that rate limiting is properly configured."""
        plugins = gateway_config.get("plugins", [])
        rate_limit_plugin = next((p for p in plugins if p.get("name") == "rate-limiting"), None)
        rate_limit_plugin = next(
            (p for p in plugins if p.get("name") == "rate-limiting"), None
        )

        assert rate_limit_plugin, "Rate limiting plugin not found"

        config = rate_limit_plugin.get("config", {})
        assert "minute" in config, "Rate limit minute not configured"
        assert "policy" in config, "Rate limit policy not configured"
        assert config["policy"] == "redis", "Rate limit should use Redis"
        assert "redis_host" in config, "Redis host not configured"

    def test_prometheus_metrics_configuration(self, gateway_config: Dict[str, Any]):
        """Test that Prometheus metrics are properly configured."""
        plugins = gateway_config.get("plugins", [])
        prometheus_plugin = next((p for p in plugins if p.get("name") == "prometheus"), None)
        prometheus_plugin = next(
            (p for p in plugins if p.get("name") == "prometheus"), None
        )

        assert prometheus_plugin, "Prometheus plugin not found"

        config = prometheus_plugin.get("config", {})
        assert (
            config.get("per_consumer") is True
        ), "Per-consumer metrics should be enabled"
        assert (
            config.get("status_code_metrics") is True
        ), "Status code metrics should be enabled"
        assert (
            config.get("latency_metrics") is True
        ), "Latency metrics should be enabled"

    def test_grpc_web_plugin_configuration(self, gateway_config: Dict[str, Any]):
        """Test that gRPC-Web plugin is properly configured."""
        plugins = gateway_config.get("plugins", [])
        grpc_web_plugin = next((p for p in plugins if p.get("name") == "grpc-web"), None)
        grpc_web_plugin = next(
            (p for p in plugins if p.get("name") == "grpc-web"), None
        )

        assert grpc_web_plugin, "gRPC-Web plugin not found"
        assert "service" in grpc_web_plugin, "gRPC-Web plugin should specify service"
        assert (
            grpc_web_plugin.get("service") == "registry-grpc-service"
        ), "gRPC-Web should target registry gRPC service"

    def test_upstream_healthcheck_configuration(self, gateway_config: Dict[str, Any]):
        """Test that upstreams have proper health check configuration."""
        upstreams = gateway_config.get("upstreams", [])

        for upstream in upstreams:
            upstream_name = upstream.get("name")
            if "healthchecks" in upstream:
                healthchecks = upstream["healthchecks"]
                assert (
                    "active" in healthchecks
                ), f"Upstream '{upstream_name}' missing active health checks"

                active = healthchecks["active"]
                assert "type" in active, f"Upstream '{upstream_name}' missing health check type"
                assert (
                    "type" in active
                ), f"Upstream '{upstream_name}' missing health check type"
                assert (
                    "http_path" in active
                ), f"Upstream '{upstream_name}' missing health check path"

    def test_service_protocol_configuration(self, gateway_config: Dict[str, Any]):
        """Test that services have proper protocol configuration."""
        services = gateway_config.get("services", [])

        for service in services:
            service_name = service.get("name")

            # Services can be defined with either protocol+host+port or url
            if "url" in service:
                # URL-based service definition (like health-service)
                url = service.get("url")
                assert url.startswith(
                    ("http://", "https://", "grpc://", "grpcs://")
                ), f"Service '{service_name}' has invalid URL protocol: {url}"
            else:
                # Protocol-based service definition
                assert (
                    "protocol" in service
                ), f"Service '{service_name}' missing protocol"
                protocol = service.get("protocol")
                valid_protocols = ["http", "https", "grpc", "grpcs"]
                assert (
                    protocol in valid_protocols
                ), f"Service '{service_name}' has invalid protocol: {protocol}"

    def test_route_protocols_configuration(self, gateway_config: Dict[str, Any]):
        """Test that routes have proper protocol configuration."""
        services = gateway_config.get("services", [])

        for service in services:
            for route in service.get("routes", []):
                route_name = route.get("name")
                assert "protocols" in route, f"Route '{route_name}' missing protocols"

                protocols = route.get("protocols", [])
                assert isinstance(
                    protocols, list
                ), f"Route '{route_name}' protocols should be a list"
                assert len(protocols) > 0, f"Route '{route_name}' has no protocols"

                valid_protocols = ["http", "https", "grpc", "grpcs", "tcp", "tls"]
                for protocol in protocols:
                    assert (
                        protocol in valid_protocols
                    ), f"Route '{route_name}' has invalid protocol: {protocol}"

    def test_consumer_tier_configuration(self, gateway_config: Dict[str, Any]):
        """Test that consumer tiers are properly configured with different rate limits."""
        consumers = gateway_config.get("consumers", [])

        # Find tier consumers
        tier_consumers = [c for c in consumers if "tier" in c.get("username", "")]
        assert (
            len(tier_consumers) >= 2
        ), "Should have at least two tier consumers configured"

        # Check for rate limit differences between tiers
        rate_limits = {}
        for consumer in consumers:
            username = consumer.get("username")
            plugins = consumer.get("plugins", [])
            rate_plugin = next(
                (p for p in plugins if p.get("name") == "rate-limiting"), None
            )
            if rate_plugin:
                config = rate_plugin.get("config", {})
                rate_limits[username] = config.get("minute", 0)

        # Verify different tiers have different limits
        if "free-tier-consumer" in rate_limits and "standard-tier-consumer" in rate_limits:
            assert (
                rate_limits["free-tier-consumer"] < rate_limits["standard-tier-consumer"]
        if (
            "free-tier-consumer" in rate_limits
            and "standard-tier-consumer" in rate_limits
        ):
            assert (
                rate_limits["free-tier-consumer"]
                < rate_limits["standard-tier-consumer"]
            ), "Free tier should have lower rate limits than standard tier"

    def test_correlation_id_plugin_configuration(self, gateway_config: Dict[str, Any]):
        """Test that correlation ID plugin is properly configured."""
        plugins = gateway_config.get("plugins", [])
        correlation_plugin = next((p for p in plugins if p.get("name") == "correlation-id"), None)
        correlation_plugin = next(
            (p for p in plugins if p.get("name") == "correlation-id"), None
        )

        assert correlation_plugin, "Correlation ID plugin not found"

        config = correlation_plugin.get("config", {})
        assert "header_name" in config, "Correlation ID header name not configured"
        assert (
            config.get("header_name") == "X-Correlation-ID"
        ), "Wrong correlation ID header name"
        assert "generator" in config, "Correlation ID generator not configured"
        assert (
            config.get("echo_downstream") is True
        ), "Correlation ID echo downstream should be enabled"

    def test_key_auth_plugin_configuration(self, gateway_config: Dict[str, Any]):
        """Test that key-auth plugin is properly configured."""
        plugins = gateway_config.get("plugins", [])
        key_auth_plugin = next((p for p in plugins if p.get("name") == "key-auth"), None)
        key_auth_plugin = next(
            (p for p in plugins if p.get("name") == "key-auth"), None
        )

        assert key_auth_plugin, "Key-auth plugin not found"

        config = key_auth_plugin.get("config", {})
        assert "key_names" in config, "Key names not configured"

        key_names = config.get("key_names", [])
        assert "X-API-Key" in key_names, "X-API-Key should be in key names"
        assert "apikey" in key_names, "apikey should be in key names"
        assert (
            config.get("hide_credentials") is True
        ), "Credentials should be hidden from upstream"

    def test_file_log_plugin_configuration(self, gateway_config: Dict[str, Any]):
        """Test that file-log plugin is properly configured."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin, "File-log plugin not found"

        config = file_log_plugin.get("config", {})
        assert "path" in config, "Log path not configured"
        assert config.get("path") == "/dev/stdout", "Log should go to stdout"

    def test_request_transformer_plugin_configuration(
        self, gateway_config: Dict[str, Any]
    ):
        """Test that request-transformer plugin is properly configured."""
        plugins = gateway_config.get("plugins", [])
        transformer_plugin = next(
            (p for p in plugins if p.get("name") == "request-transformer" and "service" in p),
            (
                p
                for p in plugins
                if p.get("name") == "request-transformer" and "service" in p
            ),
            None,
        )

        if transformer_plugin:  # Only test if present
            config = transformer_plugin.get("config", {})
            assert "add" in config, "Request transformer should add headers"
            add_config = config.get("add", {})
            assert "headers" in add_config, "Request transformer should add headers"

    def test_service_timeouts_configuration(self, gateway_config: Dict[str, Any]):
        """Test that services have proper timeout configuration."""
        services = gateway_config.get("services", [])

        for service in services:
            service_name = service.get("name")
            # Check if timeout fields are present and reasonable
            if "connect_timeout" in service:
                connect_timeout = service.get("connect_timeout")
                assert isinstance(
                    connect_timeout, int
                ), f"Service '{service_name}' connect_timeout should be integer"
                assert (
                    1000 <= connect_timeout <= 30000
                ), f"Service '{service_name}' connect_timeout should be 1-30 seconds"

            if "read_timeout" in service:
                read_timeout = service.get("read_timeout")
                assert isinstance(
                    read_timeout, int
                ), f"Service '{service_name}' read_timeout should be integer"
                assert (
                    5000 <= read_timeout <= 300000
                ), f"Service '{service_name}' read_timeout should be 5-300 seconds"

    def test_redis_configuration_consistency(self, gateway_config: Dict[str, Any]):
        """Test that Redis configuration is consistent across all plugins."""
        plugins = gateway_config.get("plugins", [])
        redis_configs = []

        for plugin in plugins:
            config = plugin.get("config", {})
            if "redis_host" in config:
                redis_configs.append(
                    {
                        "plugin": plugin.get("name"),
                        "host": config.get("redis_host"),
                        "port": config.get("redis_port", 6379),
                    }
                )

        if redis_configs:
            # All Redis configurations should be the same
            first_config = redis_configs[0]
            for config in redis_configs[1:]:
                assert (
                    config["host"] == first_config["host"]
                ), f"Redis host mismatch in {config['plugin']}"
                assert (
                    config["port"] == first_config["port"]
                ), f"Redis port mismatch in {config['plugin']}"

    def test_no_duplicate_routes_paths(self, gateway_config: Dict[str, Any]):
        """Test that no two routes have conflicting paths."""
        services = gateway_config.get("services", [])
        all_paths = []

        for service in services:
            for route in service.get("routes", []):
                route_name = route.get("name")
                paths = route.get("paths", [])
                for path in paths:
                    all_paths.append((path, route_name))

        # Check for exact duplicates
        path_counts = {}
        for path, route_name in all_paths:
            if path in path_counts:
                path_counts[path].append(route_name)
            else:
                path_counts[path] = [route_name]

        for path, routes in path_counts.items():
            if len(routes) > 1:
                # Allow if different protocols, but warn about potential conflicts
                assert False, f"Path '{path}' is used by multiple routes: {routes}"

    def test_consumer_tags_configuration(self, gateway_config: Dict[str, Any]):
        """Test that consumers have proper tags for organization."""
        consumers = gateway_config.get("consumers", [])

        for consumer in consumers:
            username = consumer.get("username")
            assert "tags" in consumer, f"Consumer '{username}' should have tags"

            tags = consumer.get("tags", [])
            assert isinstance(
                tags, list
            ), f"Consumer '{username}' tags should be a list"
            assert len(tags) > 0, f"Consumer '{username}' should have at least one tag"

    def test_plugin_scope_consistency(self, gateway_config: Dict[str, Any]):
        """Test that plugins have consistent scope configuration."""
        plugins = gateway_config.get("plugins", [])

        # Global plugins should not have service/route/consumer scope
        global_plugins = [
            p for p in plugins if "service" not in p and "route" not in p and "consumer" not in p
            p
            for p in plugins
            if "service" not in p and "route" not in p and "consumer" not in p
        ]
        service_plugins = [p for p in plugins if "service" in p]

        # Verify global plugins don't reference services
        for plugin in global_plugins:
            plugin_name = plugin.get("name")
            assert (
                "service" not in plugin
            ), f"Global plugin '{plugin_name}' should not reference service"
            assert (
                "route" not in plugin
            ), f"Global plugin '{plugin_name}' should not reference route"

        # Verify service plugins reference valid services
        services = gateway_config.get("services", [])
        service_names = [s.get("name") for s in services]

        for plugin in service_plugins:
            plugin_name = plugin.get("name")
            referenced_service = plugin.get("service")
            assert (
                referenced_service in service_names
            ), f"Plugin '{plugin_name}' references unknown service '{referenced_service}'"

    def test_jwt_claims_forwarding_configuration(self, gateway_config: Dict[str, Any]):
        """Test that JWT claims forwarding is properly configured."""
        plugins = gateway_config.get("plugins", [])

        # Find JWT plugin
        jwt_plugin = None
        for plugin in plugins:
            if plugin.get("name") == "jwt":
                jwt_plugin = plugin
                break

        assert jwt_plugin is not None, "JWT plugin should be configured"

        # Find request-transformer plugin that handles JWT claims forwarding
        transformer_plugin = None
        for plugin in plugins:
            if plugin.get("name") == "request-transformer" and "service" not in plugin:
                # Global request transformer
                transformer_plugin = plugin
                break

        assert (
            transformer_plugin is not None
        ), "Global request-transformer plugin should be configured"

        # Verify JWT claims headers are configured
        config = transformer_plugin.get("config", {})
        add_config = config.get("add", {})
        headers = add_config.get("headers", [])

        # Expected JWT claims headers
        expected_jwt_headers = [
            "X-JWT-Sub:",
            "X-JWT-Issuer:",
            "X-JWT-Audience:",
            "X-JWT-ID:",
            "X-JWT-Type:",
            "X-JWT-Scope:",
            "X-JWT-Issued-At:",
            "X-JWT-Expires-At:",
            "X-Auth-Method:",
        ]

        # Check that JWT claims forwarding headers are present
        jwt_headers_found = []
        for header in headers:
            for expected in expected_jwt_headers:
                if header.startswith(expected):
                    jwt_headers_found.append(expected)
                    break

        assert (
            len(jwt_headers_found) >= 8
        ), f"Missing JWT claims forwarding headers. Found: {jwt_headers_found}, Expected: {expected_jwt_headers}"

        # Verify JWT plugin configuration
        jwt_config = jwt_plugin.get("config", {})

        # Should have anonymous fallback configured
        assert "anonymous" in jwt_config, "JWT plugin should have anonymous fallback"

        # Should verify expiration
        claims_to_verify = jwt_config.get("claims_to_verify", [])
        assert "exp" in claims_to_verify, "JWT plugin should verify expiration claim"
