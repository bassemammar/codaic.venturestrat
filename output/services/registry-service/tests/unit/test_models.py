"""Tests for registry data models - TDD approach.

These tests define the expected behavior of ServiceRegistration,
ServiceInstance, HealthCheckConfig, and ServiceQuery models.
"""
from datetime import UTC, datetime

from registry.manifest import ManifestParser
from registry.models import (
    HealthCheckConfig,
    HealthStatus,
    Protocol,
    ServiceInstance,
    ServiceQuery,
    ServiceRegistration,
)


class TestHealthCheckConfig:
    """Tests for HealthCheckConfig model."""

    def test_default_http_health_check(self):
        """Create default HTTP health check configuration."""
        config = HealthCheckConfig(http_endpoint="/health/ready")

        assert config.http_endpoint == "/health/ready"
        assert config.grpc_service is None
        assert config.interval_seconds == 10
        assert config.timeout_seconds == 5
        assert config.deregister_after_seconds == 60

    def test_grpc_health_check(self):
        """Create gRPC health check configuration."""
        config = HealthCheckConfig(grpc_service="grpc.health.v1.Health")

        assert config.http_endpoint is None
        assert config.grpc_service == "grpc.health.v1.Health"

    def test_custom_intervals(self):
        """Health check with custom intervals."""
        config = HealthCheckConfig(
            http_endpoint="/health",
            interval_seconds=30,
            timeout_seconds=10,
            deregister_after_seconds=120,
        )

        assert config.interval_seconds == 30
        assert config.timeout_seconds == 10
        assert config.deregister_after_seconds == 120

    def test_serialization(self):
        """Health check serializes to dict."""
        config = HealthCheckConfig(http_endpoint="/health")
        data = config.to_dict()

        assert data["http_endpoint"] == "/health"
        assert "interval_seconds" in data


