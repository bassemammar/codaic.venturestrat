"""
Unit tests for tenant-header plugin configuration.

Tests Task 17.1: Verify tenant-header plugin design and configuration.
Validates that the tenant-header plugin is properly structured to extract
tenant_id from JWT claims and add X-Tenant-ID header for downstream services.
"""

import pytest
from pathlib import Path


@pytest.mark.unit
class TestTenantHeaderPlugin:
    """Test tenant-header plugin implementation."""

    @pytest.fixture
    def plugin_handler_path(self) -> Path:
        """Path to the tenant-header plugin handler."""
        return (
            Path(__file__).parent.parent.parent
            / "plugins"
            / "tenant-header"
            / "handler.lua"
        )

    @pytest.fixture
    def plugin_schema_path(self) -> Path:
        """Path to the tenant-header plugin schema."""
        return (
            Path(__file__).parent.parent.parent
            / "plugins"
            / "tenant-header"
            / "schema.lua"
        )

    def test_plugin_handler_exists(self, plugin_handler_path):
        """Test that the plugin handler file exists."""
        assert (
            plugin_handler_path.exists()
        ), f"Plugin handler not found at {plugin_handler_path}"
        assert plugin_handler_path.is_file(), "Plugin handler is not a file"

    def test_plugin_schema_exists(self, plugin_schema_path):
        """Test that the plugin schema file exists."""
        assert (
            plugin_schema_path.exists()
        ), f"Plugin schema not found at {plugin_schema_path}"
        assert plugin_schema_path.is_file(), "Plugin schema is not a file"

    def test_handler_structure(self, plugin_handler_path):
        """Test that the handler has the correct structure."""
        with open(plugin_handler_path, "r") as f:
            content = f.read()

        # Check for required handler structure
        assert "TenantHeaderHandler" in content, "Handler table not found"
        assert (
            "PRIORITY = 900" in content
        ), "Priority not set correctly (should be 900, after auth)"
        assert "VERSION" in content, "Version not specified"

        # Check for required functions
        assert "function TenantHeaderHandler:access" in content, "access function not found"
        assert (
            "function TenantHeaderHandler:access" in content
        ), "access function not found"
        assert (
            "function TenantHeaderHandler:header_filter" in content
        ), "header_filter function not found"
        assert "function TenantHeaderHandler:log" in content, "log function not found"

        # Check for return statement
        assert "return TenantHeaderHandler" in content, "Handler not returned"

    def test_handler_jwt_claims_extraction(self, plugin_handler_path):
        """Test that handler extracts tenant_id from JWT claims."""
        with open(plugin_handler_path, "r") as f:
            content = f.read()

        # Check for JWT claims access
        assert "kong.ctx.shared.jwt_claims" in content, "JWT claims not accessed"
        assert (
            "jwt_claims.tenant_id" in content
        ), "tenant_id not extracted from JWT claims"

        # Check for header setting
        assert (
            "kong.service.request.set_header" in content
        ), "Request header not being set"
        assert "X-Tenant-ID" in content, "X-Tenant-ID header not configured"

    def test_handler_path_exclusion(self, plugin_handler_path):
        """Test that handler supports path exclusion."""
        with open(plugin_handler_path, "r") as f:
            content = f.read()

        # Check for path exclusion logic
        assert "exclude_paths" in content, "Path exclusion not implemented"
        assert "kong.request.get_path()" in content, "Request path not being checked"
        assert (
            "string.match(path, pattern)" in content
        ), "Pattern matching not implemented"

    def test_handler_error_responses(self, plugin_handler_path):
        """Test that handler returns appropriate error responses."""
        with open(plugin_handler_path, "r") as f:
            content = f.read()

        # Check for error response when no tenant_id
        assert "kong.response.exit(401" in content, "401 error response not configured"
        assert "missing_tenant" in content, "Error code not specified"
        assert (
            "Token must contain tenant_id claim" in content
        ), "Error message not specified"

    def test_handler_logging(self, plugin_handler_path):
        """Test that handler includes proper logging."""
        with open(plugin_handler_path, "r") as f:
            content = f.read()

        # Check for logging
        assert "kong.log.debug" in content, "Debug logging not implemented"
        assert "kong.log.warn" in content, "Warning logging not implemented"
        assert "kong.ctx.plugin.tenant_id" in content, "Tenant context not stored"

    def test_schema_structure(self, plugin_schema_path):
        """Test that the schema has the correct structure."""
        with open(plugin_schema_path, "r") as f:
            content = f.read()

        # Check for schema table
        assert 'name = "tenant-header"' in content, "Plugin name not set"
        assert "fields = {" in content, "Fields not defined"
        assert (
            "consumer = typedefs.no_consumer" in content
        ), "Consumer configuration not disabled"
        assert (
            "protocols = typedefs.protocols_http" in content
        ), "Protocols not restricted to HTTP"

    def test_schema_configuration_fields(self, plugin_schema_path):
        """Test that the schema includes required configuration fields."""
        with open(plugin_schema_path, "r") as f:
            content = f.read()

        # Check for exclude_paths configuration
        assert "exclude_paths" in content, "exclude_paths field not defined"
        assert 'type = "array"' in content, "exclude_paths not configured as array"
        assert "/health" in content, "Default health path not excluded"
        assert "/metrics" in content, "Default metrics path not excluded"

        # Check for debug_header configuration
        assert "debug_header" in content, "debug_header field not defined"
        assert 'type = "boolean"' in content, "debug_header not configured as boolean"

        # Check for emit_metrics configuration
        assert "emit_metrics" in content, "emit_metrics field not defined"

        # Check for header_name configuration
        assert "header_name" in content, "header_name field not defined"
        assert "X-Tenant-ID" in content, "Default header name not set"

    def test_plugin_directory_structure(self):
        """Test that the plugin directory structure is correct."""
        plugin_dir = Path(__file__).parent.parent.parent / "plugins" / "tenant-header"

        assert plugin_dir.exists(), "Plugin directory does not exist"
        assert plugin_dir.is_dir(), "Plugin path is not a directory"

        # Check for required files
        handler_file = plugin_dir / "handler.lua"
        schema_file = plugin_dir / "schema.lua"

        assert handler_file.exists(), "handler.lua not found in plugin directory"
        assert schema_file.exists(), "schema.lua not found in plugin directory"

    def test_handler_priority_configuration(self, plugin_handler_path):
        """Test that handler priority is set correctly."""
        with open(plugin_handler_path, "r") as f:
            content = f.read()

        # Priority should be 900 (after JWT auth at 1005, before routing)
        assert "PRIORITY = 900" in content, "Priority not set to 900"

    def test_handler_metrics_support(self, plugin_handler_path):
        """Test that handler supports metrics emission."""
        with open(plugin_handler_path, "r") as f:
            content = f.read()

        # Check for metrics in log phase
        assert "emit_metrics" in content, "Metrics emission not supported"
        assert "tenant_requests" in content, "Tenant request metric not configured"
        assert "kong.log.inspect" in content, "Metrics logging not implemented"

    def test_handler_debug_header_support(self, plugin_handler_path):
        """Test that handler supports debug headers."""
        with open(plugin_handler_path, "r") as f:
            content = f.read()

        # Check for debug header in header_filter phase
        assert "debug_header" in content, "Debug header not supported"
        assert "X-Debug-Tenant-ID" in content, "Debug header name not configured"
        assert "kong.response.set_header" in content, "Response header not being set"

    def test_schema_default_values(self, plugin_schema_path):
        """Test that schema has appropriate default values."""
        with open(plugin_schema_path, "r") as f:
            content = f.read()

        # Check default values
        assert "default = false" in content, "debug_header should default to false"
        assert "default = true" in content, "emit_metrics should default to true"
        assert 'default = "X-Tenant-ID"' in content, "header_name should default to X-Tenant-ID"
        assert (
            'default = "X-Tenant-ID"' in content
        ), "header_name should default to X-Tenant-ID"

    def test_schema_validation_rules(self, plugin_schema_path):
        """Test that schema includes validation rules."""
        with open(plugin_schema_path, "r") as f:
            content = f.read()

        # Check for proper field types
        assert 'type = "string"' in content, "String type validation not configured"
        assert 'type = "boolean"' in content, "Boolean type validation not configured"
        assert 'type = "array"' in content, "Array type validation not configured"

        # Check for enumeration validation
        assert "one_of = {" in content, "Enumeration validation not configured"
        assert 'debug", "info", "warn", "error' in content, "Log level enumeration not complete"
        assert (
            'debug", "info", "warn", "error' in content
        ), "Log level enumeration not complete"

    def test_handler_context_management(self, plugin_handler_path):
        """Test that handler properly manages context."""
        with open(plugin_handler_path, "r") as f:
            content = f.read()

        # Check for context storage and retrieval
        assert "kong.ctx.plugin.tenant_id" in content, "Plugin context not managed"
        assert (
            "kong.log.set_serialize_value" in content
        ), "Log serialization not configured"

    def test_plugin_configuration_completeness(
        self, plugin_handler_path, plugin_schema_path
    ):
        """Test that plugin configuration is complete."""
        # Handler must exist and be readable
        with open(plugin_handler_path, "r") as f:
            handler_content = f.read()

        # Schema must exist and be readable
        with open(plugin_schema_path, "r") as f:
            schema_content = f.read()

        # Handler must have all phases implemented
        phases = ["access", "header_filter", "log"]
        for phase in phases:
            assert (
                f"function TenantHeaderHandler:{phase}" in handler_content
            ), f"Phase {phase} not implemented in handler"

        # Schema must define plugin name and configuration
        assert "tenant-header" in schema_content, "Plugin name not defined in schema"
        assert "config" in schema_content, "Configuration not defined in schema"

        # Files must not be empty
        assert len(handler_content.strip()) > 0, "Handler file is empty"
        assert len(schema_content.strip()) > 0, "Schema file is empty"

    def test_error_handling_completeness(self, plugin_handler_path):
        """Test that error handling is comprehensive."""
        with open(plugin_handler_path, "r") as f:
            content = f.read()

        # Should handle missing JWT claims
        assert (
            "jwt_claims and jwt_claims.tenant_id" in content
        ), "Missing JWT claims not handled"

        # Should handle excluded paths gracefully
        assert "return" in content, "Path exclusion doesn't return properly"

        # Should provide meaningful error messages
        error_messages = ["missing_tenant", "Token must contain tenant_id claim"]
        for msg in error_messages:
            assert msg in content, f"Error message '{msg}' not found"

    def test_plugin_integration_ready(self):
        """Test that plugin is ready for Kong integration."""
        plugin_dir = Path(__file__).parent.parent.parent / "plugins" / "tenant-header"

        # Directory structure should be correct for Kong
        assert plugin_dir.exists(), "Plugin directory does not exist"

        required_files = ["handler.lua", "schema.lua"]
        for file_name in required_files:
            file_path = plugin_dir / file_name
            assert file_path.exists(), f"Required file {file_name} not found"

            # Files should not be empty
            with open(file_path, "r") as f:
                content = f.read().strip()
                assert len(content) > 0, f"File {file_name} is empty"
