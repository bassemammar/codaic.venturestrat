"""Data models for the Registry Service.

This module defines the core data models used for service registration,
discovery, and health management.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, computed_field

if TYPE_CHECKING:
    from registry.manifest import Manifest


class HealthStatus(str, Enum):
    """Health status of a service instance."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"

    @classmethod
    def from_consul(cls, status: str) -> HealthStatus:
        """Convert Consul health status string to HealthStatus.

        Args:
            status: Consul status string (passing, warning, critical)

        Returns:
            Corresponding HealthStatus value.
        """
        mapping = {
            "passing": cls.HEALTHY,
            "warning": cls.WARNING,
            "critical": cls.CRITICAL,
        }
        return mapping.get(status.lower(), cls.CRITICAL)


class Protocol(str, Enum):
    """Communication protocol for a service."""

    HTTP = "http"
    GRPC = "grpc"
    TCP = "tcp"


class HealthCheckConfig(BaseModel):
    """Health check configuration for a service.

    Supports HTTP, gRPC, and TCP health checks with configurable intervals.
    """

    http_endpoint: str | None = None
    grpc_service: str | None = None
    tcp_address: str | None = None
    interval_seconds: int = Field(default=10, ge=1, le=300)
    timeout_seconds: int = Field(default=5, ge=1, le=60)
    deregister_after_seconds: int = Field(default=60, ge=10, le=3600)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(exclude_none=True)

    def to_consul_check(self, service_address: str, service_port: int) -> dict[str, Any]:
        """Convert to Consul health check format.

        Args:
            service_address: The service address for building check URL.
            service_port: The service port.

        Returns:
            Consul health check configuration.
        """
        check: dict[str, Any] = {
            "Interval": f"{self.interval_seconds}s",
            "Timeout": f"{self.timeout_seconds}s",
            "DeregisterCriticalServiceAfter": f"{self.deregister_after_seconds}s",
        }

        if self.http_endpoint:
            check["HTTP"] = f"http://{service_address}:{service_port}{self.http_endpoint}"
        elif self.grpc_service:
            check["GRPC"] = f"{service_address}:{service_port}/{self.grpc_service}"
        elif self.tcp_address:
            check["TCP"] = self.tcp_address
        else:
            # Default to HTTP health check
            check["HTTP"] = f"http://{service_address}:{service_port}/health"

        return check


