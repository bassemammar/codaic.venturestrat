"""Tests for ConsulClient - TDD approach.

These tests define the expected behavior of the Consul client
for service registration and discovery.
"""
from unittest.mock import MagicMock, patch

import pytest
from registry.consul_client import (
    ConsulClient,
    ConsulOperationError,
)
from registry.models import (
    HealthCheckConfig,
    HealthStatus,
    Protocol,
    ServiceInstance,
    ServiceQuery,
    ServiceRegistration,
)


@pytest.fixture
def mock_consul():
    """Create a mock Consul client."""
    with patch("registry.consul_client.consul.Consul") as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def consul_client(mock_consul):
    """Create ConsulClient with mocked Consul."""
    return ConsulClient(host="localhost", port=8500)


@pytest.fixture
def sample_registration():
    """Create a sample service registration."""
    return ServiceRegistration(
        name="test-service",
        version="1.0.0",
        instance_id="test-service-abc123",
        address="10.0.1.50",
        port=8080,
        protocol=Protocol.HTTP,
        tags=["production", "api"],
        metadata={"team": "platform"},
        health_check=HealthCheckConfig(
            http_endpoint="/health/ready",
            interval_seconds=10,
            timeout_seconds=5,
        ),
    )


class TestConsulClientConnection:
    """Tests for Consul connection management."""

    def test_create_client_with_defaults(self):
        """Create client with default settings."""
        with patch("registry.consul_client.consul.Consul"):
            client = ConsulClient()
            assert client.host == "localhost"
            assert client.port == 8500

    def test_create_client_with_custom_host(self):
        """Create client with custom host and port."""
        with patch("registry.consul_client.consul.Consul"):
            client = ConsulClient(host="consul.example.com", port=8501)
            assert client.host == "consul.example.com"
            assert client.port == 8501

    @pytest.mark.asyncio
    async def test_health_check_success(self, consul_client, mock_consul):
        """Health check returns True when Consul is healthy."""
        mock_consul.status.leader.return_value = "10.0.0.1:8300"

        is_healthy = await consul_client.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, consul_client, mock_consul):
        """Health check returns False when Consul is unavailable."""
        mock_consul.status.leader.side_effect = Exception("Connection refused")

        is_healthy = await consul_client.health_check()

        assert is_healthy is False


class TestConsulClientRegistration:
    """Tests for service registration."""

    @pytest.mark.asyncio
    async def test_register_service_success(self, consul_client, mock_consul, sample_registration):
        """Successfully register a service."""
        mock_consul.agent.service.register.return_value = True

        result = await consul_client.register(sample_registration)

        assert result is True
        mock_consul.agent.service.register.assert_called_once()

        # Verify registration payload
        call_kwargs = mock_consul.agent.service.register.call_args[1]
        assert call_kwargs["service_id"] == "test-service-abc123"
        assert call_kwargs["name"] == "test-service"
        assert call_kwargs["address"] == "10.0.1.50"
        assert call_kwargs["port"] == 8080

    @pytest.mark.asyncio
    async def test_register_service_with_health_check(
        self, consul_client, mock_consul, sample_registration
    ):
        """Register service includes health check configuration."""
        mock_consul.agent.service.register.return_value = True

        await consul_client.register(sample_registration)

        call_kwargs = mock_consul.agent.service.register.call_args[1]
        check = call_kwargs.get("check")
        assert check is not None
        assert "http" in check.get("http", "").lower() or "HTTP" in call_kwargs.get("check", {})

    @pytest.mark.asyncio
    async def test_register_service_with_tags(
        self, consul_client, mock_consul, sample_registration
    ):
        """Register service includes tags."""
        mock_consul.agent.service.register.return_value = True

        await consul_client.register(sample_registration)

        call_kwargs = mock_consul.agent.service.register.call_args[1]
        tags = call_kwargs.get("tags", [])
        assert "production" in tags
        assert "api" in tags

    @pytest.mark.asyncio
    async def test_register_service_with_metadata(
        self, consul_client, mock_consul, sample_registration
    ):
        """Register service includes metadata."""
        mock_consul.agent.service.register.return_value = True

        await consul_client.register(sample_registration)

        call_kwargs = mock_consul.agent.service.register.call_args[1]
        meta = call_kwargs.get("meta", {})
        assert meta.get("team") == "platform"
        assert meta.get("version") == "1.0.0"

    @pytest.mark.asyncio
    async def test_register_service_failure(self, consul_client, mock_consul, sample_registration):
        """Handle registration failure."""
        mock_consul.agent.service.register.side_effect = Exception("Consul error")

        with pytest.raises(ConsulOperationError) as exc_info:
            await consul_client.register(sample_registration)

        assert "register" in str(exc_info.value).lower()


