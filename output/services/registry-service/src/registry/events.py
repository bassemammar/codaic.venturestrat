"""Event publishing for service lifecycle events.

This module provides Kafka event publishing for service registration,
deregistration, and health status changes.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from aiokafka import AIOKafkaProducer

    from registry.health import HealthTransition
    from registry.models import ServiceRegistration

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of service lifecycle events."""

    REGISTERED = "service.registered"
    DEREGISTERED = "service.deregistered"
    HEALTH_CHANGED = "service.health_changed"

    # Tenant lifecycle events
    TENANT_CREATED = "tenant.created"
    TENANT_DELETED = "tenant.deleted"
    TENANT_PURGED = "tenant.purged"

    # Tenant export events
    TENANT_EXPORT_STARTED = "tenant.export.started"
    TENANT_EXPORT_COMPLETED = "tenant.export.completed"
    TENANT_EXPORT_FAILED = "tenant.export.failed"


class ServiceEvent(BaseModel):
    """Base class for service lifecycle events."""

    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    service_name: str
    instance_id: str
    version: str

    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = self.model_dump()
        data["event_type"] = self.event_type.value
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)

    def to_bytes(self) -> bytes:
        """Serialize event to bytes for Kafka."""
        return self.to_json().encode("utf-8")


class ServiceRegisteredEvent(ServiceEvent):
    """Event emitted when a service instance is registered."""

    event_type: EventType = EventType.REGISTERED
    address: str
    port: int
    protocol: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_registration(cls, registration: ServiceRegistration) -> ServiceRegisteredEvent:
        """Create event from ServiceRegistration.

        Args:
            registration: The service registration.

        Returns:
            ServiceRegisteredEvent populated from registration.
        """
        return cls(
            service_name=registration.name,
            instance_id=registration.instance_id,
            version=registration.version,
            address=registration.address,
            port=registration.port,
            protocol=registration.protocol.value,
            tags=list(registration.tags),
            metadata=dict(registration.metadata),
        )


class ServiceDeregisteredEvent(ServiceEvent):
    """Event emitted when a service instance is deregistered."""

    event_type: EventType = EventType.DEREGISTERED
    reason: str  # "graceful_shutdown", "health_check_timeout", "manual"


class ServiceHealthChangedEvent(ServiceEvent):
    """Event emitted when a service's health status changes."""

    event_type: EventType = EventType.HEALTH_CHANGED
    previous_status: str
    new_status: str
    check_name: str | None = None
    check_output: str | None = None

    @classmethod
    def from_transition(
        cls,
        transition: HealthTransition,
        version: str,
    ) -> ServiceHealthChangedEvent:
        """Create event from HealthTransition.

        Args:
            transition: The health transition.
            version: Service version.

        Returns:
            ServiceHealthChangedEvent populated from transition.
        """
        return cls(
            service_name=transition.service_name,
            instance_id=transition.instance_id,
            version=version,
            previous_status=transition.previous_status.value,
            new_status=transition.new_status.value,
            check_name=transition.check_name,
            check_output=transition.check_output,
        )


