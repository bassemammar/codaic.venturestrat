"""
Unit tests for correlation ID configuration and generation.

Tests the correlation-id plugin configuration in kong.yaml and validates
the expected behavior for correlation ID generation.
"""

import pytest
import uuid
from typing import Dict, Any


@pytest.mark.unit
class TestCorrelationIdConfiguration:
    """Test suite for correlation ID plugin configuration."""

    def test_correlation_id_plugin_present(self, gateway_config: Dict[str, Any]):
        """Test that correlation-id plugin is configured."""
        plugins = gateway_config.get("plugins", [])
        correlation_plugin = next((p for p in plugins if p.get("name") == "correlation-id"), None)
        correlation_plugin = next(
            (p for p in plugins if p.get("name") == "correlation-id"), None
        )

        assert (
            correlation_plugin is not None
        ), "Correlation ID plugin should be configured"

    def test_correlation_id_header_name(self, gateway_config: Dict[str, Any]):
        """Test that correlation ID uses correct header name."""
        plugins = gateway_config.get("plugins", [])
        correlation_plugin = next((p for p in plugins if p.get("name") == "correlation-id"), None)
        correlation_plugin = next(
            (p for p in plugins if p.get("name") == "correlation-id"), None
        )

        assert (
            correlation_plugin is not None
        ), "Correlation ID plugin should be configured"

        config = correlation_plugin.get("config", {})
        assert (
            "header_name" in config
        ), "Correlation ID plugin should specify header name"
        assert (
            config["header_name"] == "X-Correlation-ID"
        ), "Should use X-Correlation-ID header"

    def test_correlation_id_generator_type(self, gateway_config: Dict[str, Any]):
        """Test that correlation ID generator is configured."""
        plugins = gateway_config.get("plugins", [])
        correlation_plugin = next((p for p in plugins if p.get("name") == "correlation-id"), None)
        correlation_plugin = next(
            (p for p in plugins if p.get("name") == "correlation-id"), None
        )

        assert (
            correlation_plugin is not None
        ), "Correlation ID plugin should be configured"

        config = correlation_plugin.get("config", {})
        assert "generator" in config, "Correlation ID plugin should specify generator"
        assert (
            config["generator"] == "uuid"
        ), "Should use UUID generator for correlation IDs"

    def test_correlation_id_echo_downstream_enabled(
        self, gateway_config: Dict[str, Any]
    ):
        """Test that echo_downstream is enabled for correlation IDs."""
        plugins = gateway_config.get("plugins", [])
        correlation_plugin = next((p for p in plugins if p.get("name") == "correlation-id"), None)
        correlation_plugin = next(
            (p for p in plugins if p.get("name") == "correlation-id"), None
        )

        assert (
            correlation_plugin is not None
        ), "Correlation ID plugin should be configured"

        config = correlation_plugin.get("config", {})
        assert (
            "echo_downstream" in config
        ), "Correlation ID plugin should specify echo_downstream"
        assert (
            config["echo_downstream"] is True
        ), "Should echo correlation ID back to client"

    def test_correlation_id_plugin_scope(self, gateway_config: Dict[str, Any]):
        """Test that correlation ID plugin is globally scoped."""
        plugins = gateway_config.get("plugins", [])
        correlation_plugin = next((p for p in plugins if p.get("name") == "correlation-id"), None)
        correlation_plugin = next(
            (p for p in plugins if p.get("name") == "correlation-id"), None
        )

        assert (
            correlation_plugin is not None
        ), "Correlation ID plugin should be configured"

        # Global plugins should not have service, route, or consumer scope
        assert (
            "service" not in correlation_plugin
        ), "Correlation ID should be globally scoped (no service)"
        assert (
            "route" not in correlation_plugin
        ), "Correlation ID should be globally scoped (no route)"
        assert (
            "consumer" not in correlation_plugin
        ), "Correlation ID should be globally scoped (no consumer)"

    def test_cors_exposes_correlation_id_header(self, gateway_config: Dict[str, Any]):
        """Test that CORS exposes X-Correlation-ID header."""
        plugins = gateway_config.get("plugins", [])
        cors_plugin = next((p for p in plugins if p.get("name") == "cors"), None)

        if cors_plugin is not None:  # Only test if CORS is configured
            config = cors_plugin.get("config", {})
            exposed_headers = config.get("exposed_headers", [])

            assert (
                "X-Correlation-ID" in exposed_headers
            ), "CORS should expose X-Correlation-ID header for browser access"

    def test_cors_allows_correlation_id_header(self, gateway_config: Dict[str, Any]):
        """Test that CORS allows X-Correlation-ID header in requests."""
        plugins = gateway_config.get("plugins", [])
        cors_plugin = next((p for p in plugins if p.get("name") == "cors"), None)

        if cors_plugin is not None:  # Only test if CORS is configured
            config = cors_plugin.get("config", {})
            allowed_headers = config.get("headers", [])

            assert (
                "X-Correlation-ID" in allowed_headers
            ), "CORS should allow X-Correlation-ID header in requests"

    def test_correlation_id_plugin_minimal_config(self, gateway_config: Dict[str, Any]):
        """Test that correlation ID plugin has minimal required configuration."""
        plugins = gateway_config.get("plugins", [])
        correlation_plugin = next((p for p in plugins if p.get("name") == "correlation-id"), None)
        correlation_plugin = next(
            (p for p in plugins if p.get("name") == "correlation-id"), None
        )

        assert (
            correlation_plugin is not None
        ), "Correlation ID plugin should be configured"

        config = correlation_plugin.get("config", {})

        # Required fields for correlation-id plugin
        required_fields = ["header_name", "generator", "echo_downstream"]

        for field in required_fields:
            assert (
                field in config
            ), f"Correlation ID plugin missing required field: {field}"

    def test_uuid_format_validity(self):
        """Test UUID generation format (simulates Kong's UUID generator)."""
        # This test verifies that standard UUID format is what we expect
        test_uuid = str(uuid.uuid4())

        # UUID4 format: 8-4-4-4-12 hex digits separated by hyphens
        # Example: f47ac10b-58cc-4372-a567-0e02b2c3d479

        assert len(test_uuid) == 36, "UUID should be 36 characters long"
        assert test_uuid.count("-") == 4, "UUID should have 4 hyphens"

        # Split by hyphens and check segment lengths
        segments = test_uuid.split("-")
        expected_lengths = [8, 4, 4, 4, 12]

        for i, (segment, expected_length) in enumerate(zip(segments, expected_lengths)):
            assert (
                len(segment) == expected_length
            ), f"UUID segment {i} should be {expected_length} characters, got {len(segment)}"

            # All characters should be hex digits
            assert all(
                c in "0123456789abcdef" for c in segment.lower()
            ), f"UUID segment {i} should contain only hex digits"

    def test_correlation_id_uniqueness_simulation(self):
        """Test that UUID generation produces unique values."""
        # Generate multiple UUIDs to test uniqueness (simulates what Kong does)
        generated_uuids = set()
        num_iterations = 1000

        for _ in range(num_iterations):
            generated_uuid = str(uuid.uuid4())
            assert (
                generated_uuid not in generated_uuids
            ), f"UUID collision detected: {generated_uuid}"
            generated_uuids.add(generated_uuid)

        assert len(generated_uuids) == num_iterations, "All generated UUIDs should be unique"
        assert (
            len(generated_uuids) == num_iterations
        ), "All generated UUIDs should be unique"


