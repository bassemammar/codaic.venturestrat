"""Synchronous registry-service service client."""

from typing import Any
from typing import Any, Optional

import grpc

from .auth import AuthProvider
from .config import RegistryServiceConfig
from .exceptions import (
    RegistryServiceConnectionError,
)


class RegistryServiceClient:
    """Synchronous client for registry-service service.

    This client provides a synchronous interface to the registry-service service
    using gRPC for high-performance communication.

    Examples:
        Basic usage:
        >>> client = RegistryServiceClient(host="localhost", port=50051)
        >>> with client:
        ...     result = client.health_check()
        ...     print(f"Service healthy: {result}")

        With authentication:
        >>> config = RegistryServiceConfig.from_env()
        >>> client = RegistryServiceClient.from_config(config)
        >>> with client:
        ...     # Authenticated requests
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
        """Initialize client.

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

        # Build gRPC channel
        target = f"{host}:{port}"
        if secure:
            credentials = grpc.ssl_channel_credentials()
            self.channel = grpc.secure_channel(
                target, credentials, options=grpc_options.items()
            )
        else:
            self.channel = grpc.insecure_channel(target, options=grpc_options.items())

        # Initialize stubs (will be set up when gRPC stubs are available)
        self._stub = None
        self._setup_stubs()

    @classmethod
    def from_config(cls, config: RegistryServiceConfig) -> "RegistryServiceClient":
        """Create client from configuration.

        Args:
            config: Client configuration

        Returns:
            Configured client instance
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

    def __enter__(self) -> "RegistryServiceClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close client connection."""
        if hasattr(self, "channel"):
            self.channel.close()

    def _setup_stubs(self) -> None:
        """Set up gRPC stubs.

        This will be populated when gRPC code generation is available.
        """
        # TODO: Import and set up generated gRPC stubs when protobuf compilation is ready
        # from .grpc import registry_service_pb2_grpc
        # self._stub = registry_service_pb2_grpc.RegistryServiceStub(self.channel)

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

    def health_check(self, timeout: float | None = None) -> bool:
        """Check if service is healthy.

        Args:
            timeout: Request timeout (uses default if not specified)

        Returns:
            True if service is healthy

        Raises:
            RegistryServiceConnectionError: If connection fails
        """
        try:
            # Test channel connectivity
            timeout = timeout or self.timeout
            state = self.channel.get_state(try_to_connect=True)

            # Wait for connection with timeout
            deadline = grpc.time.time() + timeout
            self.channel.wait_for_state_change(state, deadline)

            final_state = self.channel.get_state()
            return final_state == grpc.ChannelConnectivity.READY

        except Exception as e:
            msg = f"Health check failed: {e}"
            raise RegistryServiceConnectionError(msg)

    # Service-specific methods will be generated based on protobuf definitions
    # Example method template:
    #
    # @handle_grpc_error
    # def example_method(
    #     self,
    #     request: ExampleRequest,
    #     timeout: Optional[float] = None,
    #     metadata: Optional[Dict[str, str]] = None,
    # ) -> ExampleResponse:
    #     """Call example method.
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
    #     timeout = timeout or self.timeout
    #     metadata = self._get_metadata(metadata)
    #
    #     response = self._stub.ExampleMethod(
    #         request,
    #         timeout=timeout,
    #         metadata=metadata.items(),
    #     )
    #
    #     return validate_response(response)
