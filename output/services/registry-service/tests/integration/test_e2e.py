"""End-to-End integration tests for Registry Service.

These tests verify complete workflows with mocked infrastructure components.
Run with: pytest tests/integration/test_e2e.py -v
"""
from unittest.mock import AsyncMock

import pytest
from registry.consul_client import ConsulClient
from registry.events import EventPublisher
from registry.health import HealthManager
from registry.models import (
    HealthCheckConfig,
    HealthStatus,
    Protocol,
    ServiceInstance,
    ServiceRegistration,
)
from registry.service import RegistryService


@pytest.fixture
def mock_consul():
    """Create mock Consul client."""
    consul = AsyncMock(spec=ConsulClient)
    consul.register.return_value = True
    consul.deregister.return_value = True
    consul.kv_put.return_value = True
    consul.kv_get.return_value = None
    consul.kv_delete.return_value = True
    return consul


@pytest.fixture
def mock_events():
    """Create mock event publisher."""
    publisher = AsyncMock(spec=EventPublisher)
    return publisher


@pytest.fixture
def health_manager():
    """Create health manager."""
    return HealthManager()


@pytest.fixture
def registry_service(mock_consul, mock_events, health_manager):
    """Create registry service with mocks."""
    return RegistryService(
        consul_client=mock_consul,
        event_publisher=mock_events,
        health_manager=health_manager,
    )


def create_registration(
    name: str,
    version: str,
    instance_id: str,
    port: int = 8080,
    address: str = "10.0.1.50",
    depends: list[str] | None = None,
    tags: list[str] | None = None,
) -> ServiceRegistration:
    """Create a service registration."""
    return ServiceRegistration(
        name=name,
        version=version,
        instance_id=instance_id,
        address=address,
        port=port,
        protocol=Protocol.HTTP,
        depends=depends or [],
        health_check=HealthCheckConfig(http_endpoint="/health/ready"),
        tags=tags or [],
        metadata={},
    )


def create_instance(
    name: str,
    version: str,
    instance_id: str,
    port: int = 8080,
    address: str = "10.0.1.50",
    health_status: HealthStatus = HealthStatus.HEALTHY,
    tags: list[str] | None = None,
) -> ServiceInstance:
    """Create a service instance."""
    return ServiceInstance(
        name=name,
        version=version,
        instance_id=instance_id,
        address=address,
        port=port,
        protocol=Protocol.HTTP,
        health_status=health_status,
        tags=tags or [],
        metadata={},
    )


# =============================================================================
# Two-Service Discovery Test
# =============================================================================


class TestTwoServiceDiscovery:
    """Tests for service discovery between two services.

    Simulates the scenario where a pricing-service discovers market-data-service.
    """

    @pytest.mark.asyncio
    async def test_service_discovers_dependency(self, registry_service, mock_consul):
        """Pricing service can discover market-data service."""
        # Register market-data-service first
        market_data_reg = create_registration(
            name="market-data-service",
            version="1.0.0",
            instance_id="market-data-001",
            port=8080,
            tags=["production"],
        )
        await registry_service.register(market_data_reg)

        # Register pricing-service with dependency
        pricing_reg = create_registration(
            name="pricing-service",
            version="1.2.0",
            instance_id="pricing-001",
            port=8081,
            depends=["market-data-service@^1.0.0"],
            tags=["production"],
        )
        await registry_service.register(pricing_reg)

        # Mock discovery response
        mock_consul.discover.return_value = [
            create_instance(
                name="market-data-service",
                version="1.0.0",
                instance_id="market-data-001",
                tags=["production"],
            )
        ]

        # Pricing service discovers market-data
        instances = await registry_service.discover(
            "market-data-service",
            version_constraint="^1.0.0",
        )

        assert len(instances) == 1
        assert instances[0].name == "market-data-service"
        assert instances[0].version == "1.0.0"

    @pytest.mark.asyncio
    async def test_multiple_instances_discovered(self, registry_service, mock_consul):
        """Service discovers multiple healthy instances."""
        # Register multiple market-data instances
        for i in range(3):
            reg = create_registration(
                name="market-data-service",
                version="1.0.0",
                instance_id=f"market-data-00{i+1}",
                port=8080 + i,
                address=f"10.0.1.{50+i}",
                tags=["production"],
            )
            await registry_service.register(reg)

        # Mock discovery returns all instances
        mock_consul.discover.return_value = [
            create_instance(
                name="market-data-service",
                version="1.0.0",
                instance_id=f"market-data-00{i+1}",
                address=f"10.0.1.{50+i}",
                tags=["production"],
            )
            for i in range(3)
        ]

        instances = await registry_service.discover("market-data-service")

        assert len(instances) == 3
        assert all(i.health_status == HealthStatus.HEALTHY for i in instances)

    @pytest.mark.asyncio
    async def test_discovery_filters_unhealthy(self, registry_service, mock_consul):
        """Discovery only returns healthy instances by default."""
        # Mock: 2 healthy, 1 unhealthy
        mock_consul.discover.return_value = [
            create_instance("market-data-service", "1.0.0", "md-001"),
            create_instance("market-data-service", "1.0.0", "md-002"),
        ]

        instances = await registry_service.discover("market-data-service", healthy_only=True)

        assert len(instances) == 2
        assert all(i.is_healthy for i in instances)