class ServiceRegistration(BaseModel):
    """Service registration payload.

    This model represents a service registering itself with the registry.
    """

    # Required fields
    name: str
    version: str
    instance_id: str
    address: str
    port: int = Field(ge=1, le=65535)
    protocol: Protocol = Protocol.HTTP

    # From manifest.yaml
    depends: list[str] = Field(default_factory=list)
    provides: dict[str, Any] = Field(default_factory=dict)

    # Health configuration
    health_check: HealthCheckConfig = Field(default_factory=HealthCheckConfig)

    # Metadata
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    # Timestamps
    registered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_manifest(
        cls,
        manifest: Manifest,
        instance_id: str,
        address: str,
        port: int,
        protocol: Protocol = Protocol.HTTP,
        extra_tags: list[str] | None = None,
        extra_metadata: dict[str, str] | None = None,
    ) -> ServiceRegistration:
        """Create registration from a parsed manifest.

        Args:
            manifest: Parsed manifest object.
            instance_id: Unique instance identifier.
            address: Service address (IP or hostname).
            port: Service port.
            protocol: Communication protocol.
            extra_tags: Additional tags to merge with manifest tags.
            extra_metadata: Additional metadata to merge with manifest metadata.

        Returns:
            ServiceRegistration populated from manifest.
        """
        # Build health check from manifest
        health_check = HealthCheckConfig(
            http_endpoint=manifest.health.readiness if manifest.health else "/health/ready",
            interval_seconds=manifest.health.interval if manifest.health else 10,
            timeout_seconds=manifest.health.timeout if manifest.health else 5,
            deregister_after_seconds=manifest.health.deregister_after if manifest.health else 60,
        )

        # Build provides dict
        provides: dict[str, Any] = {}
        if manifest.provides:
            provides["events"] = manifest.provides.events
            if manifest.provides.apis:
                provides["apis"] = manifest.provides.apis.model_dump(exclude_none=True)

        # Merge tags and metadata
        tags = list(manifest.tags)
        if extra_tags:
            tags.extend(extra_tags)

        # Add consul_tags from observability section
        if manifest.observability and manifest.observability.consul_tags:
            tags.extend(manifest.observability.consul_tags)

        metadata = dict(manifest.metadata)
        if extra_metadata:
            metadata.update(extra_metadata)

        return cls(
            name=manifest.name,
            version=manifest.version,
            instance_id=instance_id,
            address=address,
            port=port,
            protocol=protocol,
            depends=list(manifest.depends),
            provides=provides,
            health_check=health_check,
            tags=tags,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with ISO-formatted timestamps."""
        data = self.model_dump()
        data["registered_at"] = self.registered_at.isoformat()
        data["last_heartbeat"] = self.last_heartbeat.isoformat()
        data["protocol"] = self.protocol.value
        return data

    def to_consul_format(self) -> dict[str, Any]:
        """Convert to Consul service registration format.

        Returns:
            Dictionary suitable for Consul's /agent/service/register endpoint.
        """
        # Add version to tags for easy filtering
        tags = list(self.tags)
        tags.append(f"v{self.version}")

        # Build metadata with version
        meta = dict(self.metadata)
        meta["version"] = self.version
        meta["protocol"] = self.protocol.value

        return {
            "ID": self.instance_id,
            "Name": self.name,
            "Address": self.address,
            "Port": self.port,
            "Tags": tags,
            "Meta": meta,
            "Check": self.health_check.to_consul_check(self.address, self.port),
        }


class ServiceInstance(BaseModel):
    """Discovered service instance.

    This model represents a service instance returned from discovery queries.
    """

    name: str
    version: str
    instance_id: str
    address: str
    port: int
    protocol: Protocol
    health_status: HealthStatus
    tags: list[str]
    metadata: dict[str, str]

    @computed_field
    @property
    def is_healthy(self) -> bool:
        """Check if instance is fully healthy."""
        return self.health_status == HealthStatus.HEALTHY

    @computed_field
    @property
    def endpoint(self) -> str:
        """Get the service endpoint URL/address."""
        if self.protocol == Protocol.HTTP:
            return f"http://{self.address}:{self.port}"
        elif self.protocol == Protocol.GRPC:
            return f"{self.address}:{self.port}"
        else:
            return f"{self.address}:{self.port}"

    @classmethod
    def from_consul(
        cls,
        service_data: dict[str, Any],
        health_data: dict[str, Any] | None = None,
    ) -> ServiceInstance:
        """Create instance from Consul catalog response.

        Args:
            service_data: Consul service entry from catalog.
            health_data: Optional health check data.

        Returns:
            ServiceInstance populated from Consul data.
        """
        meta = service_data.get("ServiceMeta", {})
        tags = service_data.get("ServiceTags", [])

        # Extract version from meta or tags
        version = meta.get("version", "0.0.0")
        if not version:
            # Try to find version in tags (format: v1.2.3)
            for tag in tags:
                if tag.startswith("v") and "." in tag:
                    version = tag[1:]  # Remove 'v' prefix
                    break

        # Determine protocol from meta or default
        protocol_str = meta.get("protocol", "http")
        try:
            protocol = Protocol(protocol_str)
        except ValueError:
            protocol = Protocol.HTTP

        # Determine health status
        health_status = HealthStatus.HEALTHY
        if health_data:
            consul_status = health_data.get("Status", "passing")
            health_status = HealthStatus.from_consul(consul_status)

        return cls(
            name=service_data.get("ServiceName", ""),
            version=version,
            instance_id=service_data.get("ServiceID", ""),
            address=service_data.get("ServiceAddress", ""),
            port=service_data.get("ServicePort", 0),
            protocol=protocol,
            health_status=health_status,
            tags=[t for t in tags if not t.startswith("v")],  # Remove version tag
            metadata={k: v for k, v in meta.items() if k not in ("version", "protocol")},
        )


class ServiceQuery(BaseModel):
    """Query parameters for service discovery.

    Used to filter services when discovering dependencies.
    """

    name: str
    version_constraint: str | None = None
    tags: list[str] | None = None
    healthy_only: bool = True

    def to_consul_params(self) -> dict[str, Any]:
        """Convert to Consul catalog query parameters.

        Returns:
            Dictionary of query parameters for Consul's catalog/service endpoint.
        """
        params: dict[str, Any] = {
            "service": self.name,
        }

        if self.tags:
            params["tag"] = self.tags

        if self.healthy_only:
            params["passing"] = True

        return params
