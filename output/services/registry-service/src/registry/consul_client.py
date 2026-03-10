"""Consul client for service registration and discovery.

This module provides an async wrapper around python-consul for
service registration, discovery, and KV operations.
"""
from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any

import consul

from registry.models import (
    HealthStatus,
    Protocol,
    ServiceInstance,
    ServiceQuery,
    ServiceRegistration,
)

logger = logging.getLogger(__name__)


class ConsulConnectionError(Exception):
    """Raised when unable to connect to Consul."""

    pass


class ConsulOperationError(Exception):
    """Raised when a Consul operation fails."""

    pass


class ConsulClient:
    """Async client for Consul service registry.

    Provides methods for:
    - Service registration and deregistration
    - Service discovery with health filtering
    - KV store operations for metadata caching
    - Catalog queries

    Usage:
        client = ConsulClient(host="consul.local", port=8500)

        # Register a service
        await client.register(registration)

        # Discover services
        instances = await client.discover(ServiceQuery(name="my-service"))

        # Store metadata in KV
        await client.kv_put("services/my-service/config", json_data)
    """

    # Services to exclude from listings (internal Consul services)
    EXCLUDED_SERVICES = {"consul"}

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8500,
        token: str | None = None,
        scheme: str = "http",
    ):
        """Initialize Consul client.

        Args:
            host: Consul server hostname.
            port: Consul HTTP API port.
            token: Optional ACL token.
            scheme: HTTP or HTTPS.
        """
        self.host = host
        self.port = port
        self.token = token
        self.scheme = scheme

        self._consul = consul.Consul(
            host=host,
            port=port,
            token=token,
            scheme=scheme,
        )
        self._loop: asyncio.AbstractEventLoop | None = None

    async def _run_sync(self, func, *args, **kwargs) -> Any:
        """Run a synchronous function in executor.

        python-consul is synchronous, so we wrap calls to run in thread pool.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    async def health_check(self) -> bool:
        """Check if Consul is healthy and reachable.

        Returns:
            True if Consul is healthy, False otherwise.
        """
        try:
            leader = await self._run_sync(self._consul.status.leader)
            return bool(leader)
        except Exception as e:
            logger.warning(f"Consul health check failed: {e}")
            return False

    async def register(self, registration: ServiceRegistration) -> bool:
        """Register a service with Consul.

        Args:
            registration: Service registration details.

        Returns:
            True if registration succeeded.

        Raises:
            ConsulOperationError: If registration fails.
        """
        try:
            # Build tags including version
            tags = list(registration.tags)
            tags.append(f"v{registration.version}")

            # Build metadata
            meta = dict(registration.metadata)
            meta["version"] = registration.version
            meta["protocol"] = registration.protocol.value

            # Build health check
            check = None
            if registration.health_check:
                hc = registration.health_check
                check = {
                    "interval": f"{hc.interval_seconds}s",
                    "timeout": f"{hc.timeout_seconds}s",
                    "deregister_critical_service_after": f"{hc.deregister_after_seconds}s",
                }

                if hc.http_endpoint:
                    check[
                        "http"
                    ] = f"http://{registration.address}:{registration.port}{hc.http_endpoint}"
                elif hc.grpc_service:
                    check["grpc"] = f"{registration.address}:{registration.port}/{hc.grpc_service}"
                elif hc.tcp_address:
                    check["tcp"] = hc.tcp_address
                else:
                    # Default to HTTP health check
                    check["http"] = f"http://{registration.address}:{registration.port}/health"

            # Register with Consul
            await self._run_sync(
                self._consul.agent.service.register,
                name=registration.name,
                service_id=registration.instance_id,
                address=registration.address,
                port=registration.port,
                tags=tags,
                meta=meta,
                check=check,
            )

            logger.info(
                f"Registered service {registration.name} "
                f"(id={registration.instance_id}, address={registration.address}:{registration.port})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to register service {registration.name}: {e}")
            raise ConsulOperationError(f"Failed to register service: {e}") from e

    async def deregister(self, instance_id: str) -> bool:
        """Deregister a service instance from Consul.

        Args:
            instance_id: The service instance ID to deregister.

        Returns:
            True if deregistration succeeded.

        Raises:
            ConsulOperationError: If deregistration fails.
        """
        try:
            await self._run_sync(
                self._consul.agent.service.deregister,
                instance_id,
            )
            logger.info(f"Deregistered service instance {instance_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to deregister service {instance_id}: {e}")
            raise ConsulOperationError(f"Failed to deregister service: {e}") from e

    async def discover(self, query: ServiceQuery) -> list[ServiceInstance]:
        """Discover service instances matching the query.

        Args:
            query: Service discovery query parameters.

        Returns:
            List of matching service instances.

        Raises:
            ConsulOperationError: If discovery fails.
        """
        try:
            # Query health endpoint for service
            tag = query.tags[0] if query.tags else None
            passing_only = query.healthy_only

            _, services = await self._run_sync(
                self._consul.health.service,
                query.name,
                tag=tag,
                passing=passing_only,
            )

            instances = []
            for entry in services:
                service_data = entry.get("Service", {})
                checks = entry.get("Checks", [])

                # Determine overall health status
                health_status = self._calculate_health_status(checks)

                # Extract metadata (Meta can be null in Consul response)
                meta = service_data.get("Meta") or {}
                tags = service_data.get("Tags", [])

                # Get version from meta or tags
                version = meta.get("version", "0.0.0")
                if not version:
                    for t in tags:
                        if t.startswith("v") and "." in t:
                            version = t[1:]
                            break

                # Get protocol
                protocol_str = meta.get("protocol", "http")
                try:
                    protocol = Protocol(protocol_str)
                except ValueError:
                    protocol = Protocol.HTTP

                instance = ServiceInstance(
                    name=service_data.get("Service", ""),
                    version=version,
                    instance_id=service_data.get("ID", ""),
                    address=service_data.get("Address", ""),
                    port=service_data.get("Port", 0),
                    protocol=protocol,
                    health_status=health_status,
                    tags=[t for t in tags if not t.startswith("v")],
                    metadata={k: v for k, v in meta.items() if k not in ("version", "protocol")},
                )
                instances.append(instance)

            return instances

        except Exception as e:
            logger.error(f"Failed to discover service {query.name}: {e}")
            raise ConsulOperationError(f"Failed to discover service: {e}") from e

    def _calculate_health_status(self, checks: list[dict]) -> HealthStatus:
        """Calculate overall health status from check results.

        Args:
            checks: List of health check results.

        Returns:
            Overall health status.
        """
        if not checks:
            return HealthStatus.HEALTHY

        statuses = [c.get("Status", "critical") for c in checks]

        if all(s == "passing" for s in statuses):
            return HealthStatus.HEALTHY
        elif any(s == "critical" for s in statuses):
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.WARNING

    async def kv_put(self, key: str, value: str) -> bool:
        """Store a value in Consul KV.

        Args:
            key: The key path.
            value: The value to store (string).

        Returns:
            True if operation succeeded.

        Raises:
            ConsulOperationError: If operation fails.
        """
        try:
            result = await self._run_sync(
                self._consul.kv.put,
                key,
                value,
            )
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to put KV {key}: {e}")
            raise ConsulOperationError(f"Failed to put KV: {e}") from e

    async def kv_get(self, key: str) -> str | None:
        """Retrieve a value from Consul KV.

        Args:
            key: The key path.

        Returns:
            The value as string, or None if not found.

        Raises:
            ConsulOperationError: If operation fails.
        """
        try:
            _, data = await self._run_sync(
                self._consul.kv.get,
                key,
            )

            if data is None:
                return None

            value = data.get("Value")
            if value is None:
                return None

            return value.decode("utf-8") if isinstance(value, bytes) else value

        except Exception as e:
            logger.error(f"Failed to get KV {key}: {e}")
            raise ConsulOperationError(f"Failed to get KV: {e}") from e

    async def kv_delete(self, key: str) -> bool:
        """Delete a key from Consul KV.

        Args:
            key: The key path.

        Returns:
            True if operation succeeded.

        Raises:
            ConsulOperationError: If operation fails.
        """
        try:
            result = await self._run_sync(
                self._consul.kv.delete,
                key,
            )
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to delete KV {key}: {e}")
            raise ConsulOperationError(f"Failed to delete KV: {e}") from e

    async def kv_list(self, prefix: str) -> list[str]:
        """List keys under a prefix.

        Args:
            prefix: The key prefix to search.

        Returns:
            List of key paths.

        Raises:
            ConsulOperationError: If operation fails.
        """
        try:
            _, data = await self._run_sync(
                self._consul.kv.get,
                prefix,
                keys=True,
            )

            if data is None:
                return []

            if isinstance(data, list):
                return [item.get("Key", item) if isinstance(item, dict) else item for item in data]

            return []

        except Exception as e:
            logger.error(f"Failed to list KV {prefix}: {e}")
            raise ConsulOperationError(f"Failed to list KV: {e}") from e

    async def list_services(self) -> dict[str, list[str]]:
        """List all registered services.

        Returns:
            Dict mapping service names to their tags.

        Raises:
            ConsulOperationError: If operation fails.
        """
        try:
            _, services = await self._run_sync(
                self._consul.catalog.services,
            )

            # Filter out internal services
            return {
                name: tags for name, tags in services.items() if name not in self.EXCLUDED_SERVICES
            }

        except Exception as e:
            logger.error(f"Failed to list services: {e}")
            raise ConsulOperationError(f"Failed to list services: {e}") from e

    async def get_service_instances(self, service_name: str) -> list[dict]:
        """Get all instances of a service from the catalog.

        Args:
            service_name: Name of the service.

        Returns:
            List of service instance dictionaries.

        Raises:
            ConsulOperationError: If operation fails.
        """
        try:
            _, instances = await self._run_sync(
                self._consul.catalog.service,
                service_name,
            )
            return instances or []

        except Exception as e:
            logger.error(f"Failed to get instances for {service_name}: {e}")
            raise ConsulOperationError(f"Failed to get service instances: {e}") from e
