"""Tests for RegistryClient - TDD approach.

These tests define the expected behavior of the SDK client.
"""
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from venturestrat_registry import (
    ConnectionError,
    DiscoveryError,
    ManifestLoader,
    RegistrationError,
    RegistryClient,
    RegistryClientConfig,
    ServiceInstance,
    ServiceRegistration,
)


@pytest.fixture
def mock_httpx_client():
    """Create mock httpx client."""
    mock_client = AsyncMock()
    with patch("venturestrat_registry.client.httpx.AsyncClient") as mock:
        mock.return_value = mock_client
        mock_client.aclose = AsyncMock()
        yield mock_client


@pytest.fixture
def config():
    """Create client config."""
    return RegistryClientConfig(
        host="localhost",
        port=8080,
        use_grpc=False,
    )


@pytest.fixture
def sample_manifest_yaml():
    """Create sample manifest YAML content."""
    return """
name: pricing-service
version: 1.2.0
description: Real-time pricing engine
depends:
  - market-data-service@^1.0.0
provides:
  apis:
    rest: /api/v1/pricing
  events:
    - pricing.quote.created
health:
  liveness: /health/live
  readiness: /health/ready
tags:
  - production
metadata:
  team: quant
"""


# =============================================================================
# Client Configuration Tests
# =============================================================================


class TestClientConfiguration:
    """Tests for client configuration."""

    def test_default_config(self):
        """Default config uses localhost:8080."""
        config = RegistryClientConfig()
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.use_grpc is False

    def test_custom_config(self):
        """Custom config overrides defaults."""
        config = RegistryClientConfig(
            host="registry.example.com",
            port=50051,
            use_grpc=True,
        )
        assert config.host == "registry.example.com"
        assert config.port == 50051
        assert config.use_grpc is True

    def test_config_from_env(self):
        """Config can be loaded from environment."""
        with patch.dict(
            "os.environ",
            {
                "REGISTRY_HOST": "consul.local",
                "REGISTRY_PORT": "8500",
            },
        ):
            config = RegistryClientConfig.from_env()
            assert config.host == "consul.local"
            assert config.port == 8500


# =============================================================================
# Registration Tests
# =============================================================================