class TestServiceRegistration:
    """Tests for ServiceRegistration model."""

    def test_create_minimal_registration(self):
        """Create registration with required fields only."""
        reg = ServiceRegistration(
            name="test-service",
            version="1.0.0",
            instance_id="test-service-abc123",
            address="10.0.1.50",
            port=8080,
            protocol=Protocol.HTTP,
        )

        assert reg.name == "test-service"
        assert reg.version == "1.0.0"
        assert reg.instance_id == "test-service-abc123"
        assert reg.address == "10.0.1.50"
        assert reg.port == 8080
        assert reg.protocol == Protocol.HTTP

    def test_create_full_registration(self):
        """Create registration with all fields."""
        now = datetime.now(UTC)
        health_config = HealthCheckConfig(http_endpoint="/health")

        reg = ServiceRegistration(
            name="pricing-service",
            version="1.2.0",
            instance_id="pricing-service-def456",
            address="10.0.1.100",
            port=8080,
            protocol=Protocol.HTTP,
            depends=["market-data-service@^1.0.0"],
            provides={"events": ["pricing.quote.created"], "apis": {"rest": "/api/v1"}},
            health_check=health_config,
            tags=["production", "pricing"],
            metadata={"team": "quant"},
            registered_at=now,
            last_heartbeat=now,
        )

        assert reg.depends == ["market-data-service@^1.0.0"]
        assert reg.tags == ["production", "pricing"]
        assert reg.metadata == {"team": "quant"}
        assert reg.registered_at == now

    def test_create_from_manifest(self):
        """Create registration from parsed manifest."""
        parser = ManifestParser()
        manifest = parser.parse_string(
            """
name: pricing-service
version: 1.2.0
depends:
  - market-data-service@^1.0.0
provides:
  events:
    - pricing.quote.created
  apis:
    rest: /api/v1/pricing
health:
  liveness: /health/live
  readiness: /health/ready
tags:
  - production
"""
        )

        reg = ServiceRegistration.from_manifest(
            manifest=manifest,
            instance_id="pricing-service-xyz789",
            address="10.0.1.200",
            port=8080,
        )

        assert reg.name == "pricing-service"
        assert reg.version == "1.2.0"
        assert reg.depends == ["market-data-service@^1.0.0"]
        assert reg.health_check.http_endpoint == "/health/ready"
        assert "production" in reg.tags

    def test_create_from_manifest_with_consul_tags(self):
        """Create registration from manifest with observability consul_tags."""
        parser = ManifestParser()
        manifest = parser.parse_string(
            """
name: registry-service
version: 1.0.0
observability:
  tier: fast
  consul_tags:
    - metrics
    - monitoring
tags:
  - platform
  - infrastructure
"""
        )

        reg = ServiceRegistration.from_manifest(
            manifest=manifest,
            instance_id="registry-service-abc123",
            address="10.0.0.5",
            port=8080,
        )

        assert reg.name == "registry-service"
        assert reg.version == "1.0.0"
        # Should contain both regular tags and consul_tags from observability
        assert "platform" in reg.tags
        assert "infrastructure" in reg.tags
        assert "metrics" in reg.tags
        assert "monitoring" in reg.tags
        assert len(reg.tags) == 4

    def test_default_timestamps(self):
        """Registration gets automatic timestamps if not provided."""
        reg = ServiceRegistration(
            name="test-service",
            version="1.0.0",
            instance_id="test-123",
            address="127.0.0.1",
            port=8080,
            protocol=Protocol.HTTP,
        )

        # Should have timestamps set
        assert reg.registered_at is not None
        assert reg.last_heartbeat is not None

    def test_serialization_to_dict(self):
        """Registration serializes to dictionary."""
        reg = ServiceRegistration(
            name="test-service",
            version="1.0.0",
            instance_id="test-123",
            address="127.0.0.1",
            port=8080,
            protocol=Protocol.HTTP,
            tags=["test"],
        )

        data = reg.to_dict()

        assert data["name"] == "test-service"
        assert data["version"] == "1.0.0"
        assert data["tags"] == ["test"]
        assert isinstance(data["registered_at"], str)  # ISO format

    def test_serialization_to_consul_format(self):
        """Registration converts to Consul service format."""
        reg = ServiceRegistration(
            name="test-service",
            version="1.0.0",
            instance_id="test-123",
            address="127.0.0.1",
            port=8080,
            protocol=Protocol.HTTP,
            tags=["production"],
            metadata={"team": "platform"},
        )

        consul_data = reg.to_consul_format()

        # Consul expects specific fields
        assert consul_data["ID"] == "test-123"
        assert consul_data["Name"] == "test-service"
        assert consul_data["Address"] == "127.0.0.1"
        assert consul_data["Port"] == 8080
        assert "production" in consul_data["Tags"]
        assert consul_data["Meta"]["version"] == "1.0.0"
        assert consul_data["Meta"]["team"] == "platform"


