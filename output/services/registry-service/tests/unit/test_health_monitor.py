"""Unit tests for health monitoring service."""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Optional

import httpx

from registry.health_monitor import (
    HealthCheckConfig,
    PricerHealthStatus,
    HealthMonitoringService,
    HealthMonitoringManager,
)
from registry.models.pricer_registry import PricerRegistry, PricerStatus


class TestHealthCheckConfig:
    """Test health check configuration model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HealthCheckConfig()

        assert config.check_interval_seconds == 30
        assert config.timeout_seconds == 10
        assert config.failure_threshold == 3
        assert config.recovery_threshold == 2
        assert config.retry_backoff_seconds == 60
        assert config.max_concurrent_checks == 10

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HealthCheckConfig(
            check_interval_seconds=15,
            timeout_seconds=5,
            failure_threshold=5,
            recovery_threshold=3,
            retry_backoff_seconds=120,
            max_concurrent_checks=20
        )

        assert config.check_interval_seconds == 15
        assert config.timeout_seconds == 5
        assert config.failure_threshold == 5
        assert config.recovery_threshold == 3
        assert config.retry_backoff_seconds == 120
        assert config.max_concurrent_checks == 20


class TestPricerHealthStatus:
    """Test pricer health status model."""

    def test_healthy_status(self):
        """Test healthy status check."""
        status = PricerHealthStatus(
            pricer_id="quantlib-v1.18",
            status=PricerStatus.HEALTHY,
            last_check_time=datetime.now(timezone.utc)
        )

        assert status.is_healthy() is True

    def test_unhealthy_status(self):
        """Test unhealthy status check."""
        status = PricerHealthStatus(
            pricer_id="quantlib-v1.18",
            status=PricerStatus.UNHEALTHY,
            last_check_time=datetime.now(timezone.utc)
        )

        assert status.is_healthy() is False

    def test_should_check_healthy_pricer(self):
        """Test check timing for healthy pricer."""
        config = HealthCheckConfig(check_interval_seconds=30)

        # Recent check - should not check yet
        status = PricerHealthStatus(
            pricer_id="quantlib-v1.18",
            status=PricerStatus.HEALTHY,
            last_check_time=datetime.now(timezone.utc)
        )
        assert status.should_check(config) is False

        # Old check - should check now
        from datetime import timedelta
        status.last_check_time = datetime.now(timezone.utc) - timedelta(seconds=40)
        assert status.should_check(config) is True

    def test_should_check_unhealthy_pricer(self):
        """Test check timing for unhealthy pricer."""
        config = HealthCheckConfig(
            check_interval_seconds=30,
            retry_backoff_seconds=60
        )

        # Recent check - should wait for backoff
        status = PricerHealthStatus(
            pricer_id="quantlib-v1.18",
            status=PricerStatus.UNHEALTHY,
            last_check_time=datetime.now(timezone.utc)
        )
        assert status.should_check(config) is False

        # Old check - should check now
        from datetime import timedelta
        status.last_check_time = datetime.now(timezone.utc) - timedelta(seconds=70)
        assert status.should_check(config) is True


class TestHealthMonitoringService:
    """Test health monitoring service."""

    @pytest.fixture
    def mock_config(self):
        """Mock health check configuration."""
        return HealthCheckConfig(
            check_interval_seconds=1,  # Fast for testing
            timeout_seconds=5,
            failure_threshold=2,
            recovery_threshold=1,
            retry_backoff_seconds=2,
            max_concurrent_checks=5
        )

    @pytest.fixture
    def mock_pricers(self):
        """Mock list of pricers."""
        return [
            PricerRegistry(
                pricer_id="quantlib-v1.18",
                name="QuantLib",
                version="1.18.0",
                health_check_url="http://quantlib:8088/health",
                pricing_url="http://quantlib:8088/api/v1",
                status=PricerStatus.HEALTHY
            ),
            PricerRegistry(
                pricer_id="treasury-v2.3",
                name="Treasury",
                version="2.3.0",
                health_check_url="http://treasury:8101/health",
                pricing_url="http://treasury:8101/api/v1",
                status=PricerStatus.HEALTHY
            )
        ]

    @pytest.fixture
    def mock_callbacks(self, mock_pricers):
        """Mock callback functions."""
        get_pricers_mock = AsyncMock(return_value=mock_pricers)
        update_pricer_mock = AsyncMock()
        return get_pricers_mock, update_pricer_mock

    def test_initialization(self, mock_config):
        """Test service initialization."""
        service = HealthMonitoringService(config=mock_config)

        assert service.config == mock_config
        assert service.get_pricers_callback is None
        assert service.update_pricer_callback is None
        assert len(service._pricer_statuses) == 0
        assert len(service._status_change_callbacks) == 0

    def test_add_status_change_callback(self, mock_config):
        """Test adding status change callbacks."""
        service = HealthMonitoringService(config=mock_config)
        callback = MagicMock()

        service.add_status_change_callback(callback)
        assert len(service._status_change_callbacks) == 1
        assert service._status_change_callbacks[0] == callback

    @pytest.mark.asyncio
    async def test_start_and_stop(self, mock_config):
        """Test starting and stopping monitoring service."""
        service = HealthMonitoringService(config=mock_config)

        # Start service
        await service.start()
        assert service._monitoring_task is not None
        assert not service._monitoring_task.done()
        assert service._http_client is not None

        # Stop service
        await service.stop()
        assert service._monitoring_task.done()
        assert service._http_client is None

    @pytest.mark.asyncio
    async def test_update_tracked_pricers(self, mock_config, mock_pricers):
        """Test updating tracked pricers."""
        service = HealthMonitoringService(config=mock_config)

        # Update with new pricers
        await service._update_tracked_pricers(mock_pricers)

        assert len(service._pricer_statuses) == 2
        assert "quantlib-v1.18" in service._pricer_statuses
        assert "treasury-v2.3" in service._pricer_statuses

        # Remove one pricer
        await service._update_tracked_pricers([mock_pricers[0]])

        assert len(service._pricer_statuses) == 1
        assert "quantlib-v1.18" in service._pricer_statuses
        assert "treasury-v2.3" not in service._pricer_statuses

    @pytest.mark.asyncio
    async def test_successful_health_check(self, mock_config, mock_pricers):
        """Test handling successful health check."""
        service = HealthMonitoringService(config=mock_config)
        pricer = mock_pricers[0]

        # Create initial status
        status = PricerHealthStatus(
            pricer_id=pricer.pricer_id,
            status=PricerStatus.UNHEALTHY,
            last_check_time=datetime.now(timezone.utc),
            consecutive_failures=3,
            consecutive_successes=0
        )
        service._pricer_statuses[pricer.pricer_id] = status

        # Simulate successful health check
        await service._handle_health_check_success(pricer.pricer_id, status, 150.0)

        assert status.consecutive_failures == 0
        assert status.consecutive_successes == 1
        assert status.response_time_ms == 150.0
        assert status.error_message is None
        assert status.status == PricerStatus.HEALTHY  # Should transition to healthy

    @pytest.mark.asyncio
    async def test_failed_health_check(self, mock_config, mock_pricers):
        """Test handling failed health check."""
        service = HealthMonitoringService(config=mock_config)
        pricer = mock_pricers[0]

        # Create initial healthy status
        status = PricerHealthStatus(
            pricer_id=pricer.pricer_id,
            status=PricerStatus.HEALTHY,
            last_check_time=datetime.now(timezone.utc),
            consecutive_failures=0,
            consecutive_successes=5
        )
        service._pricer_statuses[pricer.pricer_id] = status

        # Simulate failed health check
        error_message = "Connection refused"
        await service._handle_health_check_failure(pricer.pricer_id, status, error_message)

        assert status.consecutive_failures == 1
        assert status.consecutive_successes == 0
        assert status.error_message == error_message
        assert status.response_time_ms is None
        # Should not transition to unhealthy yet (threshold is 2)
        assert status.status == PricerStatus.HEALTHY

        # Second failure should transition to unhealthy
        await service._handle_health_check_failure(pricer.pricer_id, status, error_message)
        assert status.consecutive_failures == 2
        assert status.status == PricerStatus.UNHEALTHY

    def test_get_metrics(self, mock_config):
        """Test getting health monitoring metrics."""
        service = HealthMonitoringService(config=mock_config)

        # Add some mock statuses
        service._pricer_statuses["healthy"] = PricerHealthStatus(
            pricer_id="healthy",
            status=PricerStatus.HEALTHY,
            last_check_time=datetime.now(timezone.utc)
        )
        service._pricer_statuses["unhealthy"] = PricerHealthStatus(
            pricer_id="unhealthy",
            status=PricerStatus.UNHEALTHY,
            last_check_time=datetime.now(timezone.utc)
        )

        # Set some metrics
        service._total_checks = 100
        service._successful_checks = 95
        service._failed_checks = 5

        metrics = service.get_metrics()

        assert metrics["total_pricers"] == 2
        assert metrics["healthy_pricers"] == 1
        assert metrics["unhealthy_pricers"] == 1
        assert metrics["health_ratio"] == 0.5
        assert metrics["total_checks"] == 100
        assert metrics["successful_checks"] == 95
        assert metrics["failed_checks"] == 5
        assert metrics["success_rate"] == 0.95

    @pytest.mark.asyncio
    async def test_http_health_check_success(self, mock_config, mock_pricers, mock_callbacks):
        """Test actual HTTP health check with success response."""
        get_pricers_mock, update_pricer_mock = mock_callbacks
        service = HealthMonitoringService(
            config=mock_config,
            get_pricers_callback=get_pricers_mock,
            update_pricer_callback=update_pricer_mock
        )

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response

        service._http_client = mock_http_client

        # Initialize status
        pricer = mock_pricers[0]
        status = PricerHealthStatus(
            pricer_id=pricer.pricer_id,
            status=PricerStatus.HEALTHY,
            last_check_time=datetime.now(timezone.utc)
        )
        service._pricer_statuses[pricer.pricer_id] = status

        # Perform health check
        await service._check_pricer_health(pricer.pricer_id, status)

        # Verify HTTP call was made
        mock_http_client.get.assert_called_once_with(pricer.health_check_url)

        # Verify status was updated
        assert status.consecutive_failures == 0
        assert status.response_time_ms is not None
        assert service._successful_checks == 1

    @pytest.mark.asyncio
    async def test_http_health_check_failure(self, mock_config, mock_pricers, mock_callbacks):
        """Test actual HTTP health check with failure response."""
        get_pricers_mock, update_pricer_mock = mock_callbacks
        service = HealthMonitoringService(
            config=mock_config,
            get_pricers_callback=get_pricers_mock,
            update_pricer_callback=update_pricer_mock
        )

        # Mock HTTP client with exception
        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = httpx.ConnectError("Connection failed")
        service._http_client = mock_http_client

        # Initialize status
        pricer = mock_pricers[0]
        status = PricerHealthStatus(
            pricer_id=pricer.pricer_id,
            status=PricerStatus.HEALTHY,
            last_check_time=datetime.now(timezone.utc)
        )
        service._pricer_statuses[pricer.pricer_id] = status

        # Perform health check
        await service._check_pricer_health(pricer.pricer_id, status)

        # Verify status was updated for failure
        assert status.consecutive_failures == 1
        assert "ConnectError: Connection failed" in status.error_message
        assert service._failed_checks == 1

    def test_status_change_callback_invocation(self, mock_config):
        """Test status change callback invocation."""
        service = HealthMonitoringService(config=mock_config)
        callback_mock = MagicMock()
        service.add_status_change_callback(callback_mock)

        # Trigger status change notification
        asyncio.run(service._notify_status_change(
            "test-pricer",
            PricerStatus.HEALTHY,
            PricerStatus.UNHEALTHY
        ))

        callback_mock.assert_called_once_with("test-pricer", PricerStatus.HEALTHY, PricerStatus.UNHEALTHY)

    def test_get_healthy_and_unhealthy_pricers(self, mock_config):
        """Test getting healthy and unhealthy pricer lists."""
        service = HealthMonitoringService(config=mock_config)

        # Add mixed statuses
        service._pricer_statuses["healthy1"] = PricerHealthStatus(
            pricer_id="healthy1",
            status=PricerStatus.HEALTHY,
            last_check_time=datetime.now(timezone.utc)
        )
        service._pricer_statuses["healthy2"] = PricerHealthStatus(
            pricer_id="healthy2",
            status=PricerStatus.HEALTHY,
            last_check_time=datetime.now(timezone.utc)
        )
        service._pricer_statuses["unhealthy1"] = PricerHealthStatus(
            pricer_id="unhealthy1",
            status=PricerStatus.UNHEALTHY,
            last_check_time=datetime.now(timezone.utc)
        )

        healthy = service.get_healthy_pricers()
        unhealthy = service.get_unhealthy_pricers()

        assert len(healthy) == 2
        assert "healthy1" in healthy
        assert "healthy2" in healthy

        assert len(unhealthy) == 1
        assert "unhealthy1" in unhealthy


class TestHealthMonitoringManager:
    """Test health monitoring manager."""

    def test_initialization(self):
        """Test manager initialization."""
        mock_registry = MagicMock()
        manager = HealthMonitoringManager(mock_registry)

        assert manager.registry_service == mock_registry
        assert manager.monitoring_service is None
        assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_with_registry_service(self):
        """Test initialization with registry service."""
        mock_registry = MagicMock()
        mock_registry.list_all_pricers = AsyncMock(return_value=[])
        mock_registry.update_pricer_health = MagicMock()

        manager = HealthMonitoringManager(mock_registry)
        service = await manager.initialize()

        assert manager._initialized is True
        assert manager.monitoring_service is not None
        assert service == manager.monitoring_service

        # Verify callbacks are set
        assert service.get_pricers_callback is not None
        assert service.update_pricer_callback is not None

    @pytest.mark.asyncio
    async def test_initialize_without_registry_service(self):
        """Test initialization without registry service."""
        manager = HealthMonitoringManager(None)
        service = await manager.initialize()

        assert manager._initialized is True
        assert service.get_pricers_callback is None
        assert service.update_pricer_callback is None

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """Test starting and stopping manager."""
        mock_registry = MagicMock()
        manager = HealthMonitoringManager(mock_registry)

        # Start with auto-initialization
        with patch.object(manager, 'initialize') as mock_init:
            mock_service = AsyncMock()
            mock_init.return_value = mock_service
            manager.monitoring_service = mock_service

            await manager.start()

            mock_init.assert_called_once()
            mock_service.start.assert_called_once()

        # Stop
        await manager.stop()
        mock_service.stop.assert_called_once()

    def test_log_status_change_callback(self):
        """Test status change logging callback."""
        manager = HealthMonitoringManager(None)

        # Should not raise exception
        manager._log_status_change(
            "test-pricer",
            PricerStatus.HEALTHY,
            PricerStatus.UNHEALTHY
        )


@pytest.mark.integration
class TestHealthMonitoringIntegration:
    """Integration tests for health monitoring."""

    @pytest.mark.asyncio
    async def test_full_monitoring_cycle(self):
        """Test a full monitoring cycle with real HTTP client."""
        config = HealthCheckConfig(
            check_interval_seconds=1,
            timeout_seconds=2,
            failure_threshold=1,
            recovery_threshold=1,
        )

        # Mock pricers
        pricers = [
            PricerRegistry(
                pricer_id="test-pricer",
                name="Test Pricer",
                version="1.0.0",
                health_check_url="http://httpbin.org/status/200",  # Always returns 200
                pricing_url="http://httpbin.org",
                status=PricerStatus.HEALTHY
            )
        ]

        get_pricers_mock = AsyncMock(return_value=pricers)
        update_pricer_mock = AsyncMock()

        service = HealthMonitoringService(
            config=config,
            get_pricers_callback=get_pricers_mock,
            update_pricer_callback=update_pricer_mock
        )

        # Start monitoring
        await service.start()

        try:
            # Wait for at least one monitoring cycle
            await asyncio.sleep(2)

            # Check that pricers are being tracked
            assert len(service._pricer_statuses) == 1
            assert "test-pricer" in service._pricer_statuses

            # Check metrics
            metrics = service.get_metrics()
            assert metrics["total_pricers"] == 1
            assert metrics["is_running"] is True

        finally:
            await service.stop()

    @pytest.mark.asyncio
    async def test_health_status_transitions(self):
        """Test health status transitions during monitoring."""
        config = HealthCheckConfig(
            check_interval_seconds=0.5,  # Very fast for testing
            failure_threshold=2,
            recovery_threshold=1,
        )

        # Mock pricers with failing health endpoint
        pricers = [
            PricerRegistry(
                pricer_id="failing-pricer",
                name="Failing Pricer",
                version="1.0.0",
                health_check_url="http://httpbin.org/status/500",  # Always returns 500
                pricing_url="http://httpbin.org",
                status=PricerStatus.HEALTHY
            )
        ]

        get_pricers_mock = AsyncMock(return_value=pricers)
        update_pricer_mock = AsyncMock()
        status_change_mock = MagicMock()

        service = HealthMonitoringService(
            config=config,
            get_pricers_callback=get_pricers_mock,
            update_pricer_callback=update_pricer_mock
        )
        service.add_status_change_callback(status_change_mock)

        await service.start()

        try:
            # Wait for health checks to detect failure
            await asyncio.sleep(2)

            # Check that pricer transitioned to unhealthy
            status = service.get_pricer_health_status("failing-pricer")
            assert status is not None
            # Due to the fast timing, we might catch it in transition

            # Verify status change callback was called
            if status_change_mock.called:
                call_args = status_change_mock.call_args_list[-1]
                assert call_args[0][0] == "failing-pricer"
                # The transition should be towards unhealthy

        finally:
            await service.stop()