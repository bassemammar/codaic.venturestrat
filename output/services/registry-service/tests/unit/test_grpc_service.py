"""Tests for gRPC Registry Service - TDD approach.

These tests define the expected behavior of the gRPC service.
"""
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from registry.api.grpc_service import RegistryGrpcService
from registry.consul_client import ConsulOperationError
from registry.grpc import (
    DeregisterRequest,
    DiscoverRequest,
    GetHealthRequest,
    GetServiceHealthRequest,
    HeartbeatRequest,
    ListServicesRequest,
    RegisterRequest,
    WatchRequest,
)
from registry.grpc import (
    HealthCheckConfig as GrpcHealthCheckConfig,
)
from registry.models import (
    HealthStatus,
    Protocol,
    ServiceInstance,
)


@pytest.fixture
def mock_registry_service():
    """Create a mock RegistryService."""
    service = AsyncMock()
    return service


@pytest.fixture
def grpc_service(mock_registry_service):
    """Create gRPC service with mocked registry."""
    return RegistryGrpcService(mock_registry_service)


@pytest.fixture
def mock_context():
    """Create a mock gRPC context."""
    context = MagicMock(spec=grpc.ServicerContext)
    context.set_code = MagicMock()
    context.set_details = MagicMock()
    return context


@pytest.fixture
def sample_register_request():
    """Create sample registration request."""
    return RegisterRequest(
        name="pricing-service",
        version="1.2.0",
        instance_id="pricing-service-abc123",
        address="10.0.1.50",
        port=8080,
        protocol="http",
        depends=["market-data-service@^1.0.0"],
        metadata={"team": "quant"},
        health_check=GrpcHealthCheckConfig(
            http_endpoint="/health/ready",
            interval_seconds=10,
            timeout_seconds=5,
            deregister_after_seconds=60,
        ),
        tags=["production", "eu-west"],
    )


@pytest.fixture
def sample_service_instance():
    """Create sample service instance."""
    return ServiceInstance(
        name="pricing-service",
        version="1.2.0",
        instance_id="pricing-service-abc123",
        address="10.0.1.50",
        port=8080,
        protocol=Protocol.HTTP,
        health_status=HealthStatus.HEALTHY,
        tags=["production", "eu-west"],
        metadata={"team": "quant"},
    )


# =============================================================================
# Register RPC Tests
# =============================================================================


class TestRegisterRpc:
    """Tests for Register RPC."""

    @pytest.mark.asyncio
    async def test_register_success(
        self, grpc_service, mock_registry_service, sample_register_request, mock_context
    ):
        """Successful registration returns RegisterResponse."""
        mock_registry_service.register.return_value = True

        response = await grpc_service.Register(sample_register_request, mock_context)

        assert response.instance_id == "pricing-service-abc123"
        assert response.consul_service_id == "pricing-service-abc123"
        assert response.health_check_id == "service:pricing-service-abc123"
        assert response.registered_at != ""
        mock_registry_service.register.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_validation_error(
        self, grpc_service, mock_registry_service, mock_context
    ):
        """Invalid request sets INVALID_ARGUMENT status."""
        request = RegisterRequest(
            name="",  # Invalid: empty name
            version="1.0.0",
            instance_id="test-123",
            address="10.0.1.50",
            port=8080,
        )

        await grpc_service.Register(request, mock_context)

        mock_context.set_code.assert_called_with(grpc.StatusCode.INVALID_ARGUMENT)

    @pytest.mark.asyncio
    async def test_register_consul_error(
        self, grpc_service, mock_registry_service, sample_register_request, mock_context
    ):
        """Consul error sets UNAVAILABLE status."""
        mock_registry_service.register.side_effect = ConsulOperationError("Connection refused")

        await grpc_service.Register(sample_register_request, mock_context)

        mock_context.set_code.assert_called_with(grpc.StatusCode.UNAVAILABLE)

    @pytest.mark.asyncio
    async def test_register_with_health_check_config(
        self, grpc_service, mock_registry_service, mock_context
    ):
        """Registration includes health check configuration."""
        request = RegisterRequest(
            name="test-service",
            version="1.0.0",
            instance_id="test-123",
            address="10.0.1.50",
            port=8080,
            protocol="http",
            health_check=GrpcHealthCheckConfig(
                http_endpoint="/health",
                interval_seconds=15,
                timeout_seconds=3,
            ),
        )
        mock_registry_service.register.return_value = True

        await grpc_service.Register(request, mock_context)

        call_args = mock_registry_service.register.call_args[0][0]
        assert call_args.health_check.http_endpoint == "/health"
        assert call_args.health_check.interval_seconds == 15


