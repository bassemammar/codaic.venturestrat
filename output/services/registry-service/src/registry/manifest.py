"""Manifest parser for VentureStrat service manifests.

This module provides parsing and validation for manifest.yaml files,
which are the service descriptors (like BaseModel's __manifest__.py) for
VentureStrat microservices.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class ManifestParseError(Exception):
    """Raised when manifest file cannot be parsed (YAML syntax, file not found)."""

    pass


class ManifestValidationError(Exception):
    """Raised when manifest content fails validation."""

    pass


# Regex patterns for validation
SERVICE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
DEPENDENCY_PATTERN = re.compile(r"^([a-z][a-z0-9-]*[a-z0-9])@(.+)$")


class ApiConfig(BaseModel):
    """API configuration for a service."""

    rest: str | None = None
    grpc: str | None = None
    graphql: str | None = None


class ProvidesConfig(BaseModel):
    """What the service provides (events and APIs)."""

    events: list[str] = Field(default_factory=list)
    apis: ApiConfig = Field(default_factory=ApiConfig)


class SecurityRule(BaseModel):
    """Access control rule for a model/role combination."""

    model: str
    role: str
    read: bool = False
    write: bool = False
    create: bool = False
    delete: bool = False


class SecurityConfig(BaseModel):
    """Security configuration for a service."""

    roles: list[str] = Field(default_factory=list)
    rules: list[SecurityRule] = Field(default_factory=list)


class UiConfig(BaseModel):
    """UI configuration for a service."""

    schemas: list[str] = Field(default_factory=list)


class HealthConfig(BaseModel):
    """Health check configuration for a service."""

    liveness: str = "/health/live"
    readiness: str = "/health/ready"
    interval: int = Field(default=10, ge=1, le=300)
    timeout: int = Field(default=5, ge=1, le=60)
    deregister_after: int = Field(default=60, ge=10, le=3600)


class ResourceConfig(BaseModel):
    """Kubernetes resource requirements."""

    cpu: str | None = None
    memory: str | None = None
    replicas: str | None = None


class ObservabilitySloConfig(BaseModel):
    """SLO configuration for observability."""

    p95_target_ms: int = Field(default=200, ge=1)
    p99_target_ms: int = Field(default=500, ge=1)


class ObservabilityMetricsConfig(BaseModel):
    """Metrics configuration for observability."""

    enabled: bool = True
    endpoint: str = "/metrics"
    histogram_buckets: list[float] = Field(
        default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
    )
    slo: ObservabilitySloConfig = Field(default_factory=ObservabilitySloConfig)


class ObservabilityLoggingConfig(BaseModel):
    """Logging configuration for observability."""

    enabled: bool = True
    level: str = "INFO"
    structured: bool = True
    correlation_id: bool = True
    sensitive_data_masking: bool = True


class ObservabilityTracingConfig(BaseModel):
    """Tracing configuration for observability."""

    enabled: bool = True
    sampling_rate: float = Field(default=0.01, ge=0.0, le=1.0)
    otlp_endpoint: str = "http://jaeger:4317"


class ObservabilityConfig(BaseModel):
    """Observability configuration for a service."""

    tier: str = "standard"  # fast, standard, batch
    metrics: ObservabilityMetricsConfig = Field(default_factory=ObservabilityMetricsConfig)
    logging: ObservabilityLoggingConfig = Field(default_factory=ObservabilityLoggingConfig)
    tracing: ObservabilityTracingConfig = Field(default_factory=ObservabilityTracingConfig)
    consul_tags: list[str] = Field(default_factory=list)

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        """Validate observability tier."""
        valid_tiers = {"fast", "standard", "batch"}
        if v not in valid_tiers:
            raise ValueError(f"Invalid tier '{v}'. Must be one of: {valid_tiers}")
        return v

    @model_validator(mode="after")
    def validate_consul_tags_for_metrics(self) -> ObservabilityConfig:
        """Validate that metrics-enabled services have consul_tags."""
        if self.metrics.enabled and not self.consul_tags:
            raise ValueError(
                "Observability configuration with metrics enabled must include consul_tags "
                "(e.g., ['metrics'] for Prometheus discovery)"
            )
        return self


class Manifest(BaseModel):
    """VentureStrat service manifest (like BaseModel's __manifest__.py).

    This dataclass represents a parsed and validated manifest.yaml file.
    """

    # Required fields
    name: str
    version: str

    # Optional metadata
    description: str | None = None
    author: str | None = None
    license: str | None = None

    # Dependencies and provides
    depends: list[str] = Field(default_factory=list)
    provides: ProvidesConfig | None = None

    # Database and security
    migrations: list[str] = Field(default_factory=list)
    security: SecurityConfig | None = None

    # UI and health
    ui: UiConfig | None = None
    health: HealthConfig = Field(default_factory=HealthConfig)

    # Resources
    resources: ResourceConfig | None = None

    # Observability configuration
    observability: ObservabilityConfig | None = None

    # Custom metadata and tags
    metadata: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate service name format."""
        if not SERVICE_NAME_PATTERN.match(v):
            raise ValueError(
                f"Invalid service name '{v}'. Must be lowercase, alphanumeric "
                "with hyphens, starting with a letter and ending with alphanumeric."
            )
        if len(v) < 2 or len(v) > 63:
            raise ValueError(f"Service name must be between 2 and 63 characters, got {len(v)}.")
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semver format."""
        if not SEMVER_PATTERN.match(v):
            raise ValueError(
                f"Invalid version '{v}'. Must be valid semver (e.g., 1.2.0, 1.0.0-alpha.1)."
            )
        return v

    @field_validator("depends")
    @classmethod
    def validate_depends(cls, v: list[str]) -> list[str]:
        """Validate dependency format."""
        for dep in v:
            if not DEPENDENCY_PATTERN.match(dep):
                raise ValueError(
                    f"Invalid dependency format '{dep}'. "
                    "Must be 'service-name@version-constraint' (e.g., market-data-service@^1.0.0)."
                )
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to dictionary."""
        return self.model_dump(exclude_none=True)

    def to_consul_metadata(self) -> dict[str, str]:
        """Convert manifest to flat Consul metadata format.

        Consul expects flat key-value pairs for service metadata.
        """
        meta = {
            "service_name": self.name,
            "service_version": self.version,
        }
        if self.description:
            meta["service_description"] = self.description
        if self.author:
            meta["service_author"] = self.author

        # Add health endpoints
        if self.health:
            meta["health_liveness"] = self.health.liveness
            meta["health_readiness"] = self.health.readiness

        # Add provides info
        if self.provides and self.provides.apis:
            if self.provides.apis.rest:
                meta["api_rest"] = self.provides.apis.rest
            if self.provides.apis.grpc:
                meta["api_grpc"] = self.provides.apis.grpc

        # Add dependency count
        meta["dependency_count"] = str(len(self.depends))

        # Add observability info
        if self.observability:
            meta["observability_tier"] = self.observability.tier
            meta["observability_metrics_enabled"] = str(self.observability.metrics.enabled).lower()
            if self.observability.metrics.enabled:
                meta["observability_metrics_endpoint"] = self.observability.metrics.endpoint

        return meta

    def __hash__(self) -> int:
        """Make manifest hashable for use in sets/dicts."""
        return hash((self.name, self.version))

    def __eq__(self, other: object) -> bool:
        """Check equality based on name and version."""
        if not isinstance(other, Manifest):
            return False
        return self.name == other.name and self.version == other.version


class ManifestParser:
    """Parser for VentureStrat manifest.yaml files.

    Usage:
        parser = ManifestParser()
        manifest = parser.parse_file(Path("path/to/manifest.yaml"))

        # Or from string
        manifest = parser.parse_string(yaml_content)

        # Or from dict
        manifest = parser.parse_dict(data)
    """

    def __init__(self, strict: bool = False):
        """Initialize parser.

        Args:
            strict: If True, unknown fields raise an error. If False, they log a warning.
        """
        self.strict = strict
        self._schema: dict | None = None

    def parse_file(self, path: Path) -> Manifest:
        """Parse manifest from file.

        Args:
            path: Path to the manifest.yaml file.

        Returns:
            Parsed and validated Manifest object.

        Raises:
            ManifestParseError: If file not found or YAML syntax error.
            ManifestValidationError: If manifest content is invalid.
        """
        if not path.exists():
            raise ManifestParseError(f"Manifest file not found: {path}")

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            raise ManifestParseError(f"Error reading manifest file: {e}") from e

        return self.parse_string(content)

    def parse_string(self, content: str) -> Manifest:
        """Parse manifest from YAML string.

        Args:
            content: YAML content as string.

        Returns:
            Parsed and validated Manifest object.

        Raises:
            ManifestParseError: If YAML syntax error.
            ManifestValidationError: If manifest content is invalid.
        """
        if not content or not content.strip():
            raise ManifestParseError("Empty manifest content")

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ManifestParseError(f"Invalid YAML syntax: {e}") from e

        if data is None:
            raise ManifestParseError("Empty manifest content")

        return self.parse_dict(data)

    def parse_dict(self, data: dict[str, Any]) -> Manifest:
        """Parse manifest from dictionary.

        Args:
            data: Dictionary containing manifest data.

        Returns:
            Parsed and validated Manifest object.

        Raises:
            ManifestValidationError: If manifest content is invalid.
        """
        # Check for unknown fields
        known_fields = {
            "name",
            "version",
            "description",
            "author",
            "license",
            "depends",
            "provides",
            "migrations",
            "security",
            "ui",
            "health",
            "resources",
            "observability",
            "metadata",
            "tags",
        }
        unknown_fields = set(data.keys()) - known_fields

        if unknown_fields:
            if self.strict:
                raise ManifestValidationError(
                    f"Unknown fields in manifest (additional properties not allowed): {unknown_fields}"
                )
            else:
                logger.warning(f"Unknown fields in manifest will be ignored: {unknown_fields}")
                # Remove unknown fields
                data = {k: v for k, v in data.items() if k in known_fields}

        # Validate required fields presence
        if "name" not in data:
            raise ManifestValidationError("Missing required field: 'name'")
        if "version" not in data:
            raise ManifestValidationError("Missing required field: 'version'")

        try:
            return Manifest.model_validate(data)
        except Exception as e:
            raise ManifestValidationError(f"Manifest validation failed: {e}") from e

    def parse_dependency(self, dep_string: str) -> tuple[str, str]:
        """Parse a dependency string into name and version constraint.

        Args:
            dep_string: Dependency string like 'service-name@^1.0.0'

        Returns:
            Tuple of (service_name, version_constraint)

        Raises:
            ManifestValidationError: If dependency format is invalid.
        """
        match = DEPENDENCY_PATTERN.match(dep_string)
        if not match:
            raise ManifestValidationError(
                f"Invalid dependency format: '{dep_string}'. "
                "Expected format: 'service-name@version-constraint'"
            )
        return match.group(1), match.group(2)

    def load_schema(self) -> dict:
        """Load the JSON Schema for manifest validation.

        Returns:
            The manifest JSON schema as a dictionary.
        """
        if self._schema is None:
            schema_path = Path(__file__).parent.parent.parent / "schemas" / "manifest-v1.0.0.json"
            with open(schema_path) as f:
                self._schema = json.load(f)
        return self._schema
