"""Tests for ManifestParser - TDD approach.

These tests define the expected behavior of the ManifestParser
before implementation.
"""
from pathlib import Path

import pytest
from registry.manifest import (
    ManifestParseError,
    ManifestParser,
    ManifestValidationError,
)

from tests.fixtures import get_manifest_path


class TestManifestParserValidManifests:
    """Tests for parsing valid manifests."""

    def test_parse_complete_manifest(self):
        """Parse a complete manifest with all fields populated."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("valid_complete"))

        # Required fields
        assert manifest.name == "pricing-service"
        assert manifest.version == "1.2.0"

        # Optional fields
        assert manifest.description == "Real-time pricing engine for FX and derivatives"
        assert manifest.author == "VentureStrat Team"
        assert manifest.license == "MIT"

    def test_parse_complete_manifest_dependencies(self):
        """Parse dependencies with version constraints."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("valid_complete"))

        assert len(manifest.depends) == 2
        assert "market-data-service@^1.0.0" in manifest.depends
        assert "reference-data-service@~1.2.0" in manifest.depends

    def test_parse_complete_manifest_provides(self):
        """Parse provides section with events and APIs."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("valid_complete"))

        assert manifest.provides is not None
        assert len(manifest.provides.events) == 3
        assert "pricing.quote.created" in manifest.provides.events
        assert manifest.provides.apis.rest == "/api/v1/pricing"
        assert manifest.provides.apis.grpc == "pricing.v1.PricingService"

    def test_parse_complete_manifest_security(self):
        """Parse security roles and rules."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("valid_complete"))

        assert manifest.security is not None
        assert len(manifest.security.roles) == 2
        assert "pricer" in manifest.security.roles
        assert "pricer_admin" in manifest.security.roles

        # Check rules
        assert len(manifest.security.rules) == 2
        pricer_rule = next(r for r in manifest.security.rules if r.role == "pricer")
        assert pricer_rule.model == "Quote"
        assert pricer_rule.read is True
        assert pricer_rule.write is False

    def test_parse_complete_manifest_health(self):
        """Parse health check configuration."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("valid_complete"))

        assert manifest.health is not None
        assert manifest.health.liveness == "/health/live"
        assert manifest.health.readiness == "/health/ready"
        assert manifest.health.interval == 15
        assert manifest.health.timeout == 3
        assert manifest.health.deregister_after == 120

    def test_parse_complete_manifest_resources(self):
        """Parse Kubernetes resource requirements."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("valid_complete"))

        assert manifest.resources is not None
        assert manifest.resources.cpu == "500m-2000m"
        assert manifest.resources.memory == "512Mi-2Gi"
        assert manifest.resources.replicas == "2-10"

    def test_parse_complete_manifest_metadata_and_tags(self):
        """Parse custom metadata and tags."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("valid_complete"))

        assert manifest.metadata == {"team": "quant", "tier": "critical"}
        assert set(manifest.tags) == {"production", "pricing", "real-time"}

    def test_parse_minimal_manifest(self):
        """Parse a minimal manifest with only required fields."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("valid_minimal"))

        assert manifest.name == "simple-service"
        assert manifest.version == "0.1.0"

        # Optional fields should have defaults or be None
        assert manifest.description is None
        assert manifest.depends == []
        assert manifest.tags == []

    def test_parse_minimal_manifest_default_health(self):
        """Minimal manifest should have default health config."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("valid_minimal"))

        # Should have defaults
        assert manifest.health is not None
        assert manifest.health.liveness == "/health/live"
        assert manifest.health.readiness == "/health/ready"
        assert manifest.health.interval == 10
        assert manifest.health.timeout == 5
        assert manifest.health.deregister_after == 60


class TestManifestParserFromString:
    """Tests for parsing manifests from YAML strings."""

    def test_parse_from_string(self):
        """Parse manifest from YAML string."""
        parser = ManifestParser()
        yaml_content = """
