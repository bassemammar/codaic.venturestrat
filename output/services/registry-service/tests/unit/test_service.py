"""Tests for RegistryService - TDD approach.

Tests for the core registry service that orchestrates
Consul, health management, and event publishing.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from registry.models import (
    HealthStatus,
    Protocol,
    ServiceInstance,
    ServiceRegistration,
)
from registry.service import RegistryService


@pytest.fixture
def mock_consul_client():
    """Create mock ConsulClient."""
    client = AsyncMock()
    client.register = AsyncMock(return_value=True)
    client.deregister = AsyncMock(return_value=True)
    client.discover = AsyncMock(return_value=[])
    client.kv_put = AsyncMock(return_value=True)
    client.kv_get = AsyncMock(return_value=None)
    client.list_services = AsyncMock(return_value={})
    client.health_check = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_event_publisher():
    """Create mock EventPublisher."""
    publisher = AsyncMock()
    publisher.start = AsyncMock()
    publisher.stop = AsyncMock()
    publisher.publish_registered = AsyncMock()
    publisher.publish_deregistered = AsyncMock()
    publisher.publish_health_changed = AsyncMock()
    return publisher


@pytest.fixture
def mock_health_manager():
    """Create mock HealthManager."""
    manager = MagicMock()
    manager.get_status = MagicMock(return_value=None)
    manager.record_check = MagicMock(return_value=None)
    manager.clear_instance = MagicMock()
    return manager


@pytest.fixture
def registry_service(mock_consul_client, mock_event_publisher, mock_health_manager):
    """Create RegistryService with mocked dependencies."""
    service = RegistryService(
        consul_client=mock_consul_client,
        event_publisher=mock_event_publisher,
        health_manager=mock_health_manager,
    )
    return service


@pytest.fixture
def sample_registration():
    """Create sample registration."""
    return ServiceRegistration(
        name="test-service",
        version="1.0.0",
        instance_id="test-service-abc123",
        address="10.0.1.50",
        port=8080,
        protocol=Protocol.HTTP,
        tags=["production"],
        metadata={"team": "platform"},
    )


class TestRegistryServiceRegistration:
    """Tests for service registration flow."""

    @pytest.mark.asyncio
    async def test_register_service_success(
        self, registry_service, mock_consul_client, mock_event_publisher, sample_registration
    ):
        """Register service: validate -> consul -> event."""
        result = await registry_service.register(sample_registration)

        assert result is True
        mock_consul_client.register.assert_called_once_with(sample_registration)
        mock_event_publisher.publish_registered.assert_called_once_with(sample_registration)

    @pytest.mark.asyncio
    async def test_register_caches_manifest(
        self, registry_service, mock_consul_client, sample_registration
    ):
        """Registration caches manifest in Consul KV."""
        await registry_service.register(sample_registration)

        # Should store metadata in KV
        mock_consul_client.kv_put.assert_called()
        call_args = mock_consul_client.kv_put.call_args
        key = call_args[0][0]
        assert "test-service" in key

    @pytest.mark.asyncio
    async def test_register_from_manifest_file(
        self, registry_service, mock_consul_client, tmp_path
    ):
        """Register service from manifest.yaml file."""
        manifest_content = """
name: pricing-service
version: 1.2.0
description: Test service
depends:
  - market-data-service@^1.0.0
health:
  liveness: /health/live
  readiness: /health/ready
tags:
  - production