# =============================================================================
# Deregister RPC Tests
# =============================================================================


class TestDeregisterRpc:
    """Tests for Deregister RPC."""

    @pytest.mark.asyncio
    async def test_deregister_success(self, grpc_service, mock_registry_service, mock_context):
        """Successful deregistration returns DeregisterResponse."""
        mock_registry_service.deregister.return_value = True

        request = DeregisterRequest(
            instance_id="pricing-service-abc123",
            service_name="pricing-service",
            version="1.2.0",
            reason="graceful_shutdown",
        )

        response = await grpc_service.Deregister(request, mock_context)

        assert response.success is True
        assert response.deregistered_at != ""
        mock_registry_service.deregister.assert_called_once()

    @pytest.mark.asyncio
    async def test_deregister_with_reason(self, grpc_service, mock_registry_service, mock_context):
        """Deregistration includes reason."""
        mock_registry_service.deregister.return_value = True

        request = DeregisterRequest(
            instance_id="pricing-service-abc123",
            service_name="pricing-service",
            version="1.2.0",
            reason="scaling_down",
        )

        await grpc_service.Deregister(request, mock_context)

        call_kwargs = mock_registry_service.deregister.call_args.kwargs
        assert call_kwargs["reason"] == "scaling_down"


# =============================================================================
# Discover RPC Tests
# =============================================================================


class TestDiscoverRpc:
    """Tests for Discover RPC."""

    @pytest.mark.asyncio
    async def test_discover_returns_instances(
        self, grpc_service, mock_registry_service, sample_service_instance, mock_context
    ):
        """Discover returns matching instances."""
        mock_registry_service.discover.return_value = [sample_service_instance]

        request = DiscoverRequest(
            service_name="pricing-service",
            healthy_only=True,
        )

        response = await grpc_service.Discover(request, mock_context)

        assert response.service == "pricing-service"
        assert len(response.instances) == 1
        assert response.instances[0].instance_id == "pricing-service-abc123"
        assert response.total_instances == 1
        assert response.healthy_instances == 1

    @pytest.mark.asyncio
    async def test_discover_with_version_constraint(
        self, grpc_service, mock_registry_service, sample_service_instance, mock_context
    ):
        """Discover applies version constraint."""
        mock_registry_service.discover.return_value = [sample_service_instance]

        request = DiscoverRequest(
            service_name="pricing-service",
            version_constraint="^1.0.0",
            healthy_only=True,
        )

        await grpc_service.Discover(request, mock_context)

        call_kwargs = mock_registry_service.discover.call_args.kwargs
        assert call_kwargs["version_constraint"] == "^1.0.0"

    @pytest.mark.asyncio
    async def test_discover_with_tags(
        self, grpc_service, mock_registry_service, sample_service_instance, mock_context
    ):
        """Discover filters by tags."""
        mock_registry_service.discover.return_value = [sample_service_instance]

        request = DiscoverRequest(
            service_name="pricing-service",
            tags=["production", "eu-west"],
            healthy_only=True,
        )

        await grpc_service.Discover(request, mock_context)

        call_kwargs = mock_registry_service.discover.call_args.kwargs
        assert call_kwargs["tags"] == ["production", "eu-west"]

    @pytest.mark.asyncio
    async def test_discover_not_found(self, grpc_service, mock_registry_service, mock_context):
        """Discover with no results sets NOT_FOUND status."""
        mock_registry_service.discover.return_value = []

        request = DiscoverRequest(
            service_name="nonexistent-service",
            healthy_only=True,
        )

        await grpc_service.Discover(request, mock_context)

        mock_context.set_code.assert_called_with(grpc.StatusCode.NOT_FOUND)


# =============================================================================
# Watch RPC Tests
# =============================================================================


