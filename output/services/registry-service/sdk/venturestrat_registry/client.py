"""VentureStrat Registry Client.

High-level client for interacting with the VentureStrat Registry Service.
"""
from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field, computed_field

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class RegistryError(Exception):
    """Base exception for registry errors."""

    pass


class ConnectionError(RegistryError):
    """Raised when unable to connect to registry."""

    pass


class RegistrationError(RegistryError):
    """Raised when registration fails."""

    pass


class DiscoveryError(RegistryError):
    """Raised when service discovery fails."""

    pass


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class RegistryClientConfig:
    """Configuration for the registry client.

    Attributes:
        host: Registry service hostname.
        port: Registry service port.
        use_grpc: Whether to use gRPC instead of REST.
        timeout: Request timeout in seconds.
        retry_attempts: Number of retry attempts for failed requests.
        retry_delay: Delay between retries in seconds.
        use_gateway: Whether to use API gateway for registry access.
        api_key: API key for gateway authentication (if use_gateway=True).
        base_url_override: Override base URL (for gateway integration).
    """

    host: str = "localhost"
    port: int = 8080
    use_grpc: bool = False
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    use_gateway: bool = False
    api_key: str | None = None
    base_url_override: str | None = None

    @classmethod
    def from_env(cls) -> RegistryClientConfig:
        """Load configuration from environment variables.

        Environment variables:
            REGISTRY_HOST: Registry hostname (default: localhost)
            REGISTRY_PORT: Registry port (default: 8080)
            REGISTRY_USE_GRPC: Use gRPC (true/false, default: false)
            REGISTRY_TIMEOUT: Request timeout (default: 30.0)
            REGISTRY_BASE_URL: Override base URL for gateway integration
            API_KEY or X_API_KEY: API key for gateway authentication
            SERVICE_DISCOVERY_MODE: Set to 'gateway' to use gateway mode
        """
        # Check if we should use gateway mode
        use_gateway = os.getenv("SERVICE_DISCOVERY_MODE", "").lower() == "gateway"

        # Get API key for gateway authentication
        api_key = os.getenv("API_KEY") or os.getenv("X_API_KEY")

        # Get base URL override (for gateway integration)
        base_url_override = os.getenv("REGISTRY_BASE_URL")

        # If using gateway mode but no explicit base URL, construct gateway URL
        if use_gateway and not base_url_override:
            gateway_host = os.getenv("GATEWAY_HOST", os.getenv("REGISTRY_HOST", "localhost"))
            gateway_port = os.getenv("GATEWAY_PORT", "8000")
            base_url_override = f"http://{gateway_host}:{gateway_port}/api/v1/registry"

        return cls(
            host=os.getenv("REGISTRY_HOST", "localhost"),
            port=int(os.getenv("REGISTRY_PORT", "8080")),
            use_grpc=os.getenv("REGISTRY_USE_GRPC", "false").lower() == "true",
            timeout=float(os.getenv("REGISTRY_TIMEOUT", "30.0")),
            use_gateway=use_gateway,
            api_key=api_key,
            base_url_override=base_url_override,
        )

    @property
    def base_url(self) -> str:
        """Get the base URL for REST API."""
        if self.base_url_override:
            return self.base_url_override
        return f"http://{self.host}:{self.port}/api/v1"


# =============================================================================
# Models
# =============================================================================


class ServiceRegistration(BaseModel):
    """Service registration payload.

    Contains all information needed to register a service instance.
    """

    name: str
    version: str
    instance_id: str
    address: str
    port: int = Field(ge=1, le=65535)
    protocol: str = "http"
    depends: list[str] = Field(default_factory=list)
    provides: dict[str, Any] = Field(default_factory=dict)
    health_check: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    def to_api_payload(self) -> dict[str, Any]:
        """Convert to API request payload."""
        return self.model_dump(exclude_none=True)


class RegistrationResult(BaseModel):
    """Result of service registration."""

    instance_id: str
    consul_service_id: str
    registered_at: str
    health_check_id: str


class ServiceInstance(BaseModel):
    """Discovered service instance.

    Represents a running instance of a service.
    """

    instance_id: str
    address: str
    port: int
    protocol: str
    version: str
    health_status: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    @computed_field
    @property
    def endpoint(self) -> str:
        """Get the service endpoint URL."""
        if self.protocol == "grpc":
            return f"{self.address}:{self.port}"
        return f"http://{self.address}:{self.port}"

    @computed_field
    @property
    def is_healthy(self) -> bool:
        """Check if instance is healthy."""
        return self.health_status == "healthy"


class ServiceEvent(BaseModel):
    """Service lifecycle event.

    Emitted when a service is registered, deregistered, or its health changes.
    """

    event_type: str  # registered, deregistered, health_changed
    service_name: str
    instance_id: str
    version: str
    timestamp: datetime | None = None
    instance: ServiceInstance | None = None


# =============================================================================
# Client
# =============================================================================