"""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(manifest_content)

        registration = await registry_service.register_from_manifest(
            manifest_path=manifest_file,
            instance_id="pricing-service-xyz",
            address="10.0.1.100",
            port=8080,
        )

        assert registration.name == "pricing-service"
        assert registration.version == "1.2.0"
        mock_consul_client.register.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_consul_failure_no_event(
        self, registry_service, mock_consul_client, mock_event_publisher, sample_registration
    ):
        """No event published if Consul registration fails."""
        mock_consul_client.register.side_effect = Exception("Consul error")

        with pytest.raises(Exception):
            await registry_service.register(sample_registration)

        mock_event_publisher.publish_registered.assert_not_called()


class TestRegistryServiceDeregistration:
    """Tests for service deregistration flow."""

    @pytest.mark.asyncio
    async def test_deregister_service_success(
        self, registry_service, mock_consul_client, mock_event_publisher, mock_health_manager
    ):
        """Deregister service: consul -> event -> cleanup."""
        result = await registry_service.deregister(
            instance_id="test-123",
            service_name="test-service",
            version="1.0.0",
            reason="graceful_shutdown",
        )

        assert result is True
        mock_consul_client.deregister.assert_called_once_with("test-123")
        mock_event_publisher.publish_deregistered.assert_called_once()
        mock_health_manager.clear_instance.assert_called_once_with("test-123")

    @pytest.mark.asyncio
    async def test_deregister_clears_kv(self, registry_service, mock_consul_client):
        """Deregistration clears KV cache."""
        await registry_service.deregister(
            instance_id="test-123",
            service_name="test-service",
            version="1.0.0",
        )

        mock_consul_client.kv_delete.assert_called()


class TestRegistryServiceDiscovery:
    """Tests for service discovery."""

    @pytest.mark.asyncio
    async def test_discover_services(self, registry_service, mock_consul_client):
        """Discover services by name."""
        mock_consul_client.discover.return_value = [
            ServiceInstance(
                name="test-service",
                version="1.0.0",
                instance_id="test-1",
                address="10.0.1.10",
                port=8080,
                protocol=Protocol.HTTP,
                health_status=HealthStatus.HEALTHY,
                tags=["production"],
                metadata={},
            ),
        ]

        instances = await registry_service.discover("test-service")

        assert len(instances) == 1
        assert instances[0].name == "test-service"

    @pytest.mark.asyncio
    async def test_discover_with_version_constraint(self, registry_service, mock_consul_client):
        """Discover services with version filtering."""
        mock_consul_client.discover.return_value = [
            ServiceInstance(
                name="test-service",
                version="1.0.0",
                instance_id="test-1",
                address="10.0.1.10",
                port=8080,
                protocol=Protocol.HTTP,
                health_status=HealthStatus.HEALTHY,
                tags=[],
                metadata={},
            ),
            ServiceInstance(
                name="test-service",
                version="2.0.0",
                instance_id="test-2",
                address="10.0.1.11",
                port=8080,
                protocol=Protocol.HTTP,
                health_status=HealthStatus.HEALTHY,
                tags=[],
                metadata={},
            ),
        ]

        instances = await registry_service.discover("test-service", version_constraint="^1.0.0")

        # Should only return v1.x.x
        assert len(instances) == 1
        assert instances[0].version == "1.0.0"

    @pytest.mark.asyncio
    async def test_discover_with_tags(self, registry_service, mock_consul_client):
        """Discover services filtered by tags."""
        await registry_service.discover("test-service", tags=["production"])

        call_args = mock_consul_client.discover.call_args
        query = call_args[0][0]
        assert query.tags == ["production"]

    @pytest.mark.asyncio
    async def test_discover_not_found(self, registry_service, mock_consul_client):
        """Handle no services found."""
        mock_consul_client.discover.return_value = []

        instances = await registry_service.discover("nonexistent-service")

        assert instances == []


class TestRegistryServiceListing:
    """Tests for service listing."""

    @pytest.mark.asyncio
    async def test_list_all_services(self, registry_service, mock_consul_client):
        """List all registered services."""
        mock_consul_client.list_services.return_value = {
            "pricing-service": ["production", "v1.0.0"],
            "market-data": ["production", "v2.0.0"],
        }

        services = await registry_service.list_services()

        assert "pricing-service" in services
        assert "market-data" in services

    @pytest.mark.asyncio
    async def test_get_service_info(self, registry_service, mock_consul_client):
        """Get detailed info about a service."""
        mock_consul_client.discover.return_value = [
            ServiceInstance(
                name="test-service",
                version="1.0.0",
                instance_id="test-1",
                address="10.0.1.10",
                port=8080,
                protocol=Protocol.HTTP,
                health_status=HealthStatus.HEALTHY,
                tags=["production"],
                metadata={"team": "platform"},
            ),
        ]

        info = await registry_service.get_service_info("test-service")

        assert info["name"] == "test-service"
        assert info["instance_count"] == 1
        assert info["healthy_count"] == 1


class TestRegistryServiceHealthIntegration:
    """Tests for health status integration."""

    @pytest.mark.asyncio
    async def test_get_health_overview(self, registry_service, mock_consul_client):
        """Get health overview of all services."""
        mock_consul_client.list_services.return_value = {
            "service-a": [],
            "service-b": [],
        }
        mock_consul_client.discover.return_value = [
            ServiceInstance(
                name="service-a",
                version="1.0.0",
                instance_id="a-1",
                address="10.0.1.10",
                port=8080,
                protocol=Protocol.HTTP,
                health_status=HealthStatus.HEALTHY,
                tags=[],
                metadata={},
            ),
        ]

        overview = await registry_service.get_health_overview()

        assert "services" in overview
        assert "total_instances" in overview
