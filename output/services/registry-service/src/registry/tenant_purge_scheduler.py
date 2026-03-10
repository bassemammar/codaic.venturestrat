"""Tenant purge scheduler for automatic cleanup of deleted tenants.

This module provides a background scheduler that periodically checks for
soft-deleted tenants that are past their purge date and permanently
deletes them.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from typing import Any, Optional

import structlog

from registry.config import settings
from registry.tenant_service import TenantService

try:
    from venturestrat_observability import get_metrics_api

    metrics_available = True
except ImportError:
    metrics_available = False

logger = structlog.get_logger(__name__)


class TenantPurgeScheduler:
    """Background scheduler for tenant purge operations.

    Periodically scans for tenants eligible for purging (30 days after deletion)
    and permanently removes them from the system.
    """

    def __init__(
        self,
        tenant_service: TenantService,
        check_interval: int = 3600,  # Check every hour by default
        enabled: bool = True,
    ):
        """Initialize the purge scheduler.

        Args:
            tenant_service: Service instance for tenant operations
            check_interval: Seconds between purge checks (default: 1 hour)
            enabled: Whether the scheduler is enabled
        """
        self.tenant_service = tenant_service
        self.check_interval = check_interval
        self.enabled = enabled
        self._task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

        # Initialize metrics if available
        self._metrics = None
        if metrics_available:
            try:
                self._metrics = get_metrics_api()
                self._purge_cycles_counter = self._metrics.counter(
                    "treasury_tenant_purge_cycles_total",
                    "Total tenant purge cycles executed",
                    labels=["status"],
                )
                self._tenants_purged_counter = self._metrics.counter(
                    "treasury_tenants_purged_total", "Total tenants permanently deleted", labels=[]
                )
                self._purge_errors_counter = self._metrics.counter(
                    "treasury_tenant_purge_errors_total",
                    "Total tenant purge errors",
                    labels=["error_type"],
                )
                self._purge_duration_histogram = self._metrics.histogram(
                    "treasury_tenant_purge_cycle_duration_seconds",
                    "Time taken for tenant purge cycles",
                    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
                )
                logger.info("tenant_purge_metrics_initialized")
            except Exception as e:
                logger.warning("failed_to_initialize_purge_metrics", error=str(e))
                self._metrics = None

    async def start(self) -> None:
        """Start the purge scheduler background task."""
        if not self.enabled:
            logger.info("tenant_purge_scheduler_disabled")
            return

        if self._task is not None:
            logger.warning("tenant_purge_scheduler_already_running")
            return

        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._run_scheduler())

        logger.info("tenant_purge_scheduler_started", check_interval=self.check_interval)

    async def stop(self) -> None:
        """Stop the purge scheduler background task."""
        if self._task is None:
            return

        logger.info("stopping_tenant_purge_scheduler")

        # Signal shutdown
        self._shutdown_event.set()

        # Wait for task to complete
        try:
            await asyncio.wait_for(self._task, timeout=30.0)
        except TimeoutError:
            logger.warning("tenant_purge_scheduler_stop_timeout")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._task = None
        logger.info("tenant_purge_scheduler_stopped")

    async def run_purge_cycle(self) -> dict[str, Any]:
        """Run a single purge cycle manually.

        Returns:
            Dictionary with purge statistics
        """
        start_time = datetime.now(UTC)

        try:
            # Get tenants eligible for purge
            eligible_tenants = await self.tenant_service.get_tenants_for_purge()

            if not eligible_tenants:
                logger.info("no_tenants_eligible_for_purge")
                end_time = datetime.now(UTC)
                duration = (end_time - start_time).total_seconds()

                # Record metrics
                if self._metrics:
                    try:
                        self._purge_cycles_counter.labels(status="success").inc()
                        self._purge_duration_histogram.observe(duration)
                    except Exception as e:
                        logger.warning("metrics_recording_failed", error=str(e))

                return {
                    "tenants_checked": 0,
                    "tenants_purged": 0,
                    "errors": 0,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                }

            logger.info(
                "found_tenants_for_purge",
                count=len(eligible_tenants),
                tenant_ids=[t.id for t in eligible_tenants],
            )

            purged_count = 0
            errors = 0
            error_types = {}

            for tenant in eligible_tenants:
                purge_success = False
                last_error = None

                # Retry logic for individual tenant purge
                for attempt in range(1, settings.tenant_purge_retry_count + 1):
                    try:
                        purged = await self.tenant_service.purge_tenant(tenant.id)
                        if purged:
                            purged_count += 1
                            purge_success = True

                            # Record metrics
                            if self._metrics:
                                try:
                                    self._tenants_purged_counter.inc()
                                except Exception as e:
                                    logger.warning("metrics_recording_failed", error=str(e))

                            logger.info(
                                "tenant_auto_purged",
                                tenant_id=tenant.id,
                                tenant_slug=tenant.slug,
                                deleted_at=tenant.deleted_at.isoformat()
                                if tenant.deleted_at
                                else None,
                                attempt=attempt,
                            )
                            break
                        else:
                            logger.warning(
                                "tenant_purge_failed",
                                tenant_id=tenant.id,
                                reason="purge_tenant returned False",
                                attempt=attempt,
                            )
                            last_error = "purge_returned_false"

                            if attempt < settings.tenant_purge_retry_count:
                                await asyncio.sleep(settings.tenant_purge_retry_delay)

                    except Exception as e:
                        error_type = type(e).__name__
                        last_error = str(e)

                        logger.error(
                            "tenant_purge_error",
                            tenant_id=tenant.id,
                            tenant_slug=tenant.slug,
                            error=str(e),
                            error_type=error_type,
                            attempt=attempt,
                        )

                        # Count error types for metrics
                        error_types[error_type] = error_types.get(error_type, 0) + 1

                        # Retry with exponential backoff
                        if attempt < settings.tenant_purge_retry_count:
                            wait_time = min(
                                settings.tenant_purge_retry_delay * (2 ** (attempt - 1)), 1800
                            )  # Max 30 minutes
                            logger.info(
                                "tenant_purge_retrying",
                                tenant_id=tenant.id,
                                attempt=attempt,
                                wait_time=wait_time,
                            )
                            await asyncio.sleep(wait_time)

                if not purge_success:
                    errors += 1
                    logger.error(
                        "tenant_purge_exhausted_retries",
                        tenant_id=tenant.id,
                        tenant_slug=tenant.slug,
                        final_error=last_error,
                        total_attempts=settings.tenant_purge_retry_count,
                    )

            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            # Record metrics
            if self._metrics:
                try:
                    status = (
                        "success"
                        if errors == 0
                        else "partial_failure"
                        if purged_count > 0
                        else "failure"
                    )
                    self._purge_cycles_counter.labels(status=status).inc()
                    self._purge_duration_histogram.observe(duration)

                    # Record errors by type
                    for error_type, count in error_types.items():
                        self._purge_errors_counter.labels(error_type=error_type).inc(count)

                except Exception as e:
                    logger.warning("metrics_recording_failed", error=str(e))

            result = {
                "tenants_checked": len(eligible_tenants),
                "tenants_purged": purged_count,
                "errors": errors,
                "error_types": error_types,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
            }

            logger.info("tenant_purge_cycle_completed", **result)
            return result

        except Exception as e:
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            # Record cycle failure metrics
            if self._metrics:
                try:
                    self._purge_cycles_counter.labels(status="error").inc()
                    self._purge_duration_histogram.observe(duration)
                    self._purge_errors_counter.labels(error_type="cycle_failure").inc()
                except Exception as metric_error:
                    logger.warning("metrics_recording_failed", error=str(metric_error))

            logger.error("tenant_purge_cycle_failed", error=str(e), duration_seconds=duration)
            raise

    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        logger.info("tenant_purge_scheduler_loop_started")

        while not self._shutdown_event.is_set():
            try:
                # Run purge cycle
                await self.run_purge_cycle()

            except Exception as e:
                logger.error("tenant_purge_scheduler_error", error=str(e))

            # Wait for next cycle or shutdown
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.check_interval)
                # If we get here, shutdown was signaled
                break
            except TimeoutError:
                # Timeout is expected - continue with next cycle
                continue

        logger.info("tenant_purge_scheduler_loop_stopped")


# Configuration helpers
def create_tenant_purge_scheduler(tenant_service: TenantService) -> TenantPurgeScheduler:
    """Create a tenant purge scheduler with default configuration.

    Args:
        tenant_service: Tenant service instance

    Returns:
        Configured purge scheduler
    """
    # Check if purge scheduler is enabled in settings
    enabled = getattr(settings, "tenant_purge_enabled", True)
    check_interval = getattr(settings, "tenant_purge_check_interval", 3600)

    logger.info("creating_tenant_purge_scheduler", enabled=enabled, check_interval=check_interval)

    return TenantPurgeScheduler(
        tenant_service=tenant_service, check_interval=check_interval, enabled=enabled
    )
