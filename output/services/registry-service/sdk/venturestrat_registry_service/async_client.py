"""Asynchronous registry-service service client."""

from typing import Any
from typing import Any, Optional

import grpc.aio

from .auth import AuthProvider
from .config import RegistryServiceConfig
from .exceptions import (
    RegistryServiceConnectionError,
)


class AsyncRegistryServiceClient:
    """Asynchronous client for registry-service service.

    This client provides an asynchronous interface to the registry-service service
    using gRPC for high-performance communication with async/await support.

    Examples:
        Basic usage:
        >>> async with AsyncRegistryServiceClient(host="localhost", port=50051) as client:
        ...     healthy = await client.health_check()
        ...     print(f"Service healthy: {healthy}")

        With configuration:
        >>> config = RegistryServiceConfig.from_env()
        >>> client = AsyncRegistryServiceClient.from_config(config)
        >>> async with client:
        ...     # Authenticated async requests
        ...     pass
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 50051,
        secure: bool = False,
        timeout: float = 30.0,
        auth: AuthProvider | None = None,
        metadata: dict[str, str] | None = None,
        auth: Optional[AuthProvider] = None,
        metadata: Optional[dict[str, str]] = None,
        **grpc_options: Any,
    ) -> None:
        """Initialize async client.

        Args:
            host: Service host
            port: Service port
            secure: Use TLS connection
            timeout: Default request timeout in seconds
            auth: Authentication provider
            metadata: Default metadata for requests
            **grpc_options: Additional gRPC channel options
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.auth = auth
        self._default_metadata = metadata or {}

        # gRPC channel will be created in async context
        self.channel: grpc.aio.Channel | None = None
        self._stub = None
        self._grpc_options = grpc_options
        self._secure = secure

    @classmethod
    def from_config(cls, config: RegistryServiceConfig) -> "AsyncRegistryServiceClient":
        """Create async client from configuration.

        Args:
            config: Client configuration

        Returns:
            Configured async client instance
        """
        auth = None
        if config.auth_token:
            from .auth import TokenAuthProvider

            auth = TokenAuthProvider(config.auth_token)
        elif config.auth_api_key:
            from .auth import ApiKeyAuthProvider

            auth = ApiKeyAuthProvider(config.auth_api_key)

        return cls(
            host=config.host,
            port=config.port,
            secure=config.secure,
            timeout=config.timeout,
            auth=auth,
            metadata=config.metadata,
        )

    async def __aenter__(self) -> "AsyncRegistryServiceClient":
        """Async context manager entry."""
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _connect(self) -> None:
        """Establish gRPC connection."""
        target = f"{self.host}:{self.port}"

        if self._secure:
            credentials = grpc.ssl_channel_credentials()
            self.channel = grpc.aio.secure_channel(
                target, credentials, options=list(self._grpc_options.items())
            )
        else:
            self.channel = grpc.aio.insecure_channel(
                target, options=list(self._grpc_options.items())
            )

        await self._setup_stubs()

    async def _setup_stubs(self) -> None:
        """Set up async gRPC stubs.

        This will be populated when gRPC code generation is available.
        """
        # TODO: Import and set up generated async gRPC stubs when protobuf compilation is ready
        # from .grpc import registry_service_pb2_grpc
        # self._stub = registry_service_pb2_grpc.RegistryServiceAsyncStub(self.channel)

    async def close(self) -> None:
        """Close async client connection."""
        if self.channel:
            await self.channel.close()

    def _get_metadata(self, metadata: dict[str, str] | None = None) -> dict[str, str]:
    def _get_metadata(
        self, metadata: Optional[dict[str, str]] = None
    ) -> dict[str, str]:
        """Get request metadata with auth headers."""
        request_metadata = self._default_metadata.copy()
        if metadata:
            request_metadata.update(metadata)

        if self.auth:
            auth_metadata = self.auth.get_metadata()
            request_metadata.update(auth_metadata)

        return request_metadata

    async def health_check(self, timeout: float | None = None) -> bool:
        """Check if service is healthy asynchronously.

        Args:
            timeout: Request timeout (uses default if not specified)

        Returns:
            True if service is healthy

        Raises:
            RegistryServiceConnectionError: If connection fails
        """
        if not self.channel:
            msg = "Client not connected. Use 'async with' or call _connect()."
            raise RegistryServiceConnectionError(msg)
            raise RegistryServiceConnectionError(
                "Client not connected. Use 'async with' or call _connect()."
            )

        try:
            timeout = timeout or self.timeout

            # Test channel connectivity
            state = self.channel.get_state()
            if state != grpc.ChannelConnectivity.READY:
                await self.channel.wait_for_state_change(state)

            final_state = self.channel.get_state()
            return final_state == grpc.ChannelConnectivity.READY

        except Exception as e:
            msg = f"Async health check failed: {e}"
            raise RegistryServiceConnectionError(msg)

    # Async service-specific methods will be generated based on protobuf definitions
    # Example async method template:
    #
    # @handle_grpc_error_async
    # async def example_method(
    #     self,
    #     request: ExampleRequest,
    #     timeout: Optional[float] = None,
    #     metadata: Optional[Dict[str, str]] = None,
    # ) -> ExampleResponse:
    #     """Call example method asynchronously.
    #
    #     Args:
    #         request: The request message
    #         timeout: Request timeout
    #         metadata: Request metadata
    #
    #     Returns:
    #         Response message
    #
    #     Raises:
    #         RegistryServiceError: If request fails
    #     """
    #     if not self._stub:
    #         raise RegistryServiceConnectionError("Client not connected")
    #
    #     timeout = timeout or self.timeout
    #     metadata = self._get_metadata(metadata)
    #
    #     response = await self._stub.ExampleMethod(
    #         request,
    #         timeout=timeout,
    #         metadata=metadata.items(),
    #     )
    #
    #     return validate_response(response)
