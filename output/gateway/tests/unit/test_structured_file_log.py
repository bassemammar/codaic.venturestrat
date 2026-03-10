"""
Unit tests for structured file-log plugin configuration.

Tests the file-log plugin configuration in kong.yaml to ensure it provides
structured output with correlation ID and consumer information.
"""

import pytest
from typing import Dict, Any


@pytest.mark.unit
class TestStructuredFileLogConfiguration:
    """Test suite for structured file-log plugin configuration."""

    def test_file_log_plugin_present(self, gateway_config: Dict[str, Any]):
        """Test that file-log plugin is configured."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

    def test_file_log_basic_configuration(self, gateway_config: Dict[str, Any]):
        """Test basic file-log plugin configuration."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        config = file_log_plugin.get("config", {})

        # Basic configuration checks
        assert "path" in config, "file-log plugin should specify output path"
        assert config["path"] == "/dev/stdout", "Logs should go to stdout"

        assert "reopen" in config, "file-log plugin should specify reopen behavior"
        assert config["reopen"] is True, "Log file should reopen on rotation"

    def test_file_log_structured_output_configuration(
        self, gateway_config: Dict[str, Any]
    ):
        """Test that file-log plugin has structured output configuration."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        config = file_log_plugin.get("config", {})

        # Check for structured output configuration
        assert (
            "custom_fields_by_lua" in config
        ), "file-log plugin should have custom_fields_by_lua for structured output"

    def test_file_log_correlation_id_field(self, gateway_config: Dict[str, Any]):
        """Test that file-log includes correlation ID in structured output."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        config = file_log_plugin.get("config", {})
        custom_fields = config.get("custom_fields_by_lua", {})

        assert (
            "correlation_id" in custom_fields
        ), "Structured logs should include correlation_id field"

        # Verify the lua expression for correlation ID
        correlation_id_expr = custom_fields["correlation_id"]
        assert (
            "correlation_id" in correlation_id_expr
        ), "Correlation ID expression should reference correlation_id"
        assert (
            "http_x_correlation_id" in correlation_id_expr
        ), "Correlation ID expression should fallback to header"

    def test_file_log_consumer_fields(self, gateway_config: Dict[str, Any]):
        """Test that file-log includes consumer information in structured output."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        config = file_log_plugin.get("config", {})
        custom_fields = config.get("custom_fields_by_lua", {})

        # Check consumer-related fields
        consumer_fields = ["consumer_id", "consumer_username", "auth_method"]

        for field in consumer_fields:
            assert field in custom_fields, f"Structured logs should include {field} field"
            assert (
                field in custom_fields
            ), f"Structured logs should include {field} field"

    def test_file_log_service_and_route_fields(self, gateway_config: Dict[str, Any]):
        """Test that file-log includes service and route information."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        config = file_log_plugin.get("config", {})
        custom_fields = config.get("custom_fields_by_lua", {})

        # Check service and route fields
        routing_fields = ["service_name", "route_name"]

        for field in routing_fields:
            assert field in custom_fields, f"Structured logs should include {field} field"

            # Verify the expression uses kong.router
            field_expr = custom_fields[field]
            assert "kong.router" in field_expr, f"{field} expression should use kong.router API"
            assert (
                field in custom_fields
            ), f"Structured logs should include {field} field"

            # Verify the expression uses kong.router
            field_expr = custom_fields[field]
            assert (
                "kong.router" in field_expr
            ), f"{field} expression should use kong.router API"

    def test_file_log_performance_metrics_fields(self, gateway_config: Dict[str, Any]):
        """Test that file-log includes performance metrics."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        config = file_log_plugin.get("config", {})
        custom_fields = config.get("custom_fields_by_lua", {})

        # Check performance metric fields
        performance_fields = [
            "request_size",
            "response_size",
            "request_time",
            "upstream_response_time",
        ]

        for field in performance_fields:
            assert field in custom_fields, f"Structured logs should include {field} field"
            assert (
                field in custom_fields
            ), f"Structured logs should include {field} field"

    def test_file_log_request_context_fields(self, gateway_config: Dict[str, Any]):
        """Test that file-log includes request context information."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        config = file_log_plugin.get("config", {})
        custom_fields = config.get("custom_fields_by_lua", {})

        # Check request context fields
        context_fields = ["upstream_status", "client_ip", "user_agent"]

        for field in context_fields:
            assert field in custom_fields, f"Structured logs should include {field} field"
            assert (
                field in custom_fields
            ), f"Structured logs should include {field} field"

    def test_file_log_auth_method_detection(self, gateway_config: Dict[str, Any]):
        """Test that auth_method field correctly detects authentication type."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        config = file_log_plugin.get("config", {})
        custom_fields = config.get("custom_fields_by_lua", {})

        auth_method_expr = custom_fields.get("auth_method", "")

        # Should check for API key authentication
        assert (
            "authenticated_consumer" in auth_method_expr
        ), "Auth method should detect API key authentication"

        # Should check for JWT authentication
        assert "jwt" in auth_method_expr.lower(), "Auth method should detect JWT authentication"

        # Should have fallback to anonymous
        assert "anonymous" in auth_method_expr, "Auth method should have anonymous fallback"
        assert (
            "jwt" in auth_method_expr.lower()
        ), "Auth method should detect JWT authentication"

        # Should have fallback to anonymous
        assert (
            "anonymous" in auth_method_expr
        ), "Auth method should have anonymous fallback"

    def test_file_log_client_ip_detection(self, gateway_config: Dict[str, Any]):
        """Test that client_ip field uses Kong's forwarded IP detection."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        config = file_log_plugin.get("config", {})
        custom_fields = config.get("custom_fields_by_lua", {})

        client_ip_expr = custom_fields.get("client_ip", "")

        # Should use Kong's get_forwarded_ip for proper X-Forwarded-For handling
        assert (
            "kong.client.get_forwarded_ip" in client_ip_expr
        ), "Client IP should use Kong's forwarded IP detection"

    def test_file_log_lua_expressions_syntax(self, gateway_config: Dict[str, Any]):
        """Test that all Lua expressions have valid return statements."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        config = file_log_plugin.get("config", {})
        custom_fields = config.get("custom_fields_by_lua", {})

        # All lua expressions should start with "return"
        for field_name, expression in custom_fields.items():
            assert expression.strip().startswith(
                "return"
            ), f"Lua expression for {field_name} should start with 'return'"

            # Should not be empty
            assert (
                len(expression.strip()) > 6
            ), f"Lua expression for {field_name} should not be empty"

    def test_file_log_global_plugin_scope(self, gateway_config: Dict[str, Any]):
        """Test that file-log plugin is globally scoped."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        # Global plugins should not have service, route, or consumer scope
        assert "service" not in file_log_plugin, "file-log should be globally scoped (no service)"
        assert "route" not in file_log_plugin, "file-log should be globally scoped (no route)"
        assert "consumer" not in file_log_plugin, "file-log should be globally scoped (no consumer)"
        assert (
            "service" not in file_log_plugin
        ), "file-log should be globally scoped (no service)"
        assert (
            "route" not in file_log_plugin
        ), "file-log should be globally scoped (no route)"
        assert (
            "consumer" not in file_log_plugin
        ), "file-log should be globally scoped (no consumer)"

    def test_file_log_minimal_required_fields(self, gateway_config: Dict[str, Any]):
        """Test that all required fields for structured logging are present."""
        plugins = gateway_config.get("plugins", [])
        file_log_plugin = next((p for p in plugins if p.get("name") == "file-log"), None)
        file_log_plugin = next(
            (p for p in plugins if p.get("name") == "file-log"), None
        )

        assert file_log_plugin is not None, "file-log plugin should be configured"

        config = file_log_plugin.get("config", {})
        custom_fields = config.get("custom_fields_by_lua", {})

        # Minimum required fields for task 11.5 verification
        required_fields = [
            "correlation_id",  # For request tracing
            "consumer_id",  # For consumer identification
            "consumer_username",  # For consumer identification
            "auth_method",  # For authentication tracking
        ]

        for field in required_fields:
            assert (
                field in custom_fields
            ), f"Required field {field} missing from structured log configuration"
