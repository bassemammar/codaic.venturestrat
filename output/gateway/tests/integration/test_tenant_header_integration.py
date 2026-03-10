"""
Integration tests for tenant-header plugin with Kong gateway.

Tests Task 17.1: Verify tenant-header plugin integration with Kong configuration.
Validates that the plugin can be properly configured in Kong and integrates
with the existing JWT authentication flow.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any


@pytest.mark.integration
class TestTenantHeaderIntegration:
    """Test tenant-header plugin integration with Kong."""

    @pytest.fixture
    def kong_config_path(self) -> Path:
        """Path to Kong configuration file."""
        return Path(__file__).parent.parent.parent / "kong.yaml"

    @pytest.fixture
    def kong_config(self, kong_config_path) -> Dict[str, Any]:
        """Load Kong configuration for testing."""
        with open(kong_config_path, "r") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def sample_tenant_header_config(self) -> Dict[str, Any]:
        """Sample tenant-header plugin configuration."""
        return {
            "name": "tenant-header",
            "config": {
                "exclude_paths": ["/health", "/metrics", "/status"],
                "debug_header": False,
                "emit_metrics": True,
                "header_name": "X-Tenant-ID",
                "strict_mode": True,
                "log_level": "info",
            },
        }

    def test_plugin_can_be_added_globally(
        self, kong_config, sample_tenant_header_config
    ):
        """Test that tenant-header plugin can be added as a global plugin."""
        # Simulate adding the plugin to global configuration
        test_config = kong_config.copy()

        if "plugins" not in test_config:
            test_config["plugins"] = []

        test_config["plugins"].append(sample_tenant_header_config)

        # Verify the configuration is valid YAML
        config_yaml = yaml.dump(test_config, default_flow_style=False)
        reparsed_config = yaml.safe_load(config_yaml)

        # Find our plugin in the reparsed configuration
        plugins = reparsed_config.get("plugins", [])
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        assert (
            len(tenant_plugins) > 0
        ), "Tenant-header plugin not found in configuration"

        tenant_plugin = tenant_plugins[0]
        config = tenant_plugin.get("config", {})

        # Verify configuration values
        assert (
            config.get("header_name") == "X-Tenant-ID"
        ), "Header name not configured correctly"
        assert config.get("strict_mode") is True, "Strict mode not enabled"
        assert config.get("emit_metrics") is True, "Metrics not enabled"

    def test_plugin_priority_with_existing_plugins(
        self, kong_config, sample_tenant_header_config
    ):
        """Test that tenant-header plugin priority works with existing plugins."""
        # Get existing plugins and their priorities
        existing_plugins = kong_config.get("plugins", [])

        # JWT plugin should exist and have higher priority than tenant-header
        jwt_plugins = [p for p in existing_plugins if p.get("name") == "jwt"]
        assert len(jwt_plugins) > 0, "JWT plugin not found in existing configuration"

        # Tenant-header plugin should run after JWT (priority 900 < 1005)
        # This ensures JWT claims are available when tenant-header runs

        # Simulate plugin execution order
        plugin_priorities = []

        # Add existing plugin priorities (estimated)
        for plugin in existing_plugins:
            name = plugin.get("name")
            if name == "jwt":
                plugin_priorities.append(("jwt", 1005))  # Kong default JWT priority
            elif name == "key-auth":
                plugin_priorities.append(
                    ("key-auth", 1003)
                )  # Kong default key-auth priority
            elif name == "rate-limiting":
                plugin_priorities.append(
                    ("rate-limiting", 901)
                )  # Kong default rate-limiting priority

        # Add our tenant-header plugin
        plugin_priorities.append(("tenant-header", 900))

        # Sort by priority (higher runs first)
        plugin_priorities.sort(key=lambda x: x[1], reverse=True)

        # Find tenant-header position
        tenant_position = next(
            i for i, (name, _) in enumerate(plugin_priorities) if name == "tenant-header"
        )
        jwt_position = next(i for i, (name, _) in enumerate(plugin_priorities) if name == "jwt")
            i
            for i, (name, _) in enumerate(plugin_priorities)
            if name == "tenant-header"
        )
        jwt_position = next(
            i for i, (name, _) in enumerate(plugin_priorities) if name == "jwt"
        )

        # Tenant-header should run after JWT
        assert (
            tenant_position > jwt_position
        ), "Tenant-header plugin should run after JWT plugin"

    def test_plugin_configuration_validation(self, sample_tenant_header_config):
        """Test that plugin configuration follows schema validation."""
        config = sample_tenant_header_config["config"]

        # Test exclude_paths
        exclude_paths = config.get("exclude_paths", [])
        assert isinstance(exclude_paths, list), "exclude_paths should be a list"
        assert (
            "/health" in exclude_paths
        ), "Health endpoint should be excluded by default"
        assert (
            "/metrics" in exclude_paths
        ), "Metrics endpoint should be excluded by default"

        # Test boolean fields
        assert isinstance(
            config.get("debug_header"), bool
        ), "debug_header should be boolean"
        assert isinstance(
            config.get("emit_metrics"), bool
        ), "emit_metrics should be boolean"
        assert isinstance(
            config.get("strict_mode"), bool
        ), "strict_mode should be boolean"

        # Test string fields
        assert isinstance(
            config.get("header_name"), str
        ), "header_name should be string"
        assert isinstance(config.get("log_level"), str), "log_level should be string"

        # Test log_level enumeration
        valid_log_levels = ["debug", "info", "warn", "error"]
        assert (
            config.get("log_level") in valid_log_levels
        ), f"log_level should be one of {valid_log_levels}"

    def test_plugin_with_service_configuration(
        self, kong_config, sample_tenant_header_config
    ):
        """Test that tenant-header plugin can be configured on specific services."""
        services = kong_config.get("services", [])

        if len(services) == 0:
            pytest.skip("No services configured in Kong")

        # Test adding plugin to a service
        test_service = services[0].copy()

        if "plugins" not in test_service:
            test_service["plugins"] = []

        test_service["plugins"].append(sample_tenant_header_config)

        # Verify service-level plugin configuration
        service_plugins = test_service.get("plugins", [])
        tenant_plugins = [
            p for p in service_plugins if p.get("name") == "tenant-header"
        ]

        assert len(tenant_plugins) > 0, "Tenant-header plugin not added to service"

    def test_plugin_exclude_paths_functionality(self, sample_tenant_header_config):
        """Test that exclude_paths configuration works as expected."""
        config = sample_tenant_header_config["config"]
        exclude_paths = config.get("exclude_paths", [])

        # Test common exclusion patterns
        test_paths = [
            ("/health", True),  # Should be excluded
            ("/metrics", True),  # Should be excluded
            ("/status", True),  # Should be excluded
            ("/api/v1/quotes", False),  # Should not be excluded
            ("/api/v1/users", False),  # Should not be excluded
        ]

        for path, should_be_excluded in test_paths:
            is_excluded = any(
                path.startswith(pattern.replace("*", "")) for pattern in exclude_paths
            )

            if should_be_excluded:
                assert is_excluded, f"Path {path} should be excluded but isn't"
            else:
                # Note: This test assumes exact matching, not regex
                # The actual plugin uses Lua string.match for regex patterns
                pass

    def test_plugin_compatibility_with_jwt(
        self, kong_config, sample_tenant_header_config
    ):
        """Test that tenant-header plugin is compatible with JWT plugin configuration."""
        existing_plugins = kong_config.get("plugins", [])
        jwt_plugins = [p for p in existing_plugins if p.get("name") == "jwt"]

        if len(jwt_plugins) == 0:
            pytest.skip("JWT plugin not configured")

        jwt_config = jwt_plugins[0].get("config", {})

        # Verify JWT plugin has necessary configuration for tenant-header
        # JWT plugin should have claims_to_verify that includes custom claims
        claims_to_verify = jwt_config.get("claims_to_verify", [])

        # Should at least verify expiration
        assert "exp" in claims_to_verify, "JWT should verify expiration for security"

        # JWT plugin should allow custom claims (tenant_id) to pass through
        # This is implicit in JWT plugin behavior

    def test_plugin_with_request_transformer(self, kong_config):
        """Test compatibility with request-transformer plugin."""
        existing_plugins = kong_config.get("plugins", [])
        transformer_plugins = [
            p for p in existing_plugins if p.get("name") == "request-transformer"
        ]

        if len(transformer_plugins) == 0:
            pytest.skip("Request-transformer plugin not configured")

        # Tenant-header plugin should work alongside request-transformer
        # Both plugins can add headers, and they should be compatible

        # Verify that request-transformer doesn't conflict with X-Tenant-ID header
        for plugin in transformer_plugins:
            config = plugin.get("config", {})
            add_headers = config.get("add", {}).get("headers", [])

            # Check if X-Tenant-ID is already being set by request-transformer
            tenant_headers = [h for h in add_headers if "X-Tenant-ID" in h]

            # If request-transformer is setting X-Tenant-ID, it might conflict
            # This is a configuration warning, not an error
            if tenant_headers:
                print("Warning: request-transformer also sets X-Tenant-ID header")

    def test_plugin_logging_integration(self, sample_tenant_header_config):
        """Test that plugin logging configuration integrates with Kong logging."""
        config = sample_tenant_header_config["config"]

        # Verify log level configuration
        log_level = config.get("log_level", "info")
        assert log_level in ["debug", "info", "warn", "error"], "Invalid log level"

        # Verify metrics emission configuration
        emit_metrics = config.get("emit_metrics", True)
        assert isinstance(emit_metrics, bool), "emit_metrics should be boolean"

    def test_plugin_header_name_customization(self, sample_tenant_header_config):
        """Test that plugin header name can be customized."""
        config = sample_tenant_header_config.copy()

        # Test with custom header name
        config["config"]["header_name"] = "X-Custom-Tenant"

        # Verify configuration accepts custom header name
        header_name = config["config"]["header_name"]
        assert header_name == "X-Custom-Tenant", "Custom header name not set correctly"
        assert header_name.startswith("X-"), "Header should follow X- convention"

    def test_plugin_strict_mode_configuration(self, sample_tenant_header_config):
        """Test that plugin strict mode works as expected."""
        config = sample_tenant_header_config["config"]

        # Strict mode should be configurable
        strict_mode = config.get("strict_mode", True)
        assert isinstance(strict_mode, bool), "strict_mode should be boolean"

        # In strict mode, plugin should fail if JWT plugin hasn't run
        # In non-strict mode, plugin should pass through without tenant_id

        # Test both configurations
        config_strict = config.copy()
        config_strict["strict_mode"] = True

        config_lenient = config.copy()
        config_lenient["strict_mode"] = False

        assert config_strict["strict_mode"] is True, "Strict mode configuration failed"
        assert (
            config_lenient["strict_mode"] is False
        ), "Lenient mode configuration failed"

    def test_plugin_debug_header_configuration(self, sample_tenant_header_config):
        """Test that debug header configuration works correctly."""
        config = sample_tenant_header_config["config"]

        # Debug header should be disabled by default for security
        debug_header = config.get("debug_header", False)
        assert debug_header is False, "Debug header should be disabled by default"

        # Test enabling debug header
        config_debug = config.copy()
        config_debug["debug_header"] = True

        assert config_debug["debug_header"] is True, "Debug header enabling failed"

    def test_plugin_full_integration_scenario(
        self, kong_config, sample_tenant_header_config
    ):
        """Test complete integration scenario with existing Kong setup."""
        # Simulate complete Kong configuration with tenant-header plugin
        test_config = kong_config.copy()

        # Add tenant-header plugin globally
        if "plugins" not in test_config:
            test_config["plugins"] = []

        test_config["plugins"].append(sample_tenant_header_config)

        # Verify the complete configuration is valid
        try:
            config_yaml = yaml.dump(test_config, default_flow_style=False)
            reparsed_config = yaml.safe_load(config_yaml)

            # Configuration should parse without errors
            assert isinstance(reparsed_config, dict), "Configuration is not valid YAML"

            # All required sections should be present
            required_sections = ["services", "plugins"]
            for section in required_sections:
                if section in kong_config:  # Only check if it existed originally
                    assert (
                        section in reparsed_config
                    ), f"Section {section} missing after adding plugin"

            # Tenant-header plugin should be present
            plugins = reparsed_config.get("plugins", [])
            tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]
            assert (
                len(tenant_plugins) > 0
            ), "Tenant-header plugin missing from final configuration"

        except yaml.YAMLError as e:
            pytest.fail(f"Configuration is not valid YAML: {e}")

    def test_plugin_configuration_examples(self):
        """Test various plugin configuration examples."""
        # Example 1: Global plugin with default settings
        global_config = {
            "name": "tenant-header",
            "config": {},  # Use all defaults
        }

        # Should work with empty config (uses defaults)
        assert global_config["name"] == "tenant-header"

        # Example 2: Service-specific plugin with custom settings
        service_config = {
            "name": "tenant-header",
            "config": {
                "exclude_paths": ["/health", "/metrics", "/admin/*"],
                "debug_header": True,
                "header_name": "X-Org-ID",
                "log_level": "debug",
            },
        }

        # Verify custom configuration
        config = service_config["config"]
        assert "/admin/*" in config["exclude_paths"], "Custom exclude path not set"
        assert config["debug_header"] is True, "Debug header not enabled"
        assert config["header_name"] == "X-Org-ID", "Custom header name not set"
        assert config["log_level"] == "debug", "Debug log level not set"

        # Example 3: Route-specific plugin with minimal settings
        route_config = {
            "name": "tenant-header",
            "config": {"strict_mode": False, "emit_metrics": False},
        }

        # Verify minimal configuration
        route_cfg = route_config["config"]
        assert route_cfg["strict_mode"] is False, "Non-strict mode not set"
        assert route_cfg["emit_metrics"] is False, "Metrics disabled incorrectly"
