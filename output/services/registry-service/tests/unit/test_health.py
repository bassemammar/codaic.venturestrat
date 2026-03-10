"""Tests for HealthManager - TDD approach.

Tests for health check management and status tracking.
"""

import pytest
from registry.health import (
    HealthCheckResult,
    HealthManager,
    HealthTransition,
)
from registry.models import HealthCheckConfig, HealthStatus


@pytest.fixture
def health_manager():
    """Create HealthManager instance."""
    return HealthManager()


class TestHealthCheckResult:
    """Tests for HealthCheckResult model."""

    def test_create_passing_result(self):
        """Create a passing health check result."""
        result = HealthCheckResult(
            instance_id="test-123",
            service_name="test-service",
            status=HealthStatus.HEALTHY,
            check_name="http-check",
            output="HTTP GET /health: 200 OK",
        )

        assert result.status == HealthStatus.HEALTHY
        assert result.is_healthy is True
        assert result.timestamp is not None

    def test_create_failing_result(self):
        """Create a failing health check result."""
        result = HealthCheckResult(
            instance_id="test-123",
            service_name="test-service",
            status=HealthStatus.CRITICAL,
            check_name="http-check",
            output="Connection refused",
        )

        assert result.status == HealthStatus.CRITICAL
        assert result.is_healthy is False


class TestHealthTransition:
    """Tests for HealthTransition model."""

    def test_create_transition(self):
        """Create a health status transition."""
        transition = HealthTransition(
            instance_id="test-123",
            service_name="test-service",
            previous_status=HealthStatus.HEALTHY,
            new_status=HealthStatus.CRITICAL,
            check_name="http-check",
            check_output="Connection timeout",
        )

        assert transition.previous_status == HealthStatus.HEALTHY
        assert transition.new_status == HealthStatus.CRITICAL
        assert transition.is_degradation is True

    def test_recovery_transition(self):
        """Transition from critical to healthy is recovery."""
        transition = HealthTransition(
            instance_id="test-123",
            service_name="test-service",
            previous_status=HealthStatus.CRITICAL,
            new_status=HealthStatus.HEALTHY,
            check_name="http-check",
            check_output="HTTP 200 OK",
        )

        assert transition.is_degradation is False
        assert transition.is_recovery is True


class TestHealthManagerTracking:
    """Tests for health status tracking."""

    def test_record_health_check(self, health_manager):
        """Record a health check result."""
        result = HealthCheckResult(
            instance_id="test-123",
            service_name="test-service",
            status=HealthStatus.HEALTHY,
            check_name="http-check",
        )

        health_manager.record_check(result)

        current = health_manager.get_status("test-123")
        assert current == HealthStatus.HEALTHY

    def test_get_status_unknown_instance(self, health_manager):
        """Get status of unknown instance returns None."""
        status = health_manager.get_status("nonexistent")
        assert status is None

    def test_status_transition_detected(self, health_manager):
        """Detect status transitions."""
        health_manager.record_check(
            HealthCheckResult(
                instance_id="test-123",
                service_name="test-service",
                status=HealthStatus.HEALTHY,
                check_name="http-check",
            )
        )

        transition = health_manager.record_check(
            HealthCheckResult(
                instance_id="test-123",
                service_name="test-service",
                status=HealthStatus.CRITICAL,
                check_name="http-check",
                output="Connection refused",
            )
        )

        assert transition is not None
        assert transition.previous_status == HealthStatus.HEALTHY
        assert transition.new_status == HealthStatus.CRITICAL

    def test_no_transition_same_status(self, health_manager):
        """No transition when status unchanged."""
        health_manager.record_check(
            HealthCheckResult(
                instance_id="test-123",
                service_name="test-service",
                status=HealthStatus.HEALTHY,
                check_name="http-check",
            )
        )

        transition = health_manager.record_check(
            HealthCheckResult(
                instance_id="test-123",
                service_name="test-service",
                status=HealthStatus.HEALTHY,
                check_name="http-check",
            )
        )

        assert transition is None

    def test_clear_instance(self, health_manager):
        """Clear instance removes tracking."""
        health_manager.record_check(
            HealthCheckResult(
                instance_id="test-123",
                service_name="test-service",
                status=HealthStatus.HEALTHY,
                check_name="http-check",
            )
        )

        health_manager.clear_instance("test-123")

        assert health_manager.get_status("test-123") is None


