"""Core Registry Service implementation.

This module provides the main RegistryService class that orchestrates
service registration, discovery, and health management.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from registry.consul_client import ConsulClient
from registry.events import EventPublisher
from registry.health import HealthManager
from registry.manifest import ManifestParser
from registry.models import (
    HealthStatus,
    Protocol,
    ServiceInstance,
    ServiceQuery,
    ServiceRegistration,
)
from registry.version import VersionMatcher

logger = logging.getLogger(__name__)


class RegistryService:
    """Core service registry that orchestrates all components.

    Provides the main API for service registration, discovery, and
    health management by coordinating:
    - ConsulClient for backend storage
    - EventPublisher for lifecycle events
    - HealthManager for health tracking
    - VersionMatcher for version constraint filtering

    Usage:
        service = RegistryService(
            consul_client=ConsulClient(),
            event_publisher=EventPublisher(),
            health_manager=HealthManager(),
        )

        # Register a service
        await service.register(registration)

        # Discover services
        instances = await service.discover("pricing-service", version_constraint="^1.0.0")

        # Deregister
        await service.deregister(instance_id, service_name, version, reason)
    """

    KV_PREFIX = "venturestrat/services"

    def __init__(
        self,
        consul_client: ConsulClient,
        event_publisher: EventPublisher,
        health_manager: HealthManager,
        manifest_parser: ManifestParser | None = None,
        version_matcher: VersionMatcher | None = None,
    ):
        """Initialize registry service.

        Args:
            consul_client: Consul client for backend operations.
            event_publisher: Event publisher for lifecycle events.
            health_manager: Health status manager.
            manifest_parser: Optional manifest parser (created if not provided).
            version_matcher: Optional version matcher (created if not provided).
        """
        self.consul = consul_client
        self.events = event_publisher
        self.health = health_manager
        self.manifest_parser = manifest_parser or ManifestParser()
        self.version_matcher = version_matcher or VersionMatcher()

    async def register(self, registration: ServiceRegistration) -> bool:
        """Register a service instance.

        Performs the following steps:
        1. Register with Consul
        2. Cache metadata in Consul KV
        3. Publish registration event

        Args:
            registration: Service registration details.

        Returns:
            True if registration succeeded.

        Raises:
            ConsulOperationError: If Consul registration fails.
        """
        # Register with Consul
        await self.consul.register(registration)

        # Cache metadata in KV
        metadata_key = (
            f"{self.KV_PREFIX}/{registration.name}/instances/{registration.instance_id}/metadata"
        )
        metadata = registration.to_dict()
        await self.consul.kv_put(metadata_key, json.dumps(metadata))

        # Publish event
        await self.events.publish_registered(registration)

        logger.info(
            f"Registered {registration.name} v{registration.version} "
            f"at {registration.address}:{registration.port} "
            f"(id={registration.instance_id})"
        )

        return True

    async def register_from_manifest(
        self,
        manifest_path: Path,
        instance_id: str,
        address: str,
        port: int,
        protocol: Protocol = Protocol.HTTP,
        extra_tags: list[str] | None = None,
        extra_metadata: dict[str, str] | None = None,
    ) -> ServiceRegistration:
        """Register a service from a manifest.yaml file.

        Args:
            manifest_path: Path to the manifest.yaml file.
            instance_id: Unique instance identifier.
            address: Service address.
            port: Service port.
            protocol: Communication protocol.
            extra_tags: Additional tags.
            extra_metadata: Additional metadata.

        Returns:
            The ServiceRegistration that was created and registered.

        Raises:
            ManifestParseError: If manifest is invalid.
            ConsulOperationError: If registration fails.
        """
        # Parse manifest
        manifest = self.manifest_parser.parse_file(manifest_path)

        # Create registration
        registration = ServiceRegistration.from_manifest(
            manifest=manifest,
            instance_id=instance_id,
            address=address,
            port=port,
            protocol=protocol,
            extra_tags=extra_tags,
            extra_metadata=extra_metadata,
        )

        # Cache manifest in KV
        manifest_key = f"{self.KV_PREFIX}/{manifest.name}/manifest"
        await self.consul.kv_put(manifest_key, json.dumps(manifest.to_dict()))

        # Register
        await self.register(registration)

        return registration

    async def deregister(
        self,
        instance_id: str,
        service_name: str,
        version: str,
        reason: str = "graceful_shutdown",
    ) -> bool:
        """Deregister a service instance.

        Args:
            instance_id: The instance ID to deregister.
            service_name: Name of the service.
            version: Service version.
            reason: Reason for deregistration.

        Returns:
            True if deregistration succeeded.
        """
        # Deregister from Consul
        await self.consul.deregister(instance_id)

        # Clear KV cache
        metadata_key = f"{self.KV_PREFIX}/{service_name}/instances/{instance_id}"
        try:
            await self.consul.kv_delete(metadata_key)
        except Exception as e:
            logger.warning(f"Failed to clear KV for {instance_id}: {e}")

        # Clear health tracking
        self.health.clear_instance(instance_id)

        # Publish event
        await self.events.publish_deregistered(
            service_name=service_name,
            instance_id=instance_id,
            version=version,
            reason=reason,
        )

        logger.info(f"Deregistered {service_name}/{instance_id} (reason={reason})")

        return True

    async def discover(
        self,
        service_name: str,
        version_constraint: str | None = None,
        tags: list[str] | None = None,
        healthy_only: bool = True,
    ) -> list[ServiceInstance]:
        """Discover service instances.

        Args:
            service_name: Name of the service to find.
            version_constraint: Semver constraint (e.g., "^1.0.0").
            tags: Filter by tags.
            healthy_only: Only return healthy instances.

        Returns:
            List of matching service instances.
        """
        query = ServiceQuery(
            name=service_name,
            tags=tags,
            healthy_only=healthy_only,
        )

        instances = await self.consul.discover(query)

        # Apply version filtering
        if version_constraint:
            instances = self.version_matcher.filter_by_version(instances, version_constraint)

        return instances

    async def list_services(self) -> dict[str, list[str]]:
        """List all registered services.

        Returns:
            Dict mapping service names to their tags.
        """
        return await self.consul.list_services()

    async def get_service_info(self, service_name: str) -> dict[str, Any]:
        """Get detailed information about a service.

        Args:
            service_name: Name of the service.

        Returns:
            Service information including instances, versions, and health.
        """
        instances = await self.discover(service_name, healthy_only=False)

        healthy_count = sum(1 for i in instances if i.health_status == HealthStatus.HEALTHY)
        versions = list(set(i.version for i in instances))

        return {
            "name": service_name,
            "instance_count": len(instances),
            "healthy_count": healthy_count,
            "unhealthy_count": len(instances) - healthy_count,
            "versions": versions,
            "instances": [
                {
                    "instance_id": i.instance_id,
                    "version": i.version,
                    "address": i.address,
                    "port": i.port,
                    "health_status": i.health_status.value,
                    "tags": i.tags,
                }
                for i in instances
            ],
        }

    async def get_health_overview(self) -> dict[str, Any]:
        """Get health overview of all services.

        Returns:
            Overview of service health status.
        """
        services = await self.list_services()

        total_instances = 0
        healthy_instances = 0
        service_statuses = {}

        for service_name in services:
            instances = await self.discover(service_name, healthy_only=False)
            total_instances += len(instances)
            healthy = sum(1 for i in instances if i.health_status == HealthStatus.HEALTHY)
            healthy_instances += healthy

            service_statuses[service_name] = {
                "total": len(instances),
                "healthy": healthy,
                "unhealthy": len(instances) - healthy,
            }

        return {
            "services": service_statuses,
            "total_instances": total_instances,
            "healthy_instances": healthy_instances,
            "unhealthy_instances": total_instances - healthy_instances,
        }