class TestConsulClientDeregistration:
    """Tests for service deregistration."""

    @pytest.mark.asyncio
    async def test_deregister_service_success(self, consul_client, mock_consul):
        """Successfully deregister a service."""
        mock_consul.agent.service.deregister.return_value = True

        result = await consul_client.deregister("test-service-abc123")

        assert result is True
        mock_consul.agent.service.deregister.assert_called_once_with("test-service-abc123")

    @pytest.mark.asyncio
    async def test_deregister_service_not_found(self, consul_client, mock_consul):
        """Handle deregistration of non-existent service."""
        mock_consul.agent.service.deregister.return_value = True

        # Should not raise - deregistering non-existent is idempotent
        result = await consul_client.deregister("nonexistent-service")

        assert result is True

    @pytest.mark.asyncio
    async def test_deregister_service_failure(self, consul_client, mock_consul):
        """Handle deregistration failure."""
        mock_consul.agent.service.deregister.side_effect = Exception("Consul error")

        with pytest.raises(ConsulOperationError):
            await consul_client.deregister("test-service-abc123")


class TestConsulClientDiscovery:
    """Tests for service discovery."""

    @pytest.mark.asyncio
    async def test_discover_services_by_name(self, consul_client, mock_consul):
        """Discover services by name."""
        mock_consul.health.service.return_value = (
            None,
            [
                {
                    "Service": {
                        "ID": "test-service-1",
                        "Service": "test-service",
                        "Address": "10.0.1.10",
                        "Port": 8080,
                        "Tags": ["production", "v1.0.0"],
                        "Meta": {"version": "1.0.0", "protocol": "http"},
                    },
                    "Checks": [{"Status": "passing"}],
                },
                {
                    "Service": {
                        "ID": "test-service-2",
                        "Service": "test-service",
                        "Address": "10.0.1.11",
                        "Port": 8080,
                        "Tags": ["production", "v1.0.0"],
                        "Meta": {"version": "1.0.0", "protocol": "http"},
                    },
                    "Checks": [{"Status": "passing"}],
                },
            ],
        )

        query = ServiceQuery(name="test-service")
        instances = await consul_client.discover(query)

        assert len(instances) == 2
        assert all(isinstance(i, ServiceInstance) for i in instances)
        assert instances[0].name == "test-service"
        assert instances[0].address == "10.0.1.10"

    @pytest.mark.asyncio
    async def test_discover_services_healthy_only(self, consul_client, mock_consul):
        """Discover only healthy services."""
        mock_consul.health.service.return_value = (
            None,
            [
                {
                    "Service": {
                        "ID": "healthy-1",
                        "Service": "test-service",
                        "Address": "10.0.1.10",
                        "Port": 8080,
                        "Tags": [],
                        "Meta": {"version": "1.0.0", "protocol": "http"},
                    },
                    "Checks": [{"Status": "passing"}],
                },
            ],
        )

        query = ServiceQuery(name="test-service", healthy_only=True)
        instances = await consul_client.discover(query)

        # Should only return healthy instances
        assert len(instances) == 1
        assert instances[0].health_status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_discover_services_with_tags(self, consul_client, mock_consul):
        """Discover services filtered by tags."""
        mock_consul.health.service.return_value = (None, [])

        query = ServiceQuery(name="test-service", tags=["production"])
        await consul_client.discover(query)

        # Verify tag was passed to Consul
        call_args = mock_consul.health.service.call_args
        assert "production" in str(call_args)

    @pytest.mark.asyncio
    async def test_discover_services_not_found(self, consul_client, mock_consul):
        """Handle no services found."""
        mock_consul.health.service.return_value = (None, [])

        query = ServiceQuery(name="nonexistent-service")
        instances = await consul_client.discover(query)

        assert instances == []

    @pytest.mark.asyncio
    async def test_discover_services_failure(self, consul_client, mock_consul):
        """Handle discovery failure."""
        mock_consul.health.service.side_effect = Exception("Consul error")

        query = ServiceQuery(name="test-service")
        with pytest.raises(ConsulOperationError):
            await consul_client.discover(query)


