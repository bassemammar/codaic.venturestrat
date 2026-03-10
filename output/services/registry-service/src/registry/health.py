"""Health check management for the Registry Service.

This module provides health status tracking, transition detection,
and health check configuration building.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field

from registry.models import HealthCheckConfig, HealthStatus

logger = logging.getLogger(__name__)


class HealthCheckResult(BaseModel):
    """Result of a health check execution."""

    instance_id: str
    service_name: str
    status: HealthStatus
    check_name: str
    output: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @computed_field
    @property
    def is_healthy(self) -> bool:
        """Check if result indicates healthy status."""
        return self.status == HealthStatus.HEALTHY


class HealthTransition(BaseModel):
    """Represents a health status transition."""

    instance_id: str
    service_name: str
    previous_status: HealthStatus
    new_status: HealthStatus
    check_name: str
    check_output: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @computed_field
    @property
    def is_degradation(self) -> bool:
        """Check if transition is a degradation (healthy -> unhealthy)."""
        healthy_to_unhealthy = self.previous_status == HealthStatus.HEALTHY and self.new_status in (
            HealthStatus.WARNING,
            HealthStatus.CRITICAL,
        )
        warning_to_critical = (
            self.previous_status == HealthStatus.WARNING
            and self.new_status == HealthStatus.CRITICAL
        )
        return healthy_to_unhealthy or warning_to_critical

    @computed_field
    @property
    def is_recovery(self) -> bool:
        """Check if transition is a recovery (unhealthy -> healthy)."""
        return (
            self.previous_status in (HealthStatus.WARNING, HealthStatus.CRITICAL)
            and self.new_status == HealthStatus.HEALTHY
        )


class HealthManager:
    """Manages health status tracking and transitions.

    Tracks the health status of all service instances and detects
    status transitions for event publishing.

    Usage:
        manager = HealthManager()

        # Record a health check result
        transition = manager.record_check(result)
        if transition:
            # Status changed, publish event
            await event_publisher.publish_health_changed(transition)

        # Query health status
        status = manager.get_status("instance-123")
        unhealthy = manager.get_unhealthy_instances()
    """

    def __init__(self):
        """Initialize health manager."""
        self._statuses: dict[str, HealthStatus] = {}
        self._service_names: dict[str, str] = {}
        self._last_checks: dict[str, HealthCheckResult] = {}

    def record_check(self, result: HealthCheckResult) -> HealthTransition | None:
        """Record a health check result and detect transitions.

        Args:
            result: The health check result.

        Returns:
            HealthTransition if status changed, None otherwise.
        """
        instance_id = result.instance_id
        previous_status = self._statuses.get(instance_id)

        # Update current status
        self._statuses[instance_id] = result.status
        self._service_names[instance_id] = result.service_name
        self._last_checks[instance_id] = result

        # Check for transition
        if previous_status is not None and previous_status != result.status:
            transition = HealthTransition(
                instance_id=instance_id,
                service_name=result.service_name,
                previous_status=previous_status,
                new_status=result.status,
                check_name=result.check_name,
                check_output=result.output,
            )
            logger.info(
                f"Health transition for {result.service_name}/{instance_id}: "
                f"{previous_status.value} -> {result.status.value}"
            )
            return transition

        return None

    def get_status(self, instance_id: str) -> HealthStatus | None:
        """Get current health status of an instance.

        Args:
            instance_id: The service instance ID.

        Returns:
            Current health status or None if not tracked.
        """
        return self._statuses.get(instance_id)

    def get_all_statuses(self) -> dict[str, HealthStatus]:
        """Get health status of all tracked instances.

        Returns:
            Dict mapping instance IDs to their status.
        """
        return dict(self._statuses)

    def get_healthy_instances(self) -> list[str]:
        """Get list of healthy instance IDs.

        Returns:
            List of instance IDs with HEALTHY status.
        """
        return [
            instance_id
            for instance_id, status in self._statuses.items()
            if status == HealthStatus.HEALTHY
        ]

    def get_unhealthy_instances(self) -> list[str]:
        """Get list of unhealthy instance IDs.

        Returns:
            List of instance IDs with WARNING or CRITICAL status.
        """
        return [
            instance_id
            for instance_id, status in self._statuses.items()
            if status in (HealthStatus.WARNING, HealthStatus.CRITICAL)
        ]

    def clear_instance(self, instance_id: str) -> None:
        """Remove an instance from tracking.

        Args:
            instance_id: The service instance ID.
        """
        self._statuses.pop(instance_id, None)
        self._service_names.pop(instance_id, None)
        self._last_checks.pop(instance_id, None)

    def build_consul_check(
        self,
        config: HealthCheckConfig,
        address: str,
        port: int,
    ) -> dict[str, Any]:
        """Build Consul health check configuration.

        Args:
            config: Health check configuration.
            address: Service address.
            port: Service port.

        Returns:
            Consul health check configuration dict.
        """
        check: dict[str, Any] = {
            "interval": f"{config.interval_seconds}s",
            "timeout": f"{config.timeout_seconds}s",
            "deregister_critical_service_after": f"{config.deregister_after_seconds}s",
        }

        if config.http_endpoint:
            check["http"] = f"http://{address}:{port}{config.http_endpoint}"
        elif config.grpc_service:
            check["grpc"] = f"{address}:{port}/{config.grpc_service}"
        elif config.tcp_address:
            check["tcp"] = config.tcp_address
        else:
            # Default to HTTP health endpoint
            check["http"] = f"http://{address}:{port}/health"

        return check