name: test-service
version: 1.0.0
description: Test service
"""
        manifest = parser.parse_string(yaml_content)

        assert manifest.name == "test-service"
        assert manifest.version == "1.0.0"
        assert manifest.description == "Test service"

    def test_parse_from_dict(self):
        """Parse manifest from dictionary."""
        parser = ManifestParser()
        data = {
            "name": "dict-service",
            "version": "2.0.0",
            "depends": ["other-service@^1.0.0"],
        }
        manifest = parser.parse_dict(data)

        assert manifest.name == "dict-service"
        assert manifest.version == "2.0.0"
        assert manifest.depends == ["other-service@^1.0.0"]


class TestManifestParserInvalidManifests:
    """Tests for validation errors on invalid manifests."""

    def test_invalid_semver_version(self):
        """Reject manifests with invalid semver versions."""
        parser = ManifestParser()

        with pytest.raises(ManifestValidationError) as exc_info:
            parser.parse_file(get_manifest_path("invalid_semver"))

        assert "version" in str(exc_info.value).lower()

    def test_invalid_service_name(self):
        """Reject manifests with invalid service names."""
        parser = ManifestParser()

        with pytest.raises(ManifestValidationError) as exc_info:
            parser.parse_file(get_manifest_path("invalid_name"))

        assert "name" in str(exc_info.value).lower()

    def test_invalid_dependency_format(self):
        """Reject manifests with invalid dependency formats."""
        parser = ManifestParser()

        with pytest.raises(ManifestValidationError) as exc_info:
            parser.parse_file(get_manifest_path("invalid_dependency"))

        assert "depend" in str(exc_info.value).lower()

    def test_missing_required_name(self):
        """Reject manifests missing required 'name' field."""
        parser = ManifestParser()

        with pytest.raises(ManifestValidationError) as exc_info:
            parser.parse_string("version: 1.0.0")

        assert "name" in str(exc_info.value).lower()

    def test_missing_required_version(self):
        """Reject manifests missing required 'version' field."""
        parser = ManifestParser()

        with pytest.raises(ManifestValidationError) as exc_info:
            parser.parse_string("name: test-service")

        assert "version" in str(exc_info.value).lower()

    def test_empty_yaml(self):
        """Reject empty YAML content."""
        parser = ManifestParser()

        with pytest.raises(ManifestParseError):
            parser.parse_string("")

    def test_invalid_yaml_syntax(self):
        """Reject invalid YAML syntax."""
        parser = ManifestParser()

        with pytest.raises(ManifestParseError):
            parser.parse_string("name: test\n  invalid: indent")

    def test_file_not_found(self):
        """Raise error for non-existent manifest file."""
        parser = ManifestParser()

        with pytest.raises(ManifestParseError) as exc_info:
            parser.parse_file(Path("/nonexistent/path/manifest.yaml"))

        assert "not found" in str(exc_info.value).lower()


class TestManifestParserUnknownFields:
    """Tests for handling unknown fields in manifests."""

    def test_unknown_fields_warning(self, caplog):
        """Log warning for unknown fields but still parse."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("with_unknown_fields"))

        # Should still parse successfully
        assert manifest.name == "service-with-extras"
        assert manifest.version == "1.0.0"

        # Should log warnings about unknown fields
        assert "custom_field" in caplog.text or "unknown" in caplog.text.lower()

    def test_strict_mode_rejects_unknown_fields(self):
        """In strict mode, unknown fields should raise an error."""
        parser = ManifestParser(strict=True)

        with pytest.raises(ManifestValidationError) as exc_info:
            parser.parse_file(get_manifest_path("with_unknown_fields"))

        assert (
            "additional properties" in str(exc_info.value).lower()
            or "unknown" in str(exc_info.value).lower()
        )