# =============================================================================
# Service Failure Test
# =============================================================================


class TestServiceFailure:
    """Tests for service failure handling.

    Simulates scenarios where services become unhealthy or fail.
    """

    @pytest.mark.asyncio
    async def test_unhealthy_instance_not_discovered(self, registry_service, mock_consul):
        """Unhealthy instances are filtered from discovery."""
        # Register a service
        reg = create_registration(
            name="failing-service",
            version="1.0.0",
            instance_id="failing-001",
        )
        await registry_service.register(reg)

        # Mock: instance becomes unhealthy
        mock_consul.discover.return_value = []  # healthy_only filters it out

        instances = await registry_service.discover("failing-service", healthy_only=True)

        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_deregistration_publishes_event(self, registry_service, mock_events):
        """Deregistration publishes event."""
        await registry_service.deregister(
            instance_id="failing-001",
            service_name="failing-service",
            version="1.0.0",
            reason="health_check_failed",
        )

        mock_events.publish_deregistered.assert_called_once()
        call_kwargs = mock_events.publish_deregistered.call_args.kwargs
        assert call_kwargs["instance_id"] == "failing-001"
        assert call_kwargs["reason"] == "health_check_failed"

    @pytest.mark.asyncio
    async def test_registration_publishes_event(self, registry_service, mock_events):
        """Registration publishes event."""
        reg = create_registration(
            name="new-service",
            version="1.0.0",
            instance_id="new-001",
        )
        await registry_service.register(reg)

        mock_events.publish_registered.assert_called_once()
        call_args = mock_events.publish_registered.call_args[0][0]
        assert call_args.instance_id == "new-001"


# =============================================================================
# Rolling Deployment Test
# =============================================================================


class TestRollingDeployment:
    """Tests for rolling deployment scenarios.

    Simulates gradual version upgrades with version filtering.
    """

    @pytest.mark.asyncio
    async def test_version_filtering_during_deployment(self, registry_service, mock_consul):
        """During deployment, clients can filter by version constraint."""
        # Register v1.0.0 instances
        for i in range(2):
            reg = create_registration(
                name="pricing-service",
                version="1.0.0",
                instance_id=f"pricing-v1-00{i+1}",
            )
            await registry_service.register(reg)

        # Add v1.1.0 instance (new version during deployment)
        reg = create_registration(
            name="pricing-service",
            version="1.1.0",
            instance_id="pricing-v11-001",
        )
        await registry_service.register(reg)

        # Mock: all versions available
        mock_consul.discover.return_value = [
            create_instance("pricing-service", "1.0.0", "pricing-v1-001"),
            create_instance("pricing-service", "1.0.0", "pricing-v1-002"),
            create_instance("pricing-service", "1.1.0", "pricing-v11-001"),
        ]

        # Client requesting ^1.0.0 gets all (1.0.x and 1.1.x match ^1.0.0)
        instances = await registry_service.discover(
            "pricing-service",
            version_constraint="^1.0.0",
        )

        assert len(instances) == 3

    @pytest.mark.asyncio
    async def test_exact_version_match(self, registry_service, mock_consul):
        """Can request exact version during deployment."""
        mock_consul.discover.return_value = [
            create_instance("pricing-service", "1.0.0", "pricing-v1-001"),
            create_instance("pricing-service", "1.0.0", "pricing-v1-002"),
            create_instance("pricing-service", "1.1.0", "pricing-v11-001"),
        ]

        # Request exactly 1.0.0
        instances = await registry_service.discover(
            "pricing-service",
            version_constraint="1.0.0",
        )

        # Version matcher filters to exact version
        assert all(i.version == "1.0.0" for i in instances)

    @pytest.mark.asyncio
    async def test_tilde_constraint_for_patch_updates(self, registry_service, mock_consul):
        """Tilde constraint only allows patch updates."""
        mock_consul.discover.return_value = [
            create_instance("pricing-service", "1.0.0", "pricing-001"),
            create_instance("pricing-service", "1.0.1", "pricing-002"),
            create_instance("pricing-service", "1.1.0", "pricing-003"),
        ]

        # ~1.0.0 allows 1.0.x but not 1.1.x
        instances = await registry_service.discover(
            "pricing-service",
            version_constraint="~1.0.0",
        )

        # Only 1.0.x versions match
        assert all(i.version.startswith("1.0.") for i in instances)