class TestConsulClientKV:
    """Tests for Consul KV operations."""

    @pytest.mark.asyncio
    async def test_kv_put_success(self, consul_client, mock_consul):
        """Store value in KV."""
        mock_consul.kv.put.return_value = True

        result = await consul_client.kv_put("venturestrat/services/test/manifest", '{"name": "test"}')

        assert result is True
        mock_consul.kv.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_kv_get_success(self, consul_client, mock_consul):
        """Retrieve value from KV."""
        mock_consul.kv.get.return_value = (None, {"Value": b'{"name": "test"}'})

        value = await consul_client.kv_get("venturestrat/services/test/manifest")

        assert value == '{"name": "test"}'

    @pytest.mark.asyncio
    async def test_kv_get_not_found(self, consul_client, mock_consul):
        """Handle KV key not found."""
        mock_consul.kv.get.return_value = (None, None)

        value = await consul_client.kv_get("venturestrat/services/nonexistent")

        assert value is None

    @pytest.mark.asyncio
    async def test_kv_delete_success(self, consul_client, mock_consul):
        """Delete key from KV."""
        mock_consul.kv.delete.return_value = True

        result = await consul_client.kv_delete("venturestrat/services/test/manifest")

        assert result is True

    @pytest.mark.asyncio
    async def test_kv_list_keys(self, consul_client, mock_consul):
        """List keys under a prefix."""
        mock_consul.kv.get.return_value = (
            None,
            [
                {"Key": "venturestrat/services/svc1/manifest"},
                {"Key": "venturestrat/services/svc2/manifest"},
            ],
        )

        keys = await consul_client.kv_list("venturestrat/services/")

        assert len(keys) == 2


class TestConsulClientCatalog:
    """Tests for Consul catalog operations."""

    @pytest.mark.asyncio
    async def test_list_services(self, consul_client, mock_consul):
        """List all registered services."""
        mock_consul.catalog.services.return_value = (
            None,
            {
                "test-service": ["production", "api"],
                "market-data": ["production"],
                "consul": [],
            },
        )

        services = await consul_client.list_services()

        assert "test-service" in services
        assert "market-data" in services
        # Consul service should be excluded
        assert "consul" not in services

    @pytest.mark.asyncio
    async def test_get_service_instances(self, consul_client, mock_consul):
        """Get all instances of a service."""
        mock_consul.catalog.service.return_value = (
            None,
            [
                {
                    "ServiceID": "test-1",
                    "ServiceName": "test-service",
                    "ServiceAddress": "10.0.1.10",
                    "ServicePort": 8080,
                    "ServiceTags": ["v1.0.0"],
                    "ServiceMeta": {"version": "1.0.0"},
                },
            ],
        )

        instances = await consul_client.get_service_instances("test-service")

        assert len(instances) == 1
        assert instances[0]["ServiceID"] == "test-1"