class TestManifestModel:
    """Tests for the Manifest dataclass itself."""

    def test_manifest_to_dict(self):
        """Manifest can be serialized to dictionary."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("valid_complete"))

        data = manifest.to_dict()

        assert data["name"] == "pricing-service"
        assert data["version"] == "1.2.0"
        assert isinstance(data["depends"], list)

    def test_manifest_to_consul_format(self):
        """Manifest can be converted to Consul metadata format."""
        parser = ManifestParser()
        manifest = parser.parse_file(get_manifest_path("valid_minimal"))

        consul_meta = manifest.to_consul_metadata()

        # Consul expects flat key-value pairs
        assert consul_meta["service_name"] == "simple-service"
        assert consul_meta["service_version"] == "0.1.0"

    def test_manifest_equality(self):
        """Two manifests with same data are equal."""
        parser = ManifestParser()
        m1 = parser.parse_file(get_manifest_path("valid_minimal"))
        m2 = parser.parse_file(get_manifest_path("valid_minimal"))

        assert m1 == m2

    def test_manifest_hash(self):
        """Manifest can be used in sets/dicts."""
        parser = ManifestParser()
        m1 = parser.parse_file(get_manifest_path("valid_minimal"))

        # Should be hashable
        manifest_set = {m1}
        assert m1 in manifest_set


class TestManifestDependencyParsing:
    """Tests for parsing dependency strings."""

    @pytest.mark.parametrize(
        "dep_string,expected_name,expected_constraint",
        [
            ("service-a@^1.0.0", "service-a", "^1.0.0"),
            ("service-b@~2.3.4", "service-b", "~2.3.4"),
            ("service-c@>=1.0.0", "service-c", ">=1.0.0"),
            ("service-d@1.2.3", "service-d", "1.2.3"),
            ("my-service@>=1.0.0-beta", "my-service", ">=1.0.0-beta"),
        ],
    )
    def test_parse_dependency_string(self, dep_string, expected_name, expected_constraint):
        """Parse dependency strings into name and constraint."""
        parser = ManifestParser()
        name, constraint = parser.parse_dependency(dep_string)

        assert name == expected_name
        assert constraint == expected_constraint

    def test_parse_dependency_string_invalid(self):
        """Invalid dependency strings raise error."""
        parser = ManifestParser()

        with pytest.raises(ManifestValidationError):
            parser.parse_dependency("invalid-no-version")


class TestManifestObservabilityConfiguration:
    """Tests for observability configuration in manifests."""

    def test_parse_complete_observability_configuration(self):
        """Parse complete observability configuration from manifest."""
        parser = ManifestParser()
        yaml_content = """
name: test-service
version: 1.0.0
description: Test service with observability

observability:
  tier: fast
  metrics:
    enabled: true
    endpoint: /metrics
    histogram_buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
    slo:
      p95_target_ms: 50
      p99_target_ms: 100
  logging:
    enabled: true
    level: INFO
    structured: true
    correlation_id: true
    sensitive_data_masking: true
  tracing:
    enabled: true
    sampling_rate: 0.01
    otlp_endpoint: http://jaeger:4317
  consul_tags:
    - metrics
"""
        manifest = parser.parse_string(yaml_content)

        assert manifest.observability is not None
        assert manifest.observability.tier == "fast"

        # Metrics configuration
        assert manifest.observability.metrics.enabled is True
        assert manifest.observability.metrics.endpoint == "/metrics"
        assert manifest.observability.metrics.histogram_buckets == [
            0.005,
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
        ]
        assert manifest.observability.metrics.slo.p95_target_ms == 50
        assert manifest.observability.metrics.slo.p99_target_ms == 100

        # Logging configuration
        assert manifest.observability.logging.enabled is True
        assert manifest.observability.logging.level == "INFO"
        assert manifest.observability.logging.structured is True
        assert manifest.observability.logging.correlation_id is True
        assert manifest.observability.logging.sensitive_data_masking is True

        # Tracing configuration
        assert manifest.observability.tracing.enabled is True
        assert manifest.observability.tracing.sampling_rate == 0.01
        assert manifest.observability.tracing.otlp_endpoint == "http://jaeger:4317"

        # Consul tags
        assert "metrics" in manifest.observability.consul_tags

    def test_parse_observability_with_standard_tier(self):
        """Parse observability configuration with standard tier."""
        parser = ManifestParser()
        yaml_content = """
name: standard-service
version: 1.0.0

observability:
  tier: standard
  metrics:
    enabled: true
    endpoint: /metrics
    histogram_buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
    slo:
      p95_target_ms: 200
      p99_target_ms: 500
  logging:
    enabled: true
    level: INFO
    structured: true
    correlation_id: true
    sensitive_data_masking: true
  tracing:
    enabled: true
    sampling_rate: 0.05
    otlp_endpoint: http://jaeger:4317
  consul_tags:
    - metrics