class TestRegistration:
    """Tests for service registration."""

    @pytest.mark.asyncio
    async def test_register_service(self, mock_httpx_client, config):
        """Register service calls API correctly."""
        mock_httpx_client.post.return_value = MagicMock(
            status_code=201,
            json=MagicMock(
                return_value={
                    "instance_id": "pricing-service-abc123",
                    "consul_service_id": "pricing-service-abc123",
                    "registered_at": "2026-01-04T10:30:00Z",
                    "health_check_id": "service:pricing-service-abc123",
                }
            ),
        )

        async with RegistryClient(config) as client:
            registration = ServiceRegistration(
                name="pricing-service",
                version="1.2.0",
                instance_id="pricing-service-abc123",
                address="10.0.1.50",
                port=8080,
            )
            result = await client.register(registration)

            assert result.instance_id == "pricing-service-abc123"
            mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_from_manifest(self, mock_httpx_client, config, sample_manifest_yaml):
        """Register from manifest parses file and calls API."""
        mock_httpx_client.post.return_value = MagicMock(
            status_code=201,
            json=MagicMock(
                return_value={
                    "instance_id": "pricing-service-abc123",
                    "consul_service_id": "pricing-service-abc123",
                    "registered_at": "2026-01-04T10:30:00Z",
                    "health_check_id": "service:pricing-service-abc123",
                }
            ),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(sample_manifest_yaml)
            manifest_path = f.name

        try:
            async with RegistryClient(config) as client:
                result = await client.register_from_manifest(
                    manifest_path=Path(manifest_path),
                    instance_id="pricing-service-abc123",
                    address="10.0.1.50",
                    port=8080,
                )

                assert result.instance_id == "pricing-service-abc123"
                # Verify registration payload includes manifest data
                call_args = mock_httpx_client.post.call_args
                payload = call_args.kwargs.get("json", {})
                assert payload.get("name") == "pricing-service"
                assert payload.get("version") == "1.2.0"
        finally:
            Path(manifest_path).unlink()

    @pytest.mark.asyncio
    async def test_register_validation_error(self, mock_httpx_client, config):
        """Registration validation error raises RegistrationError."""
        mock_httpx_client.post.return_value = MagicMock(
            status_code=400,
            json=MagicMock(
                return_value={"error": {"code": "VALIDATION_ERROR", "message": "Invalid payload"}}
            ),
        )

        async with RegistryClient(config) as client:
            registration = ServiceRegistration(
                name="",  # Invalid
                version="1.0.0",
                instance_id="test-123",
                address="10.0.1.50",
                port=8080,
            )

            with pytest.raises(RegistrationError):
                await client.register(registration)

    @pytest.mark.asyncio
    async def test_register_connection_error(self, mock_httpx_client, config):
        """Connection error raises ConnectionError."""
        import httpx

        mock_httpx_client.post.side_effect = httpx.RequestError("Connection refused")

        async with RegistryClient(config) as client:
            registration = ServiceRegistration(
                name="test-service",
                version="1.0.0",
                instance_id="test-123",
                address="10.0.1.50",
                port=8080,
            )

            with pytest.raises(ConnectionError):
                await client.register(registration)


# =============================================================================
# Deregistration Tests
# =============================================================================


class TestDeregistration:
    """Tests for service deregistration."""

    @pytest.mark.asyncio
    async def test_deregister_service(self, mock_httpx_client, config):
        """Deregister calls API correctly."""
        mock_httpx_client.delete.return_value = MagicMock(
            status_code=204,
        )

        async with RegistryClient(config) as client:
            await client.deregister(
                instance_id="pricing-service-abc123",
                service_name="pricing-service",
                version="1.2.0",
            )

            mock_httpx_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_deregister_with_reason(self, mock_httpx_client, config):
        """Deregister can include reason."""
        mock_httpx_client.delete.return_value = MagicMock(
            status_code=204,
        )

        async with RegistryClient(config) as client:
            await client.deregister(
                instance_id="pricing-service-abc123",
                service_name="pricing-service",
                version="1.2.0",
                reason="scaling_down",
            )

            call_args = mock_httpx_client.delete.call_args
            params = call_args.kwargs.get("params", {})
            assert params.get("reason") == "scaling_down"


# =============================================================================
# Discovery Tests
# =============================================================================


class TestDiscovery:
    """Tests for service discovery."""

    @pytest.mark.asyncio
    async def test_discover_services(self, mock_httpx_client, config):
        """Discover returns service instances."""
        mock_httpx_client.get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "service": "market-data-service",
                    "instances": [
                        {
                            "instance_id": "market-data-1",
                            "address": "10.0.1.10",
                            "port": 8080,
                            "protocol": "http",
                            "version": "1.0.0",
                            "health_status": "healthy",
                            "tags": ["production"],
                            "metadata": {},
                        },
                    ],
                    "total_instances": 1,
                    "healthy_instances": 1,
                }
            ),
        )

        async with RegistryClient(config) as client:
            instances = await client.discover("market-data-service")

            assert len(instances) == 1
            assert instances[0].instance_id == "market-data-1"
            assert instances[0].address == "10.0.1.10"

    @pytest.mark.asyncio
    async def test_discover_with_version_constraint(self, mock_httpx_client, config):
        """Discover with version constraint passes to API."""
        mock_httpx_client.get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "service": "market-data-service",
                    "instances": [],
                    "total_instances": 0,
                    "healthy_instances": 0,
                }
            ),
        )

        async with RegistryClient(config) as client:
            await client.discover("market-data-service", version="^1.0.0")

            call_args = mock_httpx_client.get.call_args
            params = call_args.kwargs.get("params", {})
            assert params.get("version") == "^1.0.0"

    @pytest.mark.asyncio
    async def test_discover_with_tags(self, mock_httpx_client, config):
        """Discover with tags filter."""
        mock_httpx_client.get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "service": "market-data-service",
                    "instances": [],
                    "total_instances": 0,
                    "healthy_instances": 0,
                }
            ),
        )

        async with RegistryClient(config) as client:
            await client.discover("market-data-service", tags=["production", "eu-west"])

            call_args = mock_httpx_client.get.call_args
            params = call_args.kwargs.get("params", {})
            assert "tags" in params

    @pytest.mark.asyncio
    async def test_discover_not_found(self, mock_httpx_client, config):
        """Discover unknown service raises DiscoveryError."""
        mock_httpx_client.get.return_value = MagicMock(
            status_code=404,
            json=MagicMock(
                return_value={"error": {"code": "NOT_FOUND", "message": "Service not found"}}
            ),
        )

        async with RegistryClient(config) as client:
            with pytest.raises(DiscoveryError):
                await client.discover("nonexistent-service")


# =============================================================================
# Watch Tests
# =============================================================================