class TestHealthManagerQueries:
    """Tests for health status queries."""

    def test_get_all_statuses(self, health_manager):
        """Get status of all tracked instances."""
        health_manager.record_check(
            HealthCheckResult(
                instance_id="svc-1",
                service_name="service-a",
                status=HealthStatus.HEALTHY,
                check_name="check",
            )
        )
        health_manager.record_check(
            HealthCheckResult(
                instance_id="svc-2",
                service_name="service-b",
                status=HealthStatus.CRITICAL,
                check_name="check",
            )
        )

        statuses = health_manager.get_all_statuses()

        assert statuses["svc-1"] == HealthStatus.HEALTHY
        assert statuses["svc-2"] == HealthStatus.CRITICAL

    def test_get_healthy_instances(self, health_manager):
        """Get only healthy instances."""
        health_manager.record_check(
            HealthCheckResult(
                instance_id="healthy-1",
                service_name="test",
                status=HealthStatus.HEALTHY,
                check_name="check",
            )
        )
        health_manager.record_check(
            HealthCheckResult(
                instance_id="critical-1",
                service_name="test",
                status=HealthStatus.CRITICAL,
                check_name="check",
            )
        )

        healthy = health_manager.get_healthy_instances()

        assert "healthy-1" in healthy
        assert "critical-1" not in healthy

    def test_get_unhealthy_instances(self, health_manager):
        """Get unhealthy instances (critical or warning)."""
        health_manager.record_check(
            HealthCheckResult(
                instance_id="healthy-1",
                service_name="test",
                status=HealthStatus.HEALTHY,
                check_name="check",
            )
        )
        health_manager.record_check(
            HealthCheckResult(
                instance_id="warning-1",
                service_name="test",
                status=HealthStatus.WARNING,
                check_name="check",
            )
        )
        health_manager.record_check(
            HealthCheckResult(
                instance_id="critical-1",
                service_name="test",
                status=HealthStatus.CRITICAL,
                check_name="check",
            )
        )

        unhealthy = health_manager.get_unhealthy_instances()

        assert "healthy-1" not in unhealthy
        assert "warning-1" in unhealthy
        assert "critical-1" in unhealthy


class TestHealthCheckConfiguration:
    """Tests for health check configuration building."""

    def test_build_http_check_config(self, health_manager):
        """Build HTTP health check configuration for Consul."""
        config = HealthCheckConfig(
            http_endpoint="/health/ready",
            interval_seconds=15,
            timeout_seconds=5,
            deregister_after_seconds=120,
        )

        consul_check = health_manager.build_consul_check(
            config,
            address="10.0.1.50",
            port=8080,
        )

        assert "http://10.0.1.50:8080/health/ready" in consul_check.get("http", "")
        assert consul_check["interval"] == "15s"
        assert consul_check["timeout"] == "5s"

    def test_build_grpc_check_config(self, health_manager):
        """Build gRPC health check configuration."""
        config = HealthCheckConfig(
            grpc_service="grpc.health.v1.Health",
            interval_seconds=10,
        )

        consul_check = health_manager.build_consul_check(
            config,
            address="10.0.1.50",
            port=50051,
        )

        assert "grpc" in consul_check
        assert "10.0.1.50:50051" in consul_check["grpc"]

    def test_build_tcp_check_config(self, health_manager):
        """Build TCP health check configuration."""
        config = HealthCheckConfig(
            tcp_address="10.0.1.50:5432",
            interval_seconds=30,
        )

        consul_check = health_manager.build_consul_check(
            config,
            address="10.0.1.50",
            port=5432,
        )

        assert "tcp" in consul_check
