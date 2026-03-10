"""Tests for TenantPurgeScheduler - automatic cleanup of deleted tenants.

These tests verify that the TenantPurgeScheduler properly schedules and executes
purge operations for tenants that have passed their retention period.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from registry.models import Tenant
from registry.tenant_purge_scheduler import TenantPurgeScheduler, create_tenant_purge_scheduler
from registry.tenant_service import TenantService


class TestTenantPurgeScheduler:
    """Tests for TenantPurgeScheduler functionality."""

    def test_init_with_default_settings(self):
        """TenantPurgeScheduler initializes with default settings."""
        mock_service = MagicMock(spec=TenantService)

        scheduler = TenantPurgeScheduler(mock_service)

        assert scheduler.tenant_service == mock_service
        assert scheduler.check_interval == 3600  # 1 hour default
        assert scheduler.enabled is True
        assert scheduler._task is None
        assert not scheduler._shutdown_event.is_set()

    def test_init_with_custom_settings(self):
        """TenantPurgeScheduler initializes with custom settings."""
        mock_service = MagicMock(spec=TenantService)

        scheduler = TenantPurgeScheduler(
            mock_service,
            check_interval=1800,  # 30 minutes
            enabled=False,
        )

        assert scheduler.tenant_service == mock_service
        assert scheduler.check_interval == 1800
        assert scheduler.enabled is False
        assert scheduler._task is None

    @pytest.mark.asyncio
    async def test_start_scheduler_when_enabled(self):
        """start() creates background task when enabled."""
        mock_service = MagicMock(spec=TenantService)
        scheduler = TenantPurgeScheduler(mock_service, enabled=True)

        # Mock the background task creation
        with patch("asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task

            await scheduler.start()

            # Verify task was created
            mock_create_task.assert_called_once()
            assert scheduler._task == mock_task
            assert not scheduler._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_start_scheduler_when_disabled(self):
        """start() does nothing when scheduler is disabled."""
        mock_service = MagicMock(spec=TenantService)
        scheduler = TenantPurgeScheduler(mock_service, enabled=False)

        # Mock the background task creation
        with patch("asyncio.create_task") as mock_create_task:
            await scheduler.start()

            # Verify no task was created
            mock_create_task.assert_not_called()
            assert scheduler._task is None

    @pytest.mark.asyncio
    async def test_start_scheduler_already_running(self):
        """start() does nothing when scheduler already running."""
        mock_service = MagicMock(spec=TenantService)
        scheduler = TenantPurgeScheduler(mock_service, enabled=True)

        # Simulate already running
        existing_task = MagicMock()
        scheduler._task = existing_task

        with patch("asyncio.create_task") as mock_create_task:
            await scheduler.start()

            # Verify no new task was created
            mock_create_task.assert_not_called()
            assert scheduler._task == existing_task

    @pytest.mark.asyncio
    async def test_stop_scheduler(self):
        """stop() properly stops the background task."""
        mock_service = MagicMock(spec=TenantService)
        scheduler = TenantPurgeScheduler(mock_service)

        # Create mock task
        mock_task = AsyncMock()
        scheduler._task = mock_task

        # Mock asyncio.wait_for to simulate successful completion
        with patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait_for:
            await scheduler.stop()

            # Verify shutdown was signaled
            assert scheduler._shutdown_event.is_set()

            # Verify wait_for was called
            mock_wait_for.assert_called_once_with(mock_task, timeout=30.0)

            # Verify task was cleared
            assert scheduler._task is None

    @pytest.mark.asyncio
    async def test_stop_scheduler_timeout(self):
        """stop() cancels task on timeout."""
        mock_service = MagicMock(spec=TenantService)
        scheduler = TenantPurgeScheduler(mock_service)

        # Create mock task
        mock_task = AsyncMock()
        scheduler._task = mock_task

        # Mock asyncio.wait_for to timeout
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            await scheduler.stop()

            # Verify task was cancelled
            mock_task.cancel.assert_called_once()

            # Verify task was awaited after cancel
            mock_task.__await__.assert_called()

            # Verify task was cleared
            assert scheduler._task is None

    @pytest.mark.asyncio
    async def test_stop_scheduler_not_running(self):
        """stop() does nothing when scheduler not running."""
        mock_service = MagicMock(spec=TenantService)
        scheduler = TenantPurgeScheduler(mock_service)

        # No task running
        assert scheduler._task is None

        await scheduler.stop()

        # Should not raise any errors
        assert scheduler._task is None

    @pytest.mark.asyncio
    async def test_run_purge_cycle_no_eligible_tenants(self):
        """run_purge_cycle() returns stats when no tenants eligible."""
        mock_service = AsyncMock(spec=TenantService)
        mock_service.get_tenants_for_purge.return_value = []

        scheduler = TenantPurgeScheduler(mock_service)

        result = await scheduler.run_purge_cycle()

        # Verify result structure
        assert result["tenants_checked"] == 0
        assert result["tenants_purged"] == 0
        assert result["errors"] == 0
        assert "start_time" in result
        assert "end_time" in result

        # Verify service was called
        mock_service.get_tenants_for_purge.assert_called_once()
        mock_service.purge_tenant.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_purge_cycle_with_eligible_tenants(self):
        """run_purge_cycle() purges eligible tenants successfully."""
        mock_service = AsyncMock(spec=TenantService)

        # Mock eligible tenants
        tenant1 = Tenant(
            id="tenant-1-id",
            slug="tenant-1",
            name="Tenant 1",
            status="deleted",
            deleted_at=datetime.now(UTC) - timedelta(days=31),
        )
        tenant2 = Tenant(
            id="tenant-2-id",
            slug="tenant-2",
            name="Tenant 2",
            status="deleted",
            deleted_at=datetime.now(UTC) - timedelta(days=32),
        )

        mock_service.get_tenants_for_purge.return_value = [tenant1, tenant2]
        mock_service.purge_tenant.side_effect = [True, True]  # Both purges succeed

        scheduler = TenantPurgeScheduler(mock_service)

        result = await scheduler.run_purge_cycle()

        # Verify result
        assert result["tenants_checked"] == 2
        assert result["tenants_purged"] == 2
        assert result["errors"] == 0
        assert "duration_seconds" in result

        # Verify service calls
        mock_service.get_tenants_for_purge.assert_called_once()
        assert mock_service.purge_tenant.call_count == 2
        mock_service.purge_tenant.assert_any_call("tenant-1-id")
        mock_service.purge_tenant.assert_any_call("tenant-2-id")

    @pytest.mark.asyncio
    async def test_run_purge_cycle_with_purge_failures(self):
        """run_purge_cycle() handles purge failures gracefully."""
        mock_service = AsyncMock(spec=TenantService)

        # Mock eligible tenants
        tenant1 = Tenant(id="tenant-1-id", slug="tenant-1", name="Tenant 1", status="deleted")
        tenant2 = Tenant(id="tenant-2-id", slug="tenant-2", name="Tenant 2", status="deleted")

        mock_service.get_tenants_for_purge.return_value = [tenant1, tenant2]
        # First purge fails, second succeeds
        mock_service.purge_tenant.side_effect = [Exception("Purge failed"), True]

        scheduler = TenantPurgeScheduler(mock_service)

        result = await scheduler.run_purge_cycle()

        # Verify result accounts for errors
        assert result["tenants_checked"] == 2
        assert result["tenants_purged"] == 1  # One succeeded
        assert result["errors"] == 1  # One failed

    @pytest.mark.asyncio
    async def test_run_purge_cycle_with_purge_returning_false(self):
        """run_purge_cycle() handles purge_tenant returning False."""
        mock_service = AsyncMock(spec=TenantService)

        # Mock eligible tenant
        tenant1 = Tenant(id="tenant-1-id", slug="tenant-1", name="Tenant 1", status="deleted")

        mock_service.get_tenants_for_purge.return_value = [tenant1]
        mock_service.purge_tenant.return_value = False  # Purge failed

        scheduler = TenantPurgeScheduler(mock_service)

        result = await scheduler.run_purge_cycle()

        # Verify result counts it as error
        assert result["tenants_checked"] == 1
        assert result["tenants_purged"] == 0
        assert result["errors"] == 1

    @pytest.mark.asyncio
    async def test_run_purge_cycle_service_error(self):
        """run_purge_cycle() propagates service errors."""
        mock_service = AsyncMock(spec=TenantService)
        mock_service.get_tenants_for_purge.side_effect = Exception("Database error")

        scheduler = TenantPurgeScheduler(mock_service)

        with pytest.raises(Exception, match="Database error"):
            await scheduler.run_purge_cycle()

    @pytest.mark.asyncio
    async def test_scheduler_main_loop_basic(self):
        """_run_scheduler() executes main loop correctly."""
        mock_service = AsyncMock(spec=TenantService)
        mock_service.get_tenants_for_purge.return_value = []

        scheduler = TenantPurgeScheduler(mock_service, check_interval=0.1)  # Fast interval

        # Mock asyncio.wait_for to simulate shutdown after one cycle
        original_wait_for = asyncio.wait_for
        call_count = 0

        async def mock_wait_for(coro, timeout):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call is from run_purge_cycle, let it complete
                return await original_wait_for(coro, timeout)
            else:
                # Second call is waiting for shutdown event, simulate timeout once then shutdown
                if call_count == 2:
                    raise TimeoutError()
                else:
                    scheduler._shutdown_event.set()  # Signal shutdown
                    await asyncio.sleep(0)  # Allow event to be processed

        with patch("asyncio.wait_for", side_effect=mock_wait_for):
            # Run scheduler loop for a short time
            task = asyncio.create_task(scheduler._run_scheduler())

            # Give it time to run one iteration
            await asyncio.sleep(0.2)

            # Signal shutdown
            scheduler._shutdown_event.set()
            await task

            # Verify at least one purge cycle was attempted
            mock_service.get_tenants_for_purge.assert_called()

    @pytest.mark.asyncio
    async def test_scheduler_main_loop_handles_errors(self):
        """_run_scheduler() continues running despite errors."""
        mock_service = AsyncMock(spec=TenantService)
        # First call fails, second call succeeds with empty list
        mock_service.get_tenants_for_purge.side_effect = [Exception("Temporary error"), []]

        scheduler = TenantPurgeScheduler(mock_service, check_interval=0.1)

        # Mock wait_for to allow controlled execution
        call_count = 0

        async def mock_wait_for(coro, timeout):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # Let first two iterations complete
                raise TimeoutError()
            else:
                # Signal shutdown after a few iterations
                scheduler._shutdown_event.set()
                await asyncio.sleep(0)

        with patch("asyncio.wait_for", side_effect=mock_wait_for):
            # Run scheduler
            await scheduler._run_scheduler()

            # Verify multiple calls were made (error didn't stop the loop)
            assert mock_service.get_tenants_for_purge.call_count >= 2


class TestTenantPurgeSchedulerConfigHelpers:
    """Tests for configuration helper functions."""

    def test_create_tenant_purge_scheduler_default_config(self):
        """create_tenant_purge_scheduler() uses default configuration."""
        mock_service = MagicMock(spec=TenantService)

        # Mock settings without purge-specific attributes
        with patch("registry.tenant_purge_scheduler.settings") as mock_settings:
            # Use getattr default values
            type(mock_settings).tenant_purge_enabled = PropertyMock(side_effect=AttributeError)
            type(mock_settings).tenant_purge_check_interval = PropertyMock(
                side_effect=AttributeError
            )

            scheduler = create_tenant_purge_scheduler(mock_service)

        assert scheduler.tenant_service == mock_service
        assert scheduler.enabled is True  # Default
        assert scheduler.check_interval == 3600  # Default

    def test_create_tenant_purge_scheduler_custom_config(self):
        """create_tenant_purge_scheduler() uses custom configuration from settings."""
        mock_service = MagicMock(spec=TenantService)

        # Mock settings with custom purge configuration
        with patch("registry.tenant_purge_scheduler.settings") as mock_settings:
            mock_settings.tenant_purge_enabled = False
            mock_settings.tenant_purge_check_interval = 1800

            scheduler = create_tenant_purge_scheduler(mock_service)

        assert scheduler.tenant_service == mock_service
        assert scheduler.enabled is False
        assert scheduler.check_interval == 1800


class TestTenantPurgeSchedulerIntegration:
    """Integration tests for TenantPurgeScheduler."""

    @pytest.mark.asyncio
    async def test_full_purge_cycle_integration(self):
        """Test complete purge cycle with realistic tenant data."""
        mock_service = AsyncMock(spec=TenantService)

        # Create realistic deleted tenants
        now = datetime.now(UTC)
        tenant1 = Tenant(
            id="550e8400-e29b-41d4-a716-446655440001",
            slug="purge-tenant-1",
            name="Purge Test Tenant 1",
            status="deleted",
            config={
                "deletion_reason": "Customer requested closure",
                "purge_at": (now - timedelta(days=1)).isoformat(),  # Past purge date
            },
            deleted_at=now - timedelta(days=31),
            created_at=now - timedelta(days=100),
            updated_at=now - timedelta(days=31),
        )

        tenant2 = Tenant(
            id="550e8400-e29b-41d4-a716-446655440002",
            slug="purge-tenant-2",
            name="Purge Test Tenant 2",
            status="deleted",
            config={
                "deletion_reason": "Inactive account cleanup",
                "purge_at": (now - timedelta(days=2)).isoformat(),  # Past purge date
            },
            deleted_at=now - timedelta(days=35),
            created_at=now - timedelta(days=200),
            updated_at=now - timedelta(days=35),
        )

        # Mock service responses
        mock_service.get_tenants_for_purge.return_value = [tenant1, tenant2]
        mock_service.purge_tenant.side_effect = [True, True]

        scheduler = TenantPurgeScheduler(mock_service)

        # Execute purge cycle
        result = await scheduler.run_purge_cycle()

        # Verify comprehensive result
        assert result["tenants_checked"] == 2
        assert result["tenants_purged"] == 2
        assert result["errors"] == 0
        assert result["duration_seconds"] > 0

        # Verify all expected service calls
        mock_service.get_tenants_for_purge.assert_called_once()
        mock_service.purge_tenant.assert_any_call("550e8400-e29b-41d4-a716-446655440001")
        mock_service.purge_tenant.assert_any_call("550e8400-e29b-41d4-a716-446655440002")

    @pytest.mark.asyncio
    async def test_scheduler_lifecycle(self):
        """Test complete scheduler start/stop lifecycle."""
        mock_service = MagicMock(spec=TenantService)
        scheduler = TenantPurgeScheduler(mock_service, check_interval=0.1)

        # Verify initial state
        assert scheduler._task is None
        assert not scheduler._shutdown_event.is_set()

        # Start scheduler
        with patch.object(scheduler, "_run_scheduler", new_callable=AsyncMock):
        with patch.object(scheduler, "_run_scheduler", new_callable=AsyncMock) as mock_run:
            await scheduler.start()

            # Verify task was created
            assert scheduler._task is not None

            # Stop scheduler
            await scheduler.stop()

            # Verify cleanup
            assert scheduler._task is None
            assert scheduler._shutdown_event.is_set()


# Helper to mock property that doesn't exist
class PropertyMock:
    def __init__(self, side_effect=None):
        self.side_effect = side_effect

    def __get__(self, obj, objtype):
        if self.side_effect:
            raise self.side_effect
        return None


class TestTenantPurgeSchedulerEnhancements:
    """Tests for enhanced purge scheduler functionality."""

    @pytest.mark.asyncio
    async def test_run_purge_cycle_with_metrics(self):
        """run_purge_cycle() records metrics when available."""
        mock_service = AsyncMock(spec=TenantService)
        mock_service.get_tenants_for_purge.return_value = []

        # Mock metrics
        mock_metrics = MagicMock()
        mock_counter = MagicMock()
        mock_histogram = MagicMock()
        mock_metrics.counter.return_value = mock_counter
        mock_metrics.histogram.return_value = mock_histogram

        scheduler = TenantPurgeScheduler(mock_service)

        # Inject metrics manually
        scheduler._metrics = mock_metrics
        scheduler._purge_cycles_counter = mock_counter
        scheduler._purge_duration_histogram = mock_histogram

        result = await scheduler.run_purge_cycle()

        # Verify metrics were recorded
        mock_counter.labels.assert_called_with(status="success")
        mock_counter.labels().inc.assert_called_once()
        mock_histogram.observe.assert_called_once()

        # Verify result
        assert result["tenants_checked"] == 0
        assert result["tenants_purged"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_run_purge_cycle_with_retry_logic(self):
        """run_purge_cycle() implements retry logic for failed purges."""
        mock_service = AsyncMock(spec=TenantService)

        # Mock tenant that will fail then succeed
        tenant = Tenant(
            id="tenant-id",
            slug="tenant-slug",
            name="Test Tenant",
            status="deleted",
            deleted_at=datetime.now(UTC) - timedelta(days=31),
        )

        mock_service.get_tenants_for_purge.return_value = [tenant]
        # First call fails, second succeeds
        mock_service.purge_tenant.side_effect = [Exception("Temporary error"), True]

        scheduler = TenantPurgeScheduler(mock_service)

        # Mock settings for faster test
        with patch("registry.tenant_purge_scheduler.settings") as mock_settings:
            mock_settings.tenant_purge_retry_count = 2
            mock_settings.tenant_purge_retry_delay = 0.1  # Fast retry

            result = await scheduler.run_purge_cycle()

        # Verify retry was attempted
        assert mock_service.purge_tenant.call_count == 2

        # Verify successful result after retry
        assert result["tenants_checked"] == 1
        assert result["tenants_purged"] == 1
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_run_purge_cycle_exhausted_retries(self):
        """run_purge_cycle() handles exhausted retries correctly."""
        mock_service = AsyncMock(spec=TenantService)

        # Mock tenant that always fails
        tenant = Tenant(id="tenant-id", slug="tenant-slug", name="Test Tenant", status="deleted")

        mock_service.get_tenants_for_purge.return_value = [tenant]
        mock_service.purge_tenant.side_effect = Exception("Persistent error")

        scheduler = TenantPurgeScheduler(mock_service)

        # Mock settings for faster test
        with patch("registry.tenant_purge_scheduler.settings") as mock_settings:
            mock_settings.tenant_purge_retry_count = 2
            mock_settings.tenant_purge_retry_delay = 0.1

            result = await scheduler.run_purge_cycle()

        # Verify all retries were attempted
        assert mock_service.purge_tenant.call_count == 2

        # Verify failed result
        assert result["tenants_checked"] == 1
        assert result["tenants_purged"] == 0
        assert result["errors"] == 1
        assert "Exception" in result["error_types"]

    @pytest.mark.asyncio
    async def test_run_purge_cycle_metrics_failure_doesnt_break_purge(self):
        """run_purge_cycle() continues even if metrics recording fails."""
        mock_service = AsyncMock(spec=TenantService)

        tenant = Tenant(id="tenant-id", slug="tenant-slug", name="Test Tenant", status="deleted")

        mock_service.get_tenants_for_purge.return_value = [tenant]
        mock_service.purge_tenant.return_value = True

        scheduler = TenantPurgeScheduler(mock_service)

        # Mock metrics that fail
        mock_metrics = MagicMock()
        mock_counter = MagicMock()
        mock_counter.inc.side_effect = Exception("Metrics error")
        mock_metrics.counter.return_value = mock_counter

        scheduler._metrics = mock_metrics
        scheduler._tenants_purged_counter = mock_counter

        # Should complete successfully despite metrics failure
        result = await scheduler.run_purge_cycle()

        assert result["tenants_checked"] == 1
        assert result["tenants_purged"] == 1
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_scheduler_initialization_with_metrics(self):
        """TenantPurgeScheduler initializes metrics correctly when available."""
        mock_service = MagicMock(spec=TenantService)

        # Mock metrics API
        mock_metrics_api = MagicMock()
        mock_counter = MagicMock()
        mock_histogram = MagicMock()
        mock_metrics_api.counter.return_value = mock_counter
        mock_metrics_api.histogram.return_value = mock_histogram

        with patch("registry.tenant_purge_scheduler.metrics_available", True):
            with patch(
                "registry.tenant_purge_scheduler.get_metrics_api", return_value=mock_metrics_api
            ):
                scheduler = TenantPurgeScheduler(mock_service)

                # Verify metrics were initialized
                assert scheduler._metrics is not None
                assert scheduler._purge_cycles_counter == mock_counter
                assert scheduler._purge_duration_histogram == mock_histogram

                # Verify correct metric creation calls
                expected_counter_calls = [
                    (("treasury_tenant_purge_cycles_total",), {"labels": ["status"]}),
                    (("treasury_tenants_purged_total",), {"labels": []}),
                    (("treasury_tenant_purge_errors_total",), {"labels": ["error_type"]}),
                ]

                actual_counter_calls = mock_metrics_api.counter.call_args_list
                assert len(actual_counter_calls) == 3

                mock_metrics_api.histogram.assert_called_once_with(
                    "treasury_tenant_purge_cycle_duration_seconds",
                    "Time taken for tenant purge cycles",
                    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
                )

    @pytest.mark.asyncio
    async def test_scheduler_initialization_without_metrics(self):
        """TenantPurgeScheduler works correctly when metrics are not available."""
        mock_service = MagicMock(spec=TenantService)

        with patch("registry.tenant_purge_scheduler.metrics_available", False):
            scheduler = TenantPurgeScheduler(mock_service)

            # Verify no metrics were initialized
            assert scheduler._metrics is None

    @pytest.mark.asyncio
    async def test_run_purge_cycle_partial_failure_metrics(self):
        """run_purge_cycle() records correct metrics for partial failures."""
        mock_service = AsyncMock(spec=TenantService)

        tenant1 = Tenant(id="tenant-1", slug="tenant-1", name="Tenant 1", status="deleted")
        tenant2 = Tenant(id="tenant-2", slug="tenant-2", name="Tenant 2", status="deleted")

        mock_service.get_tenants_for_purge.return_value = [tenant1, tenant2]
        # First succeeds, second fails
        mock_service.purge_tenant.side_effect = [True, Exception("Purge error")]

        scheduler = TenantPurgeScheduler(mock_service)

        # Mock metrics
        mock_metrics = MagicMock()
        mock_cycles_counter = MagicMock()
        mock_tenants_counter = MagicMock()
        mock_errors_counter = MagicMock()
        mock_histogram = MagicMock()

        scheduler._metrics = mock_metrics
        scheduler._purge_cycles_counter = mock_cycles_counter
        scheduler._tenants_purged_counter = mock_tenants_counter
        scheduler._purge_errors_counter = mock_errors_counter
        scheduler._purge_duration_histogram = mock_histogram

        # Mock settings for no retries
        with patch("registry.tenant_purge_scheduler.settings") as mock_settings:
            mock_settings.tenant_purge_retry_count = 1
            mock_settings.tenant_purge_retry_delay = 0

            result = await scheduler.run_purge_cycle()

        # Verify metrics recorded correctly
        mock_cycles_counter.labels.assert_called_with(status="partial_failure")
        mock_cycles_counter.labels().inc.assert_called_once()

        mock_tenants_counter.inc.assert_called_once()  # One successful purge

        mock_errors_counter.labels.assert_called_with(error_type="Exception")
        mock_errors_counter.labels().inc.assert_called_once_with(1)

        mock_histogram.observe.assert_called_once()

        # Verify result
        assert result["tenants_checked"] == 2
        assert result["tenants_purged"] == 1
        assert result["errors"] == 1
        assert result["error_types"]["Exception"] == 1


class TestTenantPurgeSchedulerIntegrationEnhanced:
    """Enhanced integration tests for TenantPurgeScheduler."""

    @pytest.mark.asyncio
    async def test_complete_purge_cycle_with_external_services(self):
        """Test complete purge cycle including event publishing and Keycloak cleanup."""
        mock_service = AsyncMock(spec=TenantService)

        # Create tenant with Keycloak org
        tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440001",
            slug="test-tenant",
            name="Test Tenant",
            status="deleted",
            config={
                "deletion_reason": "Test deletion",
                "purge_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            },
            keycloak_org_id="org-12345",
            deleted_at=datetime.now(UTC) - timedelta(days=31),
        )

        mock_service.get_tenants_for_purge.return_value = [tenant]
        mock_service.purge_tenant.return_value = True

        scheduler = TenantPurgeScheduler(mock_service)

        result = await scheduler.run_purge_cycle()

        # Verify successful purge
        assert result["tenants_checked"] == 1
        assert result["tenants_purged"] == 1
        assert result["errors"] == 0
        assert result["duration_seconds"] > 0

        # Verify service was called
        mock_service.get_tenants_for_purge.assert_called_once()
        mock_service.purge_tenant.assert_called_once_with("550e8400-e29b-41d4-a716-446655440001")