class TestServiceInstance:
    """Tests for ServiceInstance model (discovered service)."""

    def test_create_instance(self):
        """Create a discovered service instance."""
        instance = ServiceInstance(
            name="market-data-service",
            version="1.5.0",
            instance_id="market-data-abc",
            address="10.0.2.10",
            port=8080,
            protocol=Protocol.HTTP,
            health_status=HealthStatus.HEALTHY,
            tags=["production"],
            metadata={"region": "us-east"},
        )

        assert instance.name == "market-data-service"
        assert instance.health_status == HealthStatus.HEALTHY
        assert instance.is_healthy is True

    def test_unhealthy_instance(self):
        """Unhealthy instance has is_healthy=False."""
        instance = ServiceInstance(
            name="failing-service",
            version="1.0.0",
            instance_id="failing-123",
            address="10.0.2.20",
            port=8080,
            protocol=Protocol.HTTP,
            health_status=HealthStatus.CRITICAL,
            tags=[],
            metadata={},
        )

        assert instance.health_status == HealthStatus.CRITICAL
        assert instance.is_healthy is False

    def test_warning_instance(self):
        """Warning status is not fully healthy."""
        instance = ServiceInstance(
            name="degraded-service",
            version="1.0.0",
            instance_id="degraded-123",
            address="10.0.2.30",
            port=8080,
            protocol=Protocol.HTTP,
            health_status=HealthStatus.WARNING,
            tags=[],
            metadata={},
        )

        assert instance.health_status == HealthStatus.WARNING
        assert instance.is_healthy is False  # Warning is not fully healthy

    def test_create_from_consul_response(self):
        """Create instance from Consul catalog response."""
        consul_data = {
            "ServiceID": "market-data-xyz",
            "ServiceName": "market-data-service",
            "ServiceAddress": "10.0.3.50",
            "ServicePort": 8080,
            "ServiceTags": ["production", "v1.2.0"],
            "ServiceMeta": {
                "version": "1.2.0",
                "protocol": "http",
                "team": "data",
            },
        }
        health_data = {
            "Status": "passing",
        }

        instance = ServiceInstance.from_consul(consul_data, health_data)

        assert instance.name == "market-data-service"
        assert instance.instance_id == "market-data-xyz"
        assert instance.version == "1.2.0"
        assert instance.health_status == HealthStatus.HEALTHY
        assert instance.metadata["team"] == "data"

    def test_endpoint_url(self):
        """Instance provides endpoint URL."""
        instance = ServiceInstance(
            name="api-service",
            version="1.0.0",
            instance_id="api-123",
            address="10.0.1.10",
            port=8080,
            protocol=Protocol.HTTP,
            health_status=HealthStatus.HEALTHY,
            tags=[],
            metadata={},
        )

        assert instance.endpoint == "http://10.0.1.10:8080"

    def test_grpc_endpoint(self):
        """gRPC instance provides correct endpoint format."""
        instance = ServiceInstance(
            name="grpc-service",
            version="1.0.0",
            instance_id="grpc-123",
            address="10.0.1.20",
            port=50051,
            protocol=Protocol.GRPC,
            health_status=HealthStatus.HEALTHY,
            tags=[],
            metadata={},
        )

        assert instance.endpoint == "10.0.1.20:50051"


class TestServiceQuery:
    """Tests for ServiceQuery model (discovery filter)."""

    def test_simple_query_by_name(self):
        """Query for service by name only."""
        query = ServiceQuery(name="market-data-service")

        assert query.name == "market-data-service"
        assert query.version_constraint is None
        assert query.tags is None
        assert query.healthy_only is True  # Default

    def test_query_with_version_constraint(self):
        """Query with semver version constraint."""
        query = ServiceQuery(name="pricing-service", version_constraint="^1.0.0")

        assert query.version_constraint == "^1.0.0"

    def test_query_with_tags(self):
        """Query filtering by tags."""
        query = ServiceQuery(name="any-service", tags=["production", "region-eu"])

        assert query.tags == ["production", "region-eu"]

    def test_query_include_unhealthy(self):
        """Query including unhealthy instances."""
        query = ServiceQuery(name="any-service", healthy_only=False)

        assert query.healthy_only is False

    def test_query_to_consul_params(self):
        """Query converts to Consul API parameters."""
        query = ServiceQuery(name="test-service", tags=["production"], healthy_only=True)

        params = query.to_consul_params()

        assert params["service"] == "test-service"
        assert "production" in params.get("tag", [])
        assert params.get("passing") is True


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_health_status_values(self):
        """Health status has expected values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.WARNING.value == "warning"
        assert HealthStatus.CRITICAL.value == "critical"

    def test_from_consul_status(self):
        """Convert Consul status strings to HealthStatus."""
        assert HealthStatus.from_consul("passing") == HealthStatus.HEALTHY
        assert HealthStatus.from_consul("warning") == HealthStatus.WARNING
        assert HealthStatus.from_consul("critical") == HealthStatus.CRITICAL
        assert HealthStatus.from_consul("unknown") == HealthStatus.CRITICAL


class TestProtocol:
    """Tests for Protocol enum."""

    def test_protocol_values(self):
        """Protocol has expected values."""
        assert Protocol.HTTP.value == "http"
        assert Protocol.GRPC.value == "grpc"
        assert Protocol.TCP.value == "tcp"