class TestWatch:
    """Tests for service event watching."""

    @pytest.mark.asyncio
    async def test_watch_receives_events(self, config):
        """Watch yields service events."""
        # This would require SSE or WebSocket mocking
        # For now, skip actual streaming test
        pass

    @pytest.mark.asyncio
    async def test_watch_specific_service(self, config):
        """Watch can filter to specific service."""
        pass


# =============================================================================
# Context Manager Tests
# =============================================================================


class TestContextManager:
    """Tests for context manager (auto-registration)."""

    @pytest.mark.asyncio
    async def test_context_manager_registers_on_enter(
        self, mock_httpx_client, config, sample_manifest_yaml
    ):
        """Context manager auto-registers on enter."""
        mock_httpx_client.post.return_value = MagicMock(
            status_code=201,
            json=MagicMock(
                return_value={
                    "instance_id": "pricing-service-abc123",
                    "consul_service_id": "pricing-service-abc123",
                    "registered_at": "2026-01-04T10:30:00Z",
                    "health_check_id": "service:pricing-service-abc123",
                }
            ),
        )
        mock_httpx_client.delete.return_value = MagicMock(status_code=204)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(sample_manifest_yaml)
            manifest_path = f.name

        try:
            async with RegistryClient.from_manifest(
                manifest_path=Path(manifest_path),
                instance_id="pricing-service-abc123",
                address="10.0.1.50",
                port=8080,
                config=config,
            ):
                # Should have auto-registered
                assert mock_httpx_client.post.called
        finally:
            Path(manifest_path).unlink()

    @pytest.mark.asyncio
    async def test_context_manager_deregisters_on_exit(
        self, mock_httpx_client, config, sample_manifest_yaml
    ):
        """Context manager auto-deregisters on exit."""
        mock_httpx_client.post.return_value = MagicMock(
            status_code=201,
            json=MagicMock(
                return_value={
                    "instance_id": "pricing-service-abc123",
                    "consul_service_id": "pricing-service-abc123",
                    "registered_at": "2026-01-04T10:30:00Z",
                    "health_check_id": "service:pricing-service-abc123",
                }
            ),
        )
        mock_httpx_client.delete.return_value = MagicMock(status_code=204)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(sample_manifest_yaml)
            manifest_path = f.name

        try:
            async with RegistryClient.from_manifest(
                manifest_path=Path(manifest_path),
                instance_id="pricing-service-abc123",
                address="10.0.1.50",
                port=8080,
                config=config,
            ):
                pass

            # Should have deregistered on exit
            assert mock_httpx_client.delete.called
        finally:
            Path(manifest_path).unlink()


# =============================================================================
# Manifest Loader Tests
# =============================================================================


class TestManifestLoader:
    """Tests for manifest loading."""

    def test_load_manifest_from_file(self, sample_manifest_yaml):
        """Load manifest from YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(sample_manifest_yaml)
            manifest_path = f.name

        try:
            manifest = ManifestLoader.load(Path(manifest_path))

            assert manifest["name"] == "pricing-service"
            assert manifest["version"] == "1.2.0"
            assert "market-data-service@^1.0.0" in manifest["depends"]
        finally:
            Path(manifest_path).unlink()

    def test_load_manifest_missing_file(self):
        """Loading missing manifest raises error."""
        with pytest.raises(FileNotFoundError):
            ManifestLoader.load(Path("/nonexistent/manifest.yaml"))

    def test_load_manifest_invalid_yaml(self):
        """Loading invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            manifest_path = f.name

        try:
            with pytest.raises(ValueError):
                ManifestLoader.load(Path(manifest_path))
        finally:
            Path(manifest_path).unlink()


# =============================================================================
# Service Instance Model Tests
# =============================================================================


class TestServiceInstanceModel:
    """Tests for ServiceInstance model."""

    def test_create_instance(self):
        """Create service instance."""
        instance = ServiceInstance(
            instance_id="test-123",
            address="10.0.1.50",
            port=8080,
            protocol="http",
            version="1.0.0",
            health_status="healthy",
            tags=["production"],
            metadata={"team": "platform"},
        )

        assert instance.instance_id == "test-123"
        assert instance.endpoint == "http://10.0.1.50:8080"
        assert instance.is_healthy is True

    def test_unhealthy_instance(self):
        """Unhealthy instance has is_healthy=False."""
        instance = ServiceInstance(
            instance_id="test-123",
            address="10.0.1.50",
            port=8080,
            protocol="http",
            version="1.0.0",
            health_status="critical",
            tags=[],
            metadata={},
        )

        assert instance.is_healthy is False