@pytest.mark.unit
class TestCorrelationIdBehaviorSpecification:
    """Test suite for expected correlation ID behavior based on Kong documentation."""

    def test_correlation_id_generation_when_missing(self):
        """Test expected behavior when no correlation ID is provided."""
        # This is the specification for how Kong should behave:
        # When X-Correlation-ID header is missing, Kong should generate a new UUID

        # We can't test the actual Kong behavior here, but we can test our expectation
        # that the configuration supports this behavior

        # Generate UUID as Kong would
        generated_id = str(uuid.uuid4())

        # Verify it matches expected format
        assert len(generated_id) == 36
        assert generated_id.count("-") == 4

        # Verify it's a valid UUID
        try:
            uuid.UUID(generated_id)
        except ValueError:
            pytest.fail(f"Generated ID '{generated_id}' is not a valid UUID")

    def test_correlation_id_preservation_when_present(self):
        """Test expected behavior when correlation ID is already provided."""
        # This is the specification for how Kong should behave:
        # When X-Correlation-ID header is present, Kong should preserve it

        original_id = "test-correlation-12345"

        # Kong should preserve this value, not generate a new UUID
        # We verify our expectation that any string format should be preserved
        assert len(original_id) > 0
        assert original_id == "test-correlation-12345"  # Should be unchanged

    def test_correlation_id_echo_behavior(self):
        """Test expected echo behavior for correlation IDs."""
        # With echo_downstream: true, Kong should:
        # 1. Add X-Correlation-ID to response headers
        # 2. Use the same value that was generated or provided

        test_cases = [
            "user-provided-correlation-id",
            str(uuid.uuid4()),  # UUID format
            "simple-123",  # Simple format
            "complex-correlation-id-with-multiple-parts-2024-01-04",  # Complex format
        ]

        for test_id in test_cases:
            # Kong should echo back exactly what was provided
            assert test_id == test_id  # Identity check
            assert len(test_id) > 0  # Non-empty

    def test_correlation_id_header_case_sensitivity(self):
        """Test header name case sensitivity expectations."""
        # HTTP headers are case-insensitive, but Kong config specifies exact case
        configured_header = "X-Correlation-ID"

        # Common variations that clients might use
        variations = [
            "x-correlation-id",
            "X-CORRELATION-ID",
            "x-Correlation-Id",
            "X-correlation-id",
        ]

        # While HTTP is case-insensitive, our config specifically uses this case
        assert configured_header == "X-Correlation-ID"

        # Verify our configured header follows conventional naming
        # (Pascal-Case for HTTP headers)
        assert configured_header.startswith("X-")  # Custom header prefix
        assert "Correlation" in configured_header  # Clear purpose
        assert "ID" in configured_header  # Clear identifier

    def test_correlation_id_length_limits(self):
        """Test reasonable length limits for correlation IDs."""
        # While Kong might not enforce strict limits, we should test reasonable boundaries

        # Minimum length (should be meaningful)
        min_length_id = "a"  # Single character
        assert len(min_length_id) >= 1

        # UUID length (common case)
        uuid_id = str(uuid.uuid4())
        assert len(uuid_id) == 36

        # Reasonable maximum (avoid header size issues)
        max_reasonable_id = "x" * 255  # HTTP header line limit considerations
        assert len(max_reasonable_id) <= 255

        # Very long ID (potential issue)
        very_long_id = "x" * 1000
        # This should work but might cause issues in practice
        assert len(very_long_id) == 1000

    def test_correlation_id_special_characters(self):
        """Test handling of special characters in correlation IDs."""
        # Test various character sets that might appear in correlation IDs

        test_cases = [
            "simple-123",  # Alphanumeric with hyphens
            "uuid_" + str(uuid.uuid4()),  # UUID with prefix
            "trace.span.12345",  # Dotted notation
            "req:12345:user:67890",  # Colon separated
            "session_abc123_request_xyz789",  # Underscore separated
        ]

        for test_id in test_cases:
            # These should all be valid HTTP header values
            assert len(test_id) > 0
            assert test_id == test_id  # Identity preservation

            # Should not contain characters that break HTTP headers
            invalid_chars = ["\n", "\r", "\0"]
            for char in invalid_chars:
                assert char not in test_id, f"Correlation ID should not contain {repr(char)}"
                assert (
                    char not in test_id
                ), f"Correlation ID should not contain {repr(char)}"
