"""Health monitoring service for periodic pricer health checks.

This module provides automated health monitoring for registered pricers,
integrating with the circuit breaker pattern and health status tracking.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from registry.health import HealthCheckResult, HealthManager, HealthStatus
from registry.models.pricer_registry import PricerRegistry, PricerStatus

logger = logging.getLogger(__name__)


class HealthCheckConfig(BaseModel):
    """Configuration for health check monitoring."""

    check_interval_seconds: int = Field(default=30, description="Interval between health checks")
    timeout_seconds: int = Field(default=10, description="Timeout for each health check")
    failure_threshold: int = Field(
        default=3, description="Consecutive failures before marking unhealthy"
    )
    recovery_threshold: int = Field(
        default=2, description="Consecutive successes before marking healthy"
    )
    retry_backoff_seconds: int = Field(
        default=60, description="Backoff time after marking unhealthy"
    )
    max_concurrent_checks: int = Field(default=10, description="Maximum concurrent health checks")


class PricerHealthStatus(BaseModel):
    """Health status for a specific pricer."""

    pricer_id: str
    status: PricerStatus
    last_check_time: datetime
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None

    def is_healthy(self) -> bool:
        """Check if pricer is healthy."""
        return self.status == PricerStatus.HEALTHY

    def should_check(self, config: HealthCheckConfig) -> bool:
        """Determine if pricer should be checked based on config and status."""
        time_since_check = (datetime.now(UTC) - self.last_check_time).total_seconds()

        if self.is_healthy():
            # Regular interval for healthy pricers
            return time_since_check >= config.check_interval_seconds
        else:
            # Backoff interval for unhealthy pricers
            return time_since_check >= config.retry_backoff_seconds


class HealthMonitoringService:
    """
    Service for monitoring pricer health with circuit breaker integration.

    Performs periodic health checks on all registered pricers, tracks status
    transitions, and integrates with the circuit breaker pattern for resilience.

    Features:
    - Periodic health checks with configurable intervals
    - Circuit breaker integration for failure detection
    - Automatic status transitions (healthy -> unhealthy -> healthy)
    - Backoff strategy for unhealthy services
    - Concurrent health checking with limits
    - Health metrics and status aggregation

    Usage:
        config = HealthCheckConfig(check_interval_seconds=30)
        monitor = HealthMonitoringService(config)

        # Register status change callback
        monitor.add_status_change_callback(on_pricer_status_change)

        # Start monitoring
        await monitor.start()

        # Monitor runs in background...

        # Stop monitoring
        await monitor.stop()
    """

    def __init__(
        self,
        config: Optional[HealthCheckConfig] = None,
        get_pricers_callback: Optional[Callable[[], list[PricerRegistry]]] = None,
        update_pricer_callback: Optional[Callable[[PricerRegistry], None]] = None,
    ):
        """
        Initialize health monitoring service.

        Args:
            config: Health check configuration
            get_pricers_callback: Function to get list of registered pricers
            update_pricer_callback: Function to update pricer status in database
        """
        self.config = config or HealthCheckConfig()
        self.get_pricers_callback = get_pricers_callback
        self.update_pricer_callback = update_pricer_callback

        # Health tracking
        self.health_manager = HealthManager()
        self._pricer_statuses: dict[str, PricerHealthStatus] = {}
        self._status_change_callbacks: list[Callable[[str, PricerStatus, PricerStatus], None]] = []

        # Monitoring control
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._http_client: Optional[httpx.AsyncClient] = None

        # Metrics
        self._total_checks = 0
        self._successful_checks = 0
        self._failed_checks = 0
        self._last_check_duration = 0.0

        logger.info(f"Health monitoring service initialized with config: {self.config}")

    async def start(self) -> None:
        """Start the health monitoring service."""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Health monitoring already running")
            return

        # Initialize HTTP client
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout_seconds),
            limits=httpx.Limits(max_connections=self.config.max_concurrent_checks),
        )

        # Start monitoring task
        self._shutdown_event.clear()
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info("Health monitoring service started")

    async def stop(self) -> None:
        """Stop the health monitoring service."""
        logger.info("Stopping health monitoring service...")

        # Signal shutdown
        self._shutdown_event.set()

        # Wait for monitoring task to complete
        if self._monitoring_task:
            try:
                await asyncio.wait_for(self._monitoring_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Health monitoring task did not stop gracefully")
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass

        # Close HTTP client
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        logger.info("Health monitoring service stopped")

    def add_status_change_callback(
        self, callback: Callable[[str, PricerStatus, PricerStatus], None]
    ) -> None:
        """
        Add callback for pricer status changes.

        Args:
            callback: Function called when pricer status changes.
                     Signature: (pricer_id, old_status, new_status)
        """
        self._status_change_callbacks.append(callback)

    def get_pricer_health_status(self, pricer_id: str) -> Optional[PricerHealthStatus]:
        """Get current health status for a pricer."""
        return self._pricer_statuses.get(pricer_id)

    def get_all_health_statuses(self) -> dict[str, PricerHealthStatus]:
        """Get health statuses for all monitored pricers."""
        return dict(self._pricer_statuses)

    def get_healthy_pricers(self) -> list[str]:
        """Get list of healthy pricer IDs."""
        return [
            pricer_id for pricer_id, status in self._pricer_statuses.items() if status.is_healthy()
        ]

    def get_unhealthy_pricers(self) -> list[str]:
        """Get list of unhealthy pricer IDs."""
        return [
            pricer_id
            for pricer_id, status in self._pricer_statuses.items()
            if not status.is_healthy()
        ]

    def get_metrics(self) -> dict[str, Any]:
        """Get health monitoring metrics."""
        healthy_count = len(self.get_healthy_pricers())
        unhealthy_count = len(self.get_unhealthy_pricers())

        return {
            "total_pricers": len(self._pricer_statuses),
            "healthy_pricers": healthy_count,
            "unhealthy_pricers": unhealthy_count,
            "health_ratio": healthy_count / len(self._pricer_statuses)
            if self._pricer_statuses
            else 1.0,
            "total_checks": self._total_checks,
            "successful_checks": self._successful_checks,
            "failed_checks": self._failed_checks,
            "success_rate": self._successful_checks / self._total_checks
            if self._total_checks
            else 1.0,
            "last_check_duration_seconds": self._last_check_duration,
            "check_interval_seconds": self.config.check_interval_seconds,
            "is_running": self._monitoring_task and not self._monitoring_task.done(),
        }

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("Health monitoring loop started")

        while not self._shutdown_event.is_set():
            try:
                start_time = time.time()

                # Get current pricers to monitor
                if self.get_pricers_callback:
                    pricers = await self._get_pricers_safe()
                else:
                    pricers = []

                # Update tracking for new/removed pricers
                await self._update_tracked_pricers(pricers)

                # Check pricers that need checking
                await self._check_pricers_needing_check()

                # Update metrics
                self._last_check_duration = time.time() - start_time

                # Wait for next check interval
                await asyncio.wait_for(
                    self._shutdown_event.wait(), timeout=self.config.check_interval_seconds
                )

            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                continue
            except asyncio.CancelledError:
                logger.info("Health monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {str(e)}", exc_info=True)
                await asyncio.sleep(5)  # Brief pause before retrying

        logger.info("Health monitoring loop stopped")

    async def _get_pricers_safe(self) -> list[PricerRegistry]:
        """Safely get pricers list with error handling."""
        try:
            return await self.get_pricers_callback()
        except Exception as e:
            logger.error(f"Failed to get pricers list: {str(e)}")
            return []

    async def _update_tracked_pricers(self, current_pricers: list[PricerRegistry]) -> None:
        """Update tracking for current list of pricers."""
        current_pricer_ids = {p.pricer_id for p in current_pricers}
        tracked_pricer_ids = set(self._pricer_statuses.keys())

        # Add new pricers
        new_pricers = current_pricer_ids - tracked_pricer_ids
        for pricer_id in new_pricers:
            pricer = next(p for p in current_pricers if p.pricer_id == pricer_id)
            self._pricer_statuses[pricer_id] = PricerHealthStatus(
                pricer_id=pricer_id,
                status=PricerStatus(pricer.status),
                last_check_time=datetime.now(UTC)
                - timedelta(
                    seconds=self.config.check_interval_seconds * 2
                ),  # Force immediate check
            )
            logger.info(f"Started monitoring pricer: {pricer_id}")

        # Remove deleted pricers
        removed_pricers = tracked_pricer_ids - current_pricer_ids
        for pricer_id in removed_pricers:
            del self._pricer_statuses[pricer_id]
            self.health_manager.clear_instance(pricer_id)
            logger.info(f"Stopped monitoring pricer: {pricer_id}")

    async def _check_pricers_needing_check(self) -> None:
        """Check pricers that need health checking."""
        # Find pricers that need checking
        pricers_to_check = [
            (pricer_id, status)
            for pricer_id, status in self._pricer_statuses.items()
            if status.should_check(self.config)
        ]

        if not pricers_to_check:
            return

        logger.debug(f"Checking health of {len(pricers_to_check)} pricers")

        # Create semaphore to limit concurrent checks
        semaphore = asyncio.Semaphore(self.config.max_concurrent_checks)

        # Check pricers concurrently
        check_tasks = [
            self._check_pricer_health_with_semaphore(semaphore, pricer_id, status)
            for pricer_id, status in pricers_to_check
        ]

        await asyncio.gather(*check_tasks, return_exceptions=True)

    async def _check_pricer_health_with_semaphore(
        self, semaphore: asyncio.Semaphore, pricer_id: str, current_status: PricerHealthStatus
    ) -> None:
        """Check single pricer health with semaphore protection."""
        async with semaphore:
            await self._check_pricer_health(pricer_id, current_status)

    async def _check_pricer_health(
        self, pricer_id: str, current_status: PricerHealthStatus
    ) -> None:
        """Check health of a single pricer."""
        if not self._http_client:
            return

        # Get pricer for health check URL
        try:
            if self.get_pricers_callback:
                pricers = await self._get_pricers_safe()
                pricer = next((p for p in pricers if p.pricer_id == pricer_id), None)
                if not pricer:
                    logger.warning(f"Pricer {pricer_id} not found for health check")
                    return
            else:
                logger.warning("No get_pricers_callback configured")
                return
        except Exception as e:
            logger.error(f"Failed to get pricer {pricer_id} for health check: {str(e)}")
            return

        start_time = time.time()
        self._total_checks += 1

        try:
            # Perform HTTP health check
            response = await self._http_client.get(pricer.health_check_url)
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            if response.status_code == 200:
                # Health check succeeded
                logger.info(
                    f"[DEBUG] Health check SUCCESS for {pricer_id}: HTTP 200, response_time={response_time:.1f}ms"
                )
                await self._handle_health_check_success(pricer_id, current_status, response_time)
                self._successful_checks += 1

            else:
                # Health check returned non-200
                error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                logger.warning(f"[DEBUG] Health check FAILED for {pricer_id}: {error_msg}")
                await self._handle_health_check_failure(pricer_id, current_status, error_msg)
                self._failed_checks += 1

        except Exception as e:
            # Health check failed (network error, timeout, etc.)
            response_time = (time.time() - start_time) * 1000
            error_msg = f"{type(e).__name__}: {str(e)}"
            await self._handle_health_check_failure(pricer_id, current_status, error_msg)
            self._failed_checks += 1

            logger.debug(f"Health check failed for {pricer_id}: {error_msg}")

    async def _handle_health_check_success(
        self, pricer_id: str, current_status: PricerHealthStatus, response_time: float
    ) -> None:
        """Handle successful health check."""
        # Update status tracking
        current_status.last_check_time = datetime.now(UTC)
        current_status.consecutive_failures = 0
        current_status.consecutive_successes += 1
        current_status.response_time_ms = response_time
        current_status.error_message = None

        # Check if we should transition to healthy
        old_status = current_status.status
        if (
            current_status.status != PricerStatus.HEALTHY
            and current_status.consecutive_successes >= self.config.recovery_threshold
        ):
            current_status.status = PricerStatus.HEALTHY
            await self._notify_status_change(pricer_id, old_status, PricerStatus.HEALTHY)

            # Update database
            if self.update_pricer_callback:
                await self._update_pricer_status_safe(pricer_id, PricerStatus.HEALTHY)

            logger.info(f"Pricer {pricer_id} recovered: {old_status} -> {PricerStatus.HEALTHY}")

        # Record health check result
        health_result = HealthCheckResult(
            instance_id=pricer_id,
            service_name=f"pricer-{pricer_id}",
            status=HealthStatus.HEALTHY,
            check_name="http_health_check",
            output=f"Response time: {response_time:.1f}ms",
        )
        transition = self.health_manager.record_check(health_result)

        logger.debug(f"Health check succeeded for {pricer_id}: {response_time:.1f}ms")

    async def _handle_health_check_failure(
        self, pricer_id: str, current_status: PricerHealthStatus, error_message: str
    ) -> None:
        """Handle failed health check."""
        # Update status tracking
        current_status.last_check_time = datetime.now(UTC)
        current_status.consecutive_successes = 0
        current_status.consecutive_failures += 1
        current_status.error_message = error_message
        current_status.response_time_ms = None

        # Check if we should transition to unhealthy
        old_status = current_status.status
        if (
            current_status.status == PricerStatus.HEALTHY
            and current_status.consecutive_failures >= self.config.failure_threshold
        ):
            current_status.status = PricerStatus.UNHEALTHY
            await self._notify_status_change(pricer_id, old_status, PricerStatus.UNHEALTHY)

            # Update database
            if self.update_pricer_callback:
                await self._update_pricer_status_safe(pricer_id, PricerStatus.UNHEALTHY)

            logger.warning(
                f"Pricer {pricer_id} marked unhealthy: {old_status} -> {PricerStatus.UNHEALTHY} (error: {error_message})"
            )

        # Record health check result
        health_result = HealthCheckResult(
            instance_id=pricer_id,
            service_name=f"pricer-{pricer_id}",
            status=HealthStatus.CRITICAL,
            check_name="http_health_check",
            output=error_message,
        )
        transition = self.health_manager.record_check(health_result)

    async def _notify_status_change(
        self, pricer_id: str, old_status: PricerStatus, new_status: PricerStatus
    ) -> None:
        """Notify registered callbacks of status change."""
        for callback in self._status_change_callbacks:
            try:
                callback(pricer_id, old_status, new_status)
            except Exception as e:
                logger.error(f"Error in status change callback: {str(e)}", exc_info=True)

    async def _update_pricer_status_safe(self, pricer_id: str, status: PricerStatus) -> None:
        """Safely update pricer status in database."""
        logger.info(
            f"[DEBUG] Attempting to update pricer status in database: pricer_id={pricer_id}, status={status}"
        )
        try:
            # Create updated pricer model
            if self.get_pricers_callback:
                pricers = await self._get_pricers_safe()
                pricer = next((p for p in pricers if p.pricer_id == pricer_id), None)
                logger.info(
                    f"[DEBUG] Retrieved pricer from callback: pricer_id={pricer_id}, pricer_exists={pricer is not None}"
                )
                if pricer:
                    logger.info(
                        f"[DEBUG] Pricer before update: pricer_id={pricer.pricer_id}, current_status={pricer.status}, last_health_check={pricer.last_health_check}"
                    )
                    if status == PricerStatus.HEALTHY:
                        updated_pricer = pricer.mark_healthy()
                    else:
                        updated_pricer = pricer.mark_unhealthy()

                    logger.info(
                        f"[DEBUG] Pricer after update: pricer_id={updated_pricer.pricer_id}, new_status={updated_pricer.status}, new_last_health_check={updated_pricer.last_health_check}"
                    )
                    logger.info("[DEBUG] Calling update_pricer_callback...")
                    await self.update_pricer_callback(updated_pricer)
                    logger.info(
                        f"[DEBUG] Successfully called update_pricer_callback for {pricer_id}"
                    )
                else:
                    logger.warning(
                        f"[DEBUG] Pricer {pricer_id} not found in pricers list, cannot update status"
                    )
            else:
                logger.warning(
                    "[DEBUG] No get_pricers_callback configured, cannot update pricer status"
                )
        except Exception as e:
            logger.error(
                f"[DEBUG] Failed to update pricer status in database: {str(e)}", exc_info=True
            )


class HealthMonitoringManager:
    """
    Manager for health monitoring service lifecycle.

    Provides high-level interface for starting/stopping health monitoring
    and integrating with the registry service.
    """

    def __init__(self, registry_service_instance=None):
        """
        Initialize health monitoring manager.

        Args:
            registry_service_instance: Registry service for database operations
        """
        self.registry_service = registry_service_instance
        self.monitoring_service: Optional[HealthMonitoringService] = None
        self._initialized = False

    async def initialize(
        self, config: Optional[HealthCheckConfig] = None
    ) -> HealthMonitoringService:
        """
        Initialize health monitoring service.

        Args:
            config: Health check configuration

        Returns:
            Initialized health monitoring service
        """
        if self._initialized:
            return self.monitoring_service

        # Create callbacks for database integration
        get_pricers_callback = None
        update_pricer_callback = None

        if self.registry_service:
            get_pricers_callback = lambda: self.registry_service.list_all_pricers()
            update_pricer_callback = lambda pricer: self.registry_service.update_pricer_health(
                pricer
            )

        # Create monitoring service
        self.monitoring_service = HealthMonitoringService(
            config=config,
            get_pricers_callback=get_pricers_callback,
            update_pricer_callback=update_pricer_callback,
        )

        # Add status change logging
        self.monitoring_service.add_status_change_callback(self._log_status_change)

        self._initialized = True
        logger.info("Health monitoring manager initialized")

        return self.monitoring_service

    async def start(self, config: Optional[HealthCheckConfig] = None) -> None:
        """Start health monitoring service."""
        if not self.monitoring_service:
            await self.initialize(config)

        await self.monitoring_service.start()

    async def stop(self) -> None:
        """Stop health monitoring service."""
        if self.monitoring_service:
            await self.monitoring_service.stop()

    def _log_status_change(
        self, pricer_id: str, old_status: PricerStatus, new_status: PricerStatus
    ) -> None:
        """Log pricer status changes."""
        logger.info(f"Pricer status changed: {pricer_id} {old_status.value} -> {new_status.value}")