class RegistryClient:
    """Async client for the VentureStrat Registry Service.

    Provides methods for service registration, discovery, and health monitoring.

    Usage:
        async with RegistryClient() as client:
            # Register
            await client.register(registration)

            # Discover
            instances = await client.discover("market-data-service")

            # Deregister
            await client.deregister(instance_id, service_name, version)

    Or with auto-registration:
        async with RegistryClient.from_manifest("manifest.yaml", ...) as client:
            # Auto-registered on enter, auto-deregistered on exit
            instances = await client.discover("market-data-service")
    """

    def __init__(
        self,
        config: RegistryClientConfig | None = None,
    ):
        """Initialize registry client.

        Args:
            config: Client configuration. Uses defaults if not provided.
        """
        self.config = config or RegistryClientConfig()
        self._http_client: httpx.AsyncClient | None = None
        self._registration: ServiceRegistration | None = None
        self._registered: bool = False

    @classmethod
    def from_manifest(
        cls,
        manifest_path: Path,
        instance_id: str,
        address: str,
        port: int,
        config: RegistryClientConfig | None = None,
        extra_tags: list[str] | None = None,
        extra_metadata: dict[str, str] | None = None,
    ) -> _AutoRegisterClient:
        """Create client that auto-registers from manifest.

        Args:
            manifest_path: Path to manifest.yaml file.
            instance_id: Unique instance identifier.
            address: Service address.
            port: Service port.
            config: Client configuration.
            extra_tags: Additional tags to add.
            extra_metadata: Additional metadata to add.

        Returns:
            AutoRegisterClient that registers on enter and deregisters on exit.
        """
        return _AutoRegisterClient(
            manifest_path=manifest_path,
            instance_id=instance_id,
            address=address,
            port=port,
            config=config,
            extra_tags=extra_tags,
            extra_metadata=extra_metadata,
        )

    async def __aenter__(self) -> RegistryClient:
        """Enter async context."""
        # Prepare headers for gateway authentication
        headers = {}
        if self.config.use_gateway and self.config.api_key:
            headers["X-API-Key"] = self.config.api_key

        self._http_client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            headers=headers,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def register(self, registration: ServiceRegistration) -> RegistrationResult:
        """Register a service instance.

        Args:
            registration: Service registration details.

        Returns:
            RegistrationResult with instance details.

        Raises:
            RegistrationError: If registration fails.
            ConnectionError: If unable to connect to registry.
        """
        if not self._http_client:
            raise RegistryError("Client not initialized. Use 'async with' context.")

        try:
            response = await self._http_client.post(
                "/services",
                json=registration.to_api_payload(),
            )

            if response.status_code == 201:
                self._registration = registration
                self._registered = True
                return RegistrationResult(**response.json())

            if response.status_code in (400, 422):
                error_data = response.json()
                raise RegistrationError(
                    error_data.get("error", {}).get("message", "Registration failed")
                )

            if response.status_code == 409:
                raise RegistrationError("Instance already registered")

            raise RegistrationError(f"Registration failed: {response.status_code}")

        except httpx.RequestError as e:
            raise ConnectionError(f"Failed to connect to registry: {e}") from e

    async def register_from_manifest(
        self,
        manifest_path: Path,
        instance_id: str,
        address: str,
        port: int,
        protocol: str = "http",
        extra_tags: list[str] | None = None,
        extra_metadata: dict[str, str] | None = None,
    ) -> RegistrationResult:
        """Register service from manifest file.

        Args:
            manifest_path: Path to manifest.yaml.
            instance_id: Unique instance identifier.
            address: Service address.
            port: Service port.
            protocol: Communication protocol.
            extra_tags: Additional tags.
            extra_metadata: Additional metadata.

        Returns:
            RegistrationResult with instance details.
        """
        from venturestrat_registry.manifest import ManifestLoader

        manifest = ManifestLoader.load(manifest_path)

        # Build health check from manifest
        health_config = manifest.get("health", {})
        health_check = {}
        if health_config.get("readiness"):
            health_check["http_endpoint"] = health_config["readiness"]
        if health_config.get("interval"):
            health_check["interval_seconds"] = health_config["interval"]

        # Merge tags and metadata
        tags = list(manifest.get("tags", []))
        if extra_tags:
            tags.extend(extra_tags)

        metadata = dict(manifest.get("metadata", {}))
        if extra_metadata:
            metadata.update(extra_metadata)

        registration = ServiceRegistration(
            name=manifest["name"],
            version=manifest["version"],
            instance_id=instance_id,
            address=address,
            port=port,
            protocol=protocol,
            depends=manifest.get("depends", []),
            provides=manifest.get("provides", {}),
            health_check=health_check,
            tags=tags,
            metadata=metadata,
        )

        return await self.register(registration)

    async def deregister(
        self,
        instance_id: str,
        service_name: str,
        version: str,
        reason: str = "graceful_shutdown",
    ) -> None:
        """Deregister a service instance.

        Args:
            instance_id: Instance ID to deregister.
            service_name: Service name.
            version: Service version.
            reason: Deregistration reason.

        Raises:
            RegistryError: If deregistration fails.
            ConnectionError: If unable to connect to registry.
        """
        if not self._http_client:
            raise RegistryError("Client not initialized. Use 'async with' context.")

        try:
            response = await self._http_client.delete(
                f"/services/{instance_id}",
                params={
                    "service_name": service_name,
                    "version": version,
                    "reason": reason,
                },
            )

            if response.status_code == 204:
                self._registered = False
                return

            raise RegistryError(f"Deregistration failed: {response.status_code}")

        except httpx.RequestError as e:
            raise ConnectionError(f"Failed to connect to registry: {e}") from e

    async def discover(
        self,
        service_name: str,
        version: str | None = None,
        tags: list[str] | None = None,
        healthy_only: bool = True,
    ) -> list[ServiceInstance]:
        """Discover service instances.

        Args:
            service_name: Service name to discover.
            version: Semver constraint (e.g., "^1.0.0").
            tags: Filter by tags.
            healthy_only: Only return healthy instances.

        Returns:
            List of matching service instances.

        Raises:
            DiscoveryError: If service not found or discovery fails.
            ConnectionError: If unable to connect to registry.
        """
        if not self._http_client:
            raise RegistryError("Client not initialized. Use 'async with' context.")

        try:
            params: dict[str, Any] = {"healthy_only": str(healthy_only).lower()}
            if version:
                params["version"] = version
            if tags:
                params["tags"] = ",".join(tags)

            response = await self._http_client.get(
                f"/services/{service_name}",
                params=params,
            )

            if response.status_code == 200:
                data = response.json()
                return [ServiceInstance(**inst) for inst in data.get("instances", [])]

            if response.status_code == 404:
                raise DiscoveryError(f"Service '{service_name}' not found")

            raise DiscoveryError(f"Discovery failed: {response.status_code}")

        except httpx.RequestError as e:
            raise ConnectionError(f"Failed to connect to registry: {e}") from e

    async def watch(
        self,
        service_name: str | None = None,
    ) -> AsyncIterator[ServiceEvent]:
        """Watch for service events.

        This is a streaming endpoint that yields events as they occur.

        Args:
            service_name: Optional service to watch (all services if None).

        Yields:
            ServiceEvent for each service change.
        """
        # Note: This would require SSE or WebSocket support
        # For now, this is a placeholder
        if False:  # pragma: no cover
            yield ServiceEvent(
                event_type="registered",
                service_name="",
                instance_id="",
                version="",
            )

    async def list_services(
        self,
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List all registered services.

        Args:
            tags: Filter by tags.

        Returns:
            List of service summaries.
        """
        if not self._http_client:
            raise RegistryError("Client not initialized. Use 'async with' context.")

        params = {}
        if tags:
            params["tags"] = ",".join(tags)

        response = await self._http_client.get("/services", params=params)

        if response.status_code == 200:
            return response.json().get("services", [])

        raise RegistryError(f"Failed to list services: {response.status_code}")

    async def get_health(self) -> dict[str, Any]:
        """Get health overview of all services.

        Returns:
            Health overview with service statuses.
        """
        if not self._http_client:
            raise RegistryError("Client not initialized. Use 'async with' context.")

        response = await self._http_client.get("/health/services")

        if response.status_code == 200:
            return response.json()

        raise RegistryError(f"Failed to get health: {response.status_code}")


class _AutoRegisterClient(RegistryClient):
    """Client that auto-registers on enter and deregisters on exit."""

    def __init__(
        self,
        manifest_path: Path,
        instance_id: str,
        address: str,
        port: int,
        config: RegistryClientConfig | None = None,
        extra_tags: list[str] | None = None,
        extra_metadata: dict[str, str] | None = None,
    ):
        super().__init__(config)
        self._manifest_path = manifest_path
        self._instance_id = instance_id
        self._address = address
        self._port = port
        self._extra_tags = extra_tags
        self._extra_metadata = extra_metadata

    async def __aenter__(self) -> _AutoRegisterClient:
        """Enter async context and auto-register."""
        await super().__aenter__()

        # Auto-register from manifest
        await self.register_from_manifest(
            manifest_path=self._manifest_path,
            instance_id=self._instance_id,
            address=self._address,
            port=self._port,
            extra_tags=self._extra_tags,
            extra_metadata=self._extra_metadata,
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context and auto-deregister."""
        if self._registered and self._registration:
            try:
                await self.deregister(
                    instance_id=self._registration.instance_id,
                    service_name=self._registration.name,
                    version=self._registration.version,
                    reason="shutdown",
                )
            except Exception as e:
                logger.warning(f"Failed to deregister on exit: {e}")

        await super().__aexit__(exc_type, exc_val, exc_tb)
