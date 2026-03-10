"""Test configuration and fixtures for registry-service SDK."""

from unittest.mock import AsyncMock, Mock

import grpc
import pytest

from venturestrat_registry_service import (
    AsyncRegistryServiceClient,
    RegistryServiceClient,
    RegistryServiceConfig,
)


@pytest.fixture()
def mock_grpc_channel():
    """Mock gRPC channel."""
    channel = Mock(spec=grpc.Channel)
    channel.get_state.return_value = grpc.ChannelConnectivity.READY
    channel.close = Mock()
    return channel


@pytest.fixture()
def mock_async_grpc_channel():
    """Mock async gRPC channel."""
    channel = AsyncMock(spec=grpc.aio.Channel)
    channel.get_state.return_value = grpc.ChannelConnectivity.READY
    channel.close = AsyncMock()
    channel.wait_for_state_change = AsyncMock()
    return channel


@pytest.fixture()
def client_config():
    """Basic client configuration."""
    return RegistryServiceConfig(
        host="localhost", port=50051, secure=False, timeout=30.0
    )


@pytest.fixture()
def mock_client(client_config, mock_grpc_channel):
    """Mock synchronous client."""
    with pytest.mock.patch("grpc.insecure_channel", return_value=mock_grpc_channel):
        client = RegistryServiceClient.from_config(client_config)
        yield client


@pytest.fixture()
async def mock_async_client(client_config, mock_async_grpc_channel):
    """Mock asynchronous client."""
    with pytest.mock.patch(
        "grpc.aio.insecure_channel", return_value=mock_async_grpc_channel
    ):
        client = AsyncRegistryServiceClient.from_config(client_config)
        await client._connect()
        yield client
        await client.close()


@pytest.fixture()
def sample_metadata() -> dict[str, str]:
    """Sample metadata for testing."""
    return {"x-request-id": "test-request-123", "x-trace-id": "test-trace-456"}


@pytest.fixture()
def grpc_error():
    """Sample gRPC error."""
    return grpc.RpcError()


@pytest.fixture()
def async_grpc_error():
    """Sample async gRPC error."""
    return grpc.aio.AioRpcError()