class EventPublisher:
    """Publishes service lifecycle events to Kafka.

    Events are published to the configured topic with the service name
    as the message key for consistent partitioning.

    Usage:
        publisher = EventPublisher(
            bootstrap_servers="kafka:9092",
            topic="platform.services.lifecycle",
        )
        await publisher.start()

        # Publish events
        await publisher.publish_registered(registration)
        await publisher.publish_deregistered(service_name, instance_id, version, reason)
        await publisher.publish_health_changed(transition, version)

        await publisher.stop()
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "platform.services.lifecycle",
    ):
        """Initialize event publisher.

        Args:
            bootstrap_servers: Kafka bootstrap servers.
            topic: Topic to publish events to.
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start the Kafka producer."""
        if self._producer is None:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
            )

        await self._producer.start()
        logger.info(f"Event publisher started, topic={self.topic}")

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("Event publisher stopped")

    async def _publish(self, event: ServiceEvent) -> None:
        """Publish an event to Kafka.

        Args:
            event: The event to publish.
        """
        if self._producer is None:
            logger.warning("Event publisher not started, skipping event")
            return

        try:
            key = f"{event.service_name}".encode()
            value = event.to_bytes()

            await self._producer.send_and_wait(
                self.topic,
                value=value,
                key=key,
            )

            logger.debug(
                f"Published {event.event_type.value} event "
                f"for {event.service_name}/{event.instance_id}"
            )

        except Exception as e:
            logger.error(
                f"Failed to publish {event.event_type.value} event "
                f"for {event.service_name}/{event.instance_id}: {e}"
            )

    async def publish_registered(self, registration: ServiceRegistration) -> None:
        """Publish service registered event.

        Args:
            registration: The service registration.
        """
        event = ServiceRegisteredEvent.from_registration(registration)
        await self._publish(event)

    async def publish_deregistered(
        self,
        service_name: str,
        instance_id: str,
        version: str,
        reason: str,
    ) -> None:
        """Publish service deregistered event.

        Args:
            service_name: Name of the service.
            instance_id: Instance ID.
            version: Service version.
            reason: Reason for deregistration.
        """
        event = ServiceDeregisteredEvent(
            service_name=service_name,
            instance_id=instance_id,
            version=version,
            reason=reason,
        )
        await self._publish(event)

    async def publish_health_changed(
        self,
        transition: HealthTransition,
        version: str,
    ) -> None:
        """Publish health status changed event.

        Args:
            transition: The health transition.
            version: Service version.
        """
        event = ServiceHealthChangedEvent.from_transition(transition, version)
        await self._publish(event)


class TenantCreatedEvent(BaseModel):
    """Event emitted when a tenant is created."""

    event_type: str = EventType.TENANT_CREATED
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tenant_id: str
    tenant_slug: str
    tenant_name: str
    keycloak_org_id: str | None
    admin_email: str | None
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: str

    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)

    def to_bytes(self) -> bytes:
        """Serialize event to bytes for Kafka."""
        return self.to_json().encode("utf-8")


class TenantDeletedEvent(BaseModel):
    """Event emitted when a tenant is soft deleted."""

    event_type: str = EventType.TENANT_DELETED
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tenant_id: str
    tenant_slug: str
    tenant_name: str
    deletion_reason: str
    deleted_at: str
    purge_at: str

    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)

    def to_bytes(self) -> bytes:
        """Serialize event to bytes for Kafka."""
        return self.to_json().encode("utf-8")


class TenantPurgedEvent(BaseModel):
    """Event emitted when a tenant is permanently purged."""

    event_type: str = EventType.TENANT_PURGED
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tenant_id: str
    tenant_slug: str
    tenant_name: str
    keycloak_org_id: str | None
    deleted_at: str | None
    purged_at: str

    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)

    def to_bytes(self) -> bytes:
        """Serialize event to bytes for Kafka."""
        return self.to_json().encode("utf-8")


class TenantExportEvent(BaseModel):
    """Event emitted during tenant data export operations."""

    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    export_id: str
    tenant_id: str
    status: str
    records_exported: int = 0
    models_exported: list[str] = Field(default_factory=list)
    reason: str
    created_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None

    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)

    def to_bytes(self) -> bytes:
        """Serialize event to bytes for Kafka."""
        return self.to_json().encode("utf-8")


class TenantEventPublisher:
    """Publishes tenant lifecycle events to Kafka.

    This is a specialized publisher for tenant events that publishes to
    the tenant lifecycle topic separate from service events.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "platform.tenant.lifecycle",
    ):
        """Initialize tenant event publisher.

        Args:
            bootstrap_servers: Kafka bootstrap servers.
            topic: Topic to publish tenant events to.
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start the Kafka producer."""
        if self._producer is None:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
            )

        await self._producer.start()
        logger.info(f"Tenant event publisher started, topic={self.topic}")

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("Tenant event publisher stopped")

    async def _publish(
        self, event: TenantCreatedEvent | TenantDeletedEvent | TenantPurgedEvent | TenantExportEvent
    ) -> None:
        """Publish a tenant event to Kafka.

        Args:
            event: The tenant event to publish.
        """
        if self._producer is None:
            logger.warning("Tenant event publisher not started, skipping event")
            return

        try:
            key = f"tenant.{event.tenant_id}".encode()
            value = event.to_bytes()

            await self._producer.send_and_wait(
                self.topic,
                value=value,
                key=key,
            )

            # Handle different event types for logging
            tenant_slug = getattr(event, "tenant_slug", "unknown")
            logger.info(
                f"Published {event.event_type} event for tenant {tenant_slug} ({event.tenant_id})"
            )

        except Exception as e:
            logger.error(
                f"Failed to publish {event.event_type} event "
                f"for tenant {event.tenant_slug} ({event.tenant_id}): {e}"
            )
            # Re-raise the exception to allow retry logic in callers
            raise

    async def publish_tenant_created(
        self,
        tenant_id: str,
        tenant_slug: str,
        tenant_name: str,
        keycloak_org_id: str | None,
        admin_email: str | None,
        config: dict[str, Any] | None,
        created_at: str,
    ) -> None:
        """Publish tenant created event.

        Args:
            tenant_id: UUID of the created tenant
            tenant_slug: Slug of the created tenant
            tenant_name: Name of the created tenant
            keycloak_org_id: Keycloak organization ID (if created)
            admin_email: Admin user email (if provided)
            config: Tenant configuration (if any)
            created_at: ISO timestamp when created
        """
        event = TenantCreatedEvent(
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            tenant_name=tenant_name,
            keycloak_org_id=keycloak_org_id,
            admin_email=admin_email,
            config=config or {},
            created_at=created_at,
        )
        await self._publish(event)

    async def publish_tenant_deleted(
        self,
        tenant_id: str,
        tenant_slug: str,
        tenant_name: str,
        deletion_reason: str,
        deleted_at: str,
        purge_at: str,
    ) -> None:
        """Publish tenant deleted event.

        Args:
            tenant_id: UUID of the deleted tenant
            tenant_slug: Slug of the deleted tenant
            tenant_name: Name of the deleted tenant
            deletion_reason: Reason for deletion
            deleted_at: ISO timestamp when deleted
            purge_at: ISO timestamp when purge is scheduled
        """
        event = TenantDeletedEvent(
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            tenant_name=tenant_name,
            deletion_reason=deletion_reason,
            deleted_at=deleted_at,
            purge_at=purge_at,
        )
        await self._publish(event)

    async def publish_tenant_purged(
        self,
        tenant_id: str,
        tenant_slug: str,
        tenant_name: str,
        keycloak_org_id: str | None,
        deleted_at: str | None,
        purged_at: str,
    ) -> None:
        """Publish tenant purged event.

        Args:
            tenant_id: UUID of the purged tenant
            tenant_slug: Slug of the purged tenant
            tenant_name: Name of the purged tenant
            keycloak_org_id: Keycloak organization ID (if any)
            deleted_at: ISO timestamp when deleted (if available)
            purged_at: ISO timestamp when purged
        """
        event = TenantPurgedEvent(
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            tenant_name=tenant_name,
            keycloak_org_id=keycloak_org_id,
            deleted_at=deleted_at,
            purged_at=purged_at,
        )
        await self._publish(event)

    async def publish_export_event(
        self,
        event_type: str,
        export_id: str,
        tenant_id: str,
        status: str,
        records_exported: int = 0,
        models_exported: list[str] = None,
        reason: str = "",
        created_at: str | None = None,
        completed_at: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Publish tenant export event.

        Args:
            event_type: Type of export event
            export_id: Unique export identifier
            tenant_id: UUID of the tenant
            status: Export status
            records_exported: Number of records exported
            models_exported: List of models included in export
            reason: Reason for export
            created_at: ISO timestamp when export was created
            completed_at: ISO timestamp when export completed
            error_message: Error message if failed
        """
        event = TenantExportEvent(
            event_type=event_type,
            export_id=export_id,
            tenant_id=tenant_id,
            status=status,
            records_exported=records_exported,
            models_exported=models_exported or [],
            reason=reason,
            created_at=created_at,
            completed_at=completed_at,
            error_message=error_message,
        )
        await self._publish(event)