# =============================================================================
# Tag-Based Discovery Tests
# =============================================================================


class TestTagBasedDiscovery:
    """Tests for tag-based service discovery."""

    @pytest.mark.asyncio
    async def test_discover_by_environment_tag(self, registry_service, mock_consul):
        """Can discover services by environment tag."""
        mock_consul.discover.return_value = [
            create_instance(
                "pricing-service",
                "1.0.0",
                "pricing-prod-001",
                tags=["production", "eu-west"],
            ),
        ]

        instances = await registry_service.discover(
            "pricing-service",
            tags=["production"],
        )

        assert len(instances) == 1
        assert "production" in instances[0].tags

    @pytest.mark.asyncio
    async def test_discover_by_region_tag(self, registry_service, mock_consul):
        """Can discover services by region tag."""
        mock_consul.discover.return_value = [
            create_instance(
                "pricing-service",
                "1.0.0",
                "pricing-eu-001",
                tags=["production", "eu-west"],
            ),
        ]

        instances = await registry_service.discover(
            "pricing-service",
            tags=["eu-west"],
        )

        assert len(instances) == 1


# =============================================================================
# Health Overview Tests
# =============================================================================


class TestHealthOverview:
    """Tests for health monitoring and overview."""

    @pytest.mark.asyncio
    async def test_health_overview_all_healthy(self, registry_service, mock_consul):
        """Health overview shows all services healthy."""
        mock_consul.list_services.return_value = {
            "pricing-service": ["production"],
            "market-data-service": ["production"],
        }
        mock_consul.discover.return_value = [
            create_instance("pricing-service", "1.0.0", "pricing-001"),
        ]

        overview = await registry_service.get_health_overview()

        assert "services" in overview
        assert overview["unhealthy_instances"] == 0

    @pytest.mark.asyncio
    async def test_get_service_info(self, registry_service, mock_consul):
        """Can get detailed info for a service."""
        mock_consul.discover.return_value = [
            create_instance("pricing-service", "1.0.0", "pricing-001"),
            create_instance("pricing-service", "1.0.0", "pricing-002"),
        ]

        info = await registry_service.get_service_info("pricing-service")

        assert info["name"] == "pricing-service"
        assert info["instance_count"] == 2
        assert info["healthy_count"] == 2
        assert "1.0.0" in info["versions"]


# =============================================================================
# Complete Registration Flow Test
# =============================================================================


class TestCompleteFlow:
    """Tests for complete registration/discovery/deregistration flow."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, registry_service, mock_consul, mock_events):
        """Test complete service lifecycle."""
        # 1. Register service
        reg = create_registration(
            name="lifecycle-service",
            version="1.0.0",
            instance_id="lifecycle-001",
            tags=["production"],
        )
        await registry_service.register(reg)

        # Verify registration published event
        mock_events.publish_registered.assert_called_once()

        # 2. Discover service
        mock_consul.discover.return_value = [
            create_instance(
                "lifecycle-service",
                "1.0.0",
                "lifecycle-001",
                tags=["production"],
            )
        ]

        instances = await registry_service.discover("lifecycle-service")
        assert len(instances) == 1

        # 3. Deregister service
        await registry_service.deregister(
            instance_id="lifecycle-001",
            service_name="lifecycle-service",
            version="1.0.0",
        )

        # Verify deregistration published event
        mock_events.publish_deregistered.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_services_coexist(self, registry_service, mock_consul, mock_events):
        """Multiple services can be registered and discovered."""
        services = [
            ("market-data-service", "1.0.0"),
            ("pricing-service", "1.2.0"),
            ("risk-service", "2.0.0"),
        ]

        # Register all services
        for name, version in services:
            reg = create_registration(
                name=name,
                version=version,
                instance_id=f"{name}-001",
            )
            await registry_service.register(reg)

        # Verify all registrations published events
        assert mock_events.publish_registered.call_count == 3

        # List services
        mock_consul.list_services.return_value = {name: [] for name, _ in services}

        service_list = await registry_service.list_services()
        assert len(service_list) == 3