"""
        manifest = parser.parse_string(yaml_content)

        assert manifest.observability.tier == "standard"
        assert manifest.observability.metrics.histogram_buckets == [
            0.01,
            0.05,
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
        ]
        assert manifest.observability.metrics.slo.p95_target_ms == 200
        assert manifest.observability.metrics.slo.p99_target_ms == 500
        assert manifest.observability.tracing.sampling_rate == 0.05

    def test_parse_observability_with_batch_tier(self):
        """Parse observability configuration with batch tier."""
        parser = ManifestParser()
        yaml_content = """
name: batch-service
version: 1.0.0

observability:
  tier: batch
  metrics:
    enabled: true
    endpoint: /metrics
    histogram_buckets: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
    slo:
      p95_target_ms: 2000
      p99_target_ms: 5000
  logging:
    enabled: true
    level: INFO
    structured: true
    correlation_id: true
    sensitive_data_masking: true
  tracing:
    enabled: true
    sampling_rate: 0.1
    otlp_endpoint: http://jaeger:4317
  consul_tags:
    - metrics
"""
        manifest = parser.parse_string(yaml_content)

        assert manifest.observability.tier == "batch"
        assert manifest.observability.metrics.histogram_buckets == [
            0.1,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
            30.0,
        ]
        assert manifest.observability.metrics.slo.p95_target_ms == 2000
        assert manifest.observability.metrics.slo.p99_target_ms == 5000
        assert manifest.observability.tracing.sampling_rate == 0.1

    def test_validate_invalid_observability_tier(self):
        """Reject manifests with invalid observability tier."""
        parser = ManifestParser()
        yaml_content = """
name: invalid-service
version: 1.0.0

observability:
  tier: invalid_tier
  metrics:
    enabled: true
"""

        with pytest.raises(ManifestValidationError) as exc_info:
            parser.parse_string(yaml_content)

        assert "tier" in str(exc_info.value).lower()
        assert "invalid_tier" in str(exc_info.value) or "fast" in str(exc_info.value)

    def test_validate_missing_consul_tags(self):
        """Reject observability config without required consul_tags for metrics."""
        parser = ManifestParser()
        yaml_content = """
name: no-tags-service
version: 1.0.0

observability:
  tier: fast
  metrics:
    enabled: true
    endpoint: /metrics
"""

        with pytest.raises(ManifestValidationError) as exc_info:
            parser.parse_string(yaml_content)

        assert (
            "consul_tags" in str(exc_info.value).lower() or "metrics" in str(exc_info.value).lower()
        )

    def test_validate_invalid_sampling_rate(self):
        """Reject invalid sampling rates (outside 0.0-1.0 range)."""
        parser = ManifestParser()
        yaml_content = """
name: invalid-sampling-service
version: 1.0.0

observability:
  tier: fast
  tracing:
    sampling_rate: 2.0
"""

        with pytest.raises(ManifestValidationError) as exc_info:
            parser.parse_string(yaml_content)

        assert "sampling_rate" in str(exc_info.value).lower()

    def test_parse_minimal_observability_with_defaults(self):
        """Parse minimal observability config and apply defaults."""
        parser = ManifestParser()
        yaml_content = """
name: minimal-observability-service
version: 1.0.0

observability:
  tier: fast
  consul_tags:
    - metrics
"""
        manifest = parser.parse_string(yaml_content)

        # Should have defaults applied
        assert manifest.observability.metrics.enabled is True
        assert manifest.observability.metrics.endpoint == "/metrics"
        assert manifest.observability.logging.enabled is True
        assert manifest.observability.logging.level == "INFO"
        assert manifest.observability.tracing.enabled is True

    def test_registry_service_manifest_has_fast_tier(self):
        """Registry service manifest should have fast tier configuration."""
        parser = ManifestParser()
        manifest = parser.parse_file(Path("services/registry-service/manifest.yaml"))

        assert manifest.observability is not None
        assert manifest.observability.tier == "fast"
        assert "metrics" in manifest.observability.consul_tags

    def test_observability_to_consul_metadata(self):
        """Observability config should be included in Consul metadata."""
        parser = ManifestParser()
        yaml_content = """
name: consul-test-service
version: 1.0.0

observability:
  tier: fast
  consul_tags:
    - metrics
"""
        manifest = parser.parse_string(yaml_content)
        consul_meta = manifest.to_consul_metadata()

        assert consul_meta["observability_tier"] == "fast"
        assert consul_meta["observability_metrics_enabled"] == "true"
