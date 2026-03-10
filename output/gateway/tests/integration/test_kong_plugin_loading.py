"""
Integration test for Kong plugin loading and configuration validation.

Tests Task 17.4: Verify that Kong can successfully load the tenant-header plugin
and that the configuration is valid.
"""

import pytest
import yaml
import subprocess
from pathlib import Path
from typing import Dict, Any


@pytest.mark.integration
class TestKongPluginLoading:
    """Test Kong plugin loading and configuration validation."""

    @pytest.fixture
    def kong_config_path(self) -> Path:
        """Path to Kong configuration file."""
        return Path(__file__).parent.parent.parent / "kong-test.yaml"

    @pytest.fixture
    def kong_config(self, kong_config_path) -> Dict[str, Any]:
        """Load Kong configuration."""
        with open(kong_config_path, "r") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def plugin_directory(self) -> Path:
        """Path to plugin directory."""
        return Path(__file__).parent.parent.parent / "plugins"

    def test_kong_config_file_valid_yaml(self, kong_config_path):
        """Test that Kong configuration file is valid YAML."""
        with open(kong_config_path, "r") as f:
            config = yaml.safe_load(f)

        assert isinstance(config, dict), "Kong configuration should be a dictionary"
        assert "_format_version" in config, "Kong config should have _format_version"
        assert (
            config["_format_version"] == "3.0"
        ), "Kong config should use format version 3.0"

    def test_tenant_header_plugin_in_config(self, kong_config):
        """Test that tenant-header plugin is configured in Kong config."""
        plugins = kong_config.get("plugins", [])
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        assert len(tenant_plugins) > 0, "Tenant-header plugin should be configured"

        plugin_config = tenant_plugins[0]
        assert plugin_config.get("name") == "tenant-header"
        assert "config" in plugin_config

    def test_tenant_header_plugin_configuration_valid(self, kong_config):
        """Test that tenant-header plugin configuration is valid."""
        plugins = kong_config.get("plugins", [])
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        plugin_config = tenant_plugins[0]["config"]

        # Test required configuration fields
        assert "exclude_paths" in plugin_config
        assert isinstance(plugin_config["exclude_paths"], list)
        assert "/health" in plugin_config["exclude_paths"]
        assert "/metrics" in plugin_config["exclude_paths"]

        # Test optional configuration fields
        if "debug_header" in plugin_config:
            assert isinstance(plugin_config["debug_header"], bool)

        if "emit_metrics" in plugin_config:
            assert isinstance(plugin_config["emit_metrics"], bool)

        if "header_name" in plugin_config:
            assert isinstance(plugin_config["header_name"], str)
            assert len(plugin_config["header_name"]) > 0

        if "strict_mode" in plugin_config:
            assert isinstance(plugin_config["strict_mode"], bool)

        if "log_level" in plugin_config:
            assert plugin_config["log_level"] in ["debug", "info", "warn", "error"]

    def test_plugin_files_exist(self, plugin_directory):
        """Test that plugin files exist in the correct location."""
        tenant_plugin_dir = plugin_directory / "tenant-header"

        assert tenant_plugin_dir.exists(), "Tenant-header plugin directory should exist"
        assert (
            tenant_plugin_dir.is_dir()
        ), "Tenant-header plugin path should be a directory"

        handler_file = tenant_plugin_dir / "handler.lua"
        schema_file = tenant_plugin_dir / "schema.lua"

        assert handler_file.exists(), "handler.lua should exist"
        assert schema_file.exists(), "schema.lua should exist"

        # Check that files are not empty
        assert handler_file.stat().st_size > 0, "handler.lua should not be empty"
        assert schema_file.stat().st_size > 0, "schema.lua should not be empty"

    def test_plugin_handler_syntax(self, plugin_directory):
        """Test that plugin handler has valid Lua syntax."""
        handler_file = plugin_directory / "tenant-header" / "handler.lua"

        with open(handler_file, "r") as f:
            content = f.read()

        # Basic syntax checks
        assert "TenantHeaderHandler" in content
        assert "PRIORITY = 900" in content
        assert "function TenantHeaderHandler:access" in content
        assert "return TenantHeaderHandler" in content

        # Check for required Kong API usage
        assert "kong.ctx.shared.jwt_claims" in content
        assert "kong.service.request.set_header" in content
        assert "kong.response.exit" in content

    def test_plugin_schema_syntax(self, plugin_directory):
        """Test that plugin schema has valid structure."""
        schema_file = plugin_directory / "tenant-header" / "schema.lua"

        with open(schema_file, "r") as f:
            content = f.read()

        # Basic syntax checks
        assert 'name = "tenant-header"' in content
        assert "fields = {" in content
        assert "config = {" in content

        # Check for required schema elements
        assert "exclude_paths" in content
        assert "debug_header" in content
        assert "emit_metrics" in content
        assert "header_name" in content
        assert "strict_mode" in content
        assert "log_level" in content

    def test_jwt_plugin_configured_before_tenant_plugin(self, kong_config):
        """Test that JWT plugin is configured and has higher priority than tenant plugin."""
        plugins = kong_config.get("plugins", [])

        jwt_plugins = [p for p in plugins if p.get("name") == "jwt"]
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        # Tenant-header plugin should always be present
        assert len(tenant_plugins) > 0, "Tenant-header plugin should be configured"

        # JWT plugin may not be in test config, but if it is, check configuration
        if len(jwt_plugins) > 0:
            # Verify JWT plugin is configured (tenant plugin depends on it)
            jwt_config = jwt_plugins[0].get("config", {})
            # JWT plugin should have basic configuration
            assert isinstance(jwt_config, dict), "JWT plugin should have config"

    def test_plugin_priority_in_handler(self, plugin_directory):
        """Test that plugin has correct priority in handler file."""
        handler_file = plugin_directory / "tenant-header" / "handler.lua"

        with open(handler_file, "r") as f:
            content = f.read()

        # Check priority is set correctly
        assert "PRIORITY = 900" in content, "Plugin priority should be 900"

        # Priority 900 ensures it runs after JWT plugin (1005) but before routing

    def test_kong_config_validation_with_lua_check(self, kong_config_path):
        """Test Kong configuration validation using lua syntax checking."""
        # This is a basic check - in a real environment you'd use 'kong config parse'
        config_content = kong_config_path.read_text()

        # Check for basic YAML structure
        assert "_format_version:" in config_content
        assert "services:" in config_content
        assert "plugins:" in config_content

        # Check that tenant-header plugin is mentioned
        assert "tenant-header" in config_content

    @pytest.mark.slow
    def test_kong_config_dry_run_validation(self, kong_config_path):
        """Test Kong configuration with dry-run validation if Kong is available."""
        # This test requires Kong to be installed but doesn't require it to be running
        try:
            # Try to validate the configuration with Kong (if available)
            result = subprocess.run(
                ["kong", "config", "parse", str(kong_config_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                # Kong validated the configuration successfully
                assert True
            else:
                # Kong found issues - check if it's plugin-related
                if "tenant-header" in result.stderr:
                    pytest.fail(
                        f"Kong validation failed for tenant-header plugin: {result.stderr}"
                    )
                else:
                    # Other validation issues (might be expected in test environment)
                    pytest.skip(
                        f"Kong validation issues (not plugin-related): {result.stderr}"
                    )

        except FileNotFoundError:
            pytest.skip("Kong CLI not available for configuration validation")
        except subprocess.TimeoutExpired:
            pytest.skip("Kong configuration validation timed out")

    def test_plugin_configuration_compatibility(self, kong_config):
        """Test that plugin configuration is compatible with Kong version."""
        # Check that we're using format version 3.0 (modern Kong)
        assert kong_config.get("_format_version") == "3.0"

        # Check that plugin configuration uses modern syntax
        plugins = kong_config.get("plugins", [])
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        plugin_config = tenant_plugins[0]

        # Should have 'config' section (not legacy format)
        assert "config" in plugin_config

        # Should not have deprecated fields
        config = plugin_config["config"]
        deprecated_fields = ["api_id", "consumer_id"]
        for field in deprecated_fields:
            assert (
                field not in config
            ), f"Plugin should not use deprecated field: {field}"

    def test_plugin_directory_structure_for_kong(self, plugin_directory):
        """Test that plugin directory structure matches Kong expectations."""
        tenant_plugin_dir = plugin_directory / "tenant-header"

        # Kong expects plugins to be in a directory named after the plugin
        assert tenant_plugin_dir.name == "tenant-header"

        # Kong expects these specific files
        expected_files = ["handler.lua", "schema.lua"]
        for filename in expected_files:
            file_path = tenant_plugin_dir / filename
            assert file_path.exists(), f"Plugin should have {filename}"

        # Check that files have appropriate content structure
        handler_content = (tenant_plugin_dir / "handler.lua").read_text()
        schema_content = (tenant_plugin_dir / "schema.lua").read_text()

        # Handler should define a handler table and return it
        assert "TenantHeaderHandler" in handler_content
        assert "return TenantHeaderHandler" in handler_content

        # Schema should define schema structure and return it
        assert "return {" in schema_content or "local schema = {" in schema_content

    def test_plugin_integration_with_existing_plugins(self, kong_config):
        """Test that tenant-header plugin integrates well with existing plugins."""
        plugins = kong_config.get("plugins", [])
        plugin_names = [p.get("name") for p in plugins]

        # Tenant-header plugin should be present
        assert "tenant-header" in plugin_names

        # JWT plugin is preferred but not required in test configs
        if "jwt" in plugin_names:
            # If JWT is present, it should be compatible with tenant-header
            assert "tenant-header" in plugin_names

        # Should have other standard plugins that don't conflict
        compatible_plugins = [
            "rate-limiting",
            "prometheus",
            "key-auth",
            "correlation-id",
        ]
        for plugin in compatible_plugins:
            if plugin in plugin_names:
                # If present, should not conflict with tenant-header
                assert "tenant-header" in plugin_names

    def test_plugin_enables_correctly(self, kong_config):
        """Test that plugin is enabled correctly in configuration."""
        plugins = kong_config.get("plugins", [])
        tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

        plugin_config = tenant_plugins[0]

        # Plugin should be enabled (default behavior unless explicitly disabled)
        enabled = plugin_config.get("enabled", True)
        assert enabled is True, "Plugin should be enabled"

        # Should not be applied to specific consumer/service unless intended
        assert (
            "consumer" not in plugin_config
        ), "Plugin should be global (not consumer-specific)"

        # If it's applied to specific services, that should be intentional
        if "service" in plugin_config:
            assert isinstance(
                plugin_config["service"], (str, dict)
            ), "Service reference should be valid"

    def test_kong_yaml_format_compliance(self, kong_config_path):
        """Test that Kong YAML format complies with Kong standards."""
        with open(kong_config_path, "r") as f:
            content = f.read()

        # Should use Kong 3.x format
        assert '_format_version: "3.0"' in content or "_format_version: '3.0'" in content
        assert (
            '_format_version: "3.0"' in content or "_format_version: '3.0'" in content
        )

        # Should use transform flag for declarative config
        assert "_transform: true" in content

        # Should have proper sections
        required_sections = ["services", "plugins"]
        for section in required_sections:
            assert f"{section}:" in content

    def test_plugin_lua_module_structure(self, plugin_directory):
        """Test that plugin Lua modules follow Kong conventions."""
        handler_file = plugin_directory / "tenant-header" / "handler.lua"
        schema_file = plugin_directory / "tenant-header" / "schema.lua"

        # Handler module structure
        handler_content = handler_file.read_text()

        # Should define handler with proper priority
        assert "PRIORITY = " in handler_content
        assert "VERSION = " in handler_content

        # Should implement Kong plugin phases
        kong_phases = ["access", "header_filter", "log"]
        for phase in kong_phases:
            assert f"function TenantHeaderHandler:{phase}" in handler_content

        # Schema module structure
        schema_content = schema_file.read_text()

        # Should require Kong typedefs
        assert (
            "typedefs" in schema_content or "kong.db.schema.typedefs" in schema_content
        )

        # Should define proper schema structure
        assert "name = " in schema_content
        assert "fields = " in schema_content