class TestWatchRpc:
    """Tests for Watch streaming RPC."""

    @pytest.mark.asyncio
    async def test_watch_receives_events(self, grpc_service, mock_registry_service, mock_context):
        """Watch stream receives service events."""
        # Create mock event queue
        events = [
            {
                "event_type": "registered",
                "service_name": "pricing-service",
                "instance_id": "pricing-123",
                "version": "1.0.0",
            },
            {
                "event_type": "health_changed",
                "service_name": "pricing-service",
                "instance_id": "pricing-123",
                "version": "1.0.0",
            },
        ]
        mock_registry_service.subscribe_events = MagicMock(return_value=iter(events))

        request = WatchRequest(service_name="pricing-service")

        received_events = []
        async for event in grpc_service.Watch(request, mock_context):
            received_events.append(event)
            if len(received_events) >= 2:
                break

        assert len(received_events) == 2
        assert received_events[0].event_type == "registered"
        assert received_events[1].event_type == "health_changed"

    @pytest.mark.asyncio
    async def test_watch_all_services(self, grpc_service, mock_registry_service, mock_context):
        """Watch with empty service_name watches all services."""
        events = [
            {
                "event_type": "registered",
                "service_name": "pricing-service",
                "instance_id": "pricing-123",
                "version": "1.0.0",
            },
        ]
        mock_registry_service.subscribe_events = MagicMock(return_value=iter(events))

        request = WatchRequest(service_name="")  # Empty = watch all

        async for event in grpc_service.Watch(request, mock_context):
            assert event.service_name == "pricing-service"
            break


# =============================================================================
# Heartbeat RPC Tests
# =============================================================================


class TestHeartbeatRpc:
    """Tests for Heartbeat RPC."""

    @pytest.mark.asyncio
    async def test_heartbeat_success(self, grpc_service, mock_registry_service, mock_context):
        """Heartbeat returns status."""
        request = HeartbeatRequest(
            instance_id="pricing-service-abc123",
            status="passing",
        )

        response = await grpc_service.Heartbeat(request, mock_context)

        assert response.instance_id == "pricing-service-abc123"
        assert response.status == "passing"
        assert response.last_heartbeat != ""


# =============================================================================
# ListServices RPC Tests
# =============================================================================


class TestListServicesRpc:
    """Tests for ListServices RPC."""

    @pytest.mark.asyncio
    async def test_list_services_returns_all(
        self, grpc_service, mock_registry_service, mock_context
    ):
        """ListServices returns all services."""
        mock_registry_service.list_services.return_value = {
            "pricing-service": ["production"],
            "market-data-service": ["production"],
        }
        mock_registry_service.get_service_info.side_effect = [
            {
                "name": "pricing-service",
                "versions": ["1.2.0"],
                "instance_count": 3,
                "healthy_count": 3,
            },
            {
                "name": "market-data-service",
                "versions": ["1.0.0"],
                "instance_count": 5,
                "healthy_count": 4,
            },
        ]

        request = ListServicesRequest()

        response = await grpc_service.ListServices(request, mock_context)

        assert response.total_services == 2
        assert len(response.services) == 2


# =============================================================================
# GetHealth RPC Tests
# =============================================================================


class TestGetHealthRpc:
    """Tests for GetHealth RPC."""

    @pytest.mark.asyncio
    async def test_get_health_returns_overview(
        self, grpc_service, mock_registry_service, mock_context
    ):
        """GetHealth returns health overview."""
        mock_registry_service.get_health_overview.return_value = {
            "services": {
                "pricing-service": {"total": 3, "healthy": 3, "unhealthy": 0},
            },
            "total_instances": 3,
            "healthy_instances": 3,
            "unhealthy_instances": 0,
        }

        request = GetHealthRequest()

        response = await grpc_service.GetHealth(request, mock_context)

        assert response.overall_status == "healthy"
        assert len(response.services) == 1


# =============================================================================
# GetServiceHealth RPC Tests
# =============================================================================


class TestGetServiceHealthRpc:
    """Tests for GetServiceHealth RPC."""

    @pytest.mark.asyncio
    async def test_get_service_health_returns_details(
        self, grpc_service, mock_registry_service, sample_service_instance, mock_context
    ):
        """GetServiceHealth returns detailed instance health."""
        mock_registry_service.discover.return_value = [sample_service_instance]

        request = GetServiceHealthRequest(service_name="pricing-service")

        response = await grpc_service.GetServiceHealth(request, mock_context)

        assert response.service == "pricing-service"
        assert response.status == "healthy"
        assert len(response.instances) == 1

    @pytest.mark.asyncio
    async def test_get_service_health_not_found(
        self, grpc_service, mock_registry_service, mock_context
    ):
        """GetServiceHealth for unknown service sets NOT_FOUND."""
        mock_registry_service.discover.return_value = []

        request = GetServiceHealthRequest(service_name="nonexistent-service")

        await grpc_service.GetServiceHealth(request, mock_context)

        mock_context.set_code.assert_called_with(grpc.StatusCode.NOT_FOUND)
