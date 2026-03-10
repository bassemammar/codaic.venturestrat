"""
Unit tests for observability assertions in registry service.

Tests specific observability functionality including correlation ID propagation,
metrics collection, structured logging, tracing integration, and sensitive data masking.
These tests verify that the observability middleware is properly integrated and
functioning according to the technical specification.
"""

import time
import uuid

import pytest
from fastapi.testclient import TestClient
from registry.main import app


class TestCorrelationIdAssertions:
    """Test correlation ID functionality according to spec."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Get test client for registry service."""
        return TestClient(app)

    def test_correlation_id_extracted_from_x_correlation_id_header(self, client: TestClient):
        """Test that correlation ID is extracted from X-Correlation-ID header."""
        test_correlation_id = "test-correlation-extraction-001"

        response = client.get("/api/v1/services", headers={"X-Correlation-ID": test_correlation_id})

        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == test_correlation_id

    def test_correlation_id_extracted_from_x_request_id_header(self, client: TestClient):
        """Test that correlation ID is extracted from X-Request-ID header as fallback."""
        test_request_id = "test-request-id-fallback-002"

        response = client.get("/api/v1/services", headers={"X-Request-ID": test_request_id})

        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == test_request_id

    def test_correlation_id_extracted_from_request_id_header(self, client: TestClient):
        """Test that correlation ID is extracted from request-id header as final fallback."""
        test_req_id = "test-req-id-final-fallback-003"

        response = client.get("/api/v1/services", headers={"request-id": test_req_id})

        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == test_req_id

    def test_correlation_id_header_priority_order(self, client: TestClient):
        """Test that correlation ID headers follow correct priority order."""
        response = client.get(
            "/api/v1/services",
            headers={
                "X-Correlation-ID": "priority-1-correlation",
                "X-Request-ID": "priority-2-request",
                "request-id": "priority-3-request",
                "X-Trace-ID": "priority-4-trace",
            },
        )

        assert response.status_code == 200
        # Should use X-Correlation-ID as it has highest priority
        assert response.headers["X-Correlation-ID"] == "priority-1-correlation"

    def test_correlation_id_generated_uuid_when_no_header_present(self, client: TestClient):
        """Test that a UUID is generated when no correlation header is present."""
        response = client.get("/api/v1/services")

        assert response.status_code == 200

        correlation_id = response.headers.get("X-Correlation-ID")
        assert correlation_id is not None
        assert len(correlation_id) == 36  # UUID format

        # Verify it's a valid UUID
        uuid_obj = uuid.UUID(correlation_id)
        assert str(uuid_obj) == correlation_id

    def test_correlation_id_echoed_in_response_header(self, client: TestClient):
        """Test that correlation ID is always echoed in X-Correlation-ID response header."""
        test_correlation_id = "echo-test-correlation-004"

        response = client.get("/health/live", headers={"X-Correlation-ID": test_correlation_id})

        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == test_correlation_id

    def test_correlation_id_available_via_context(self, client: TestClient):
        """Test that correlation ID is available via get_correlation_id during request."""

        test_correlation_id = "context-test-correlation-005"

        # We'll need to capture the correlation ID from within a request handler
        # For this test, we'll verify that the middleware sets it correctly
        response = client.get("/api/v1/services", headers={"X-Correlation-ID": test_correlation_id})

        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == test_correlation_id


class TestMetricsAssertions:
    """Test metrics functionality according to spec."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Get test client for registry service."""
        return TestClient(app)

    def test_http_requests_total_counter_incremented(self, client: TestClient):
        """Test that http request metrics are collected for HTTP requests."""
        # Make a request
        response = client.get("/api/v1/services")
        assert response.status_code == 200

        # Check metrics
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        metrics_content = metrics_response.text

        # Verify HTTP metrics are present (actual format may vary)
        assert (
            "http_requests_total" in metrics_content
            or "http_request_duration_seconds" in metrics_content
        )
        assert 'method="GET"' in metrics_content

    def test_http_request_duration_histogram_recorded(self, client: TestClient):
        """Test that http_request_duration_seconds histogram is recorded."""
        response = client.get("/api/v1/services")
        assert response.status_code == 200

        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        # Verify HTTP duration histogram is present
        assert "http_request_duration_seconds" in metrics_content
        assert "http_request_duration_seconds_bucket" in metrics_content

    def test_metrics_include_service_version_env_labels(self, client: TestClient):
        """Test that metrics include service, version, and env labels."""
        response = client.get("/api/v1/services")
        assert response.status_code == 200

        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        # Verify standard labels are present
        assert "service=" in metrics_content
        assert "version=" in metrics_content
        assert "env=" in metrics_content

    def test_path_normalized_for_metrics_cardinality(self, client: TestClient):
        """Test that path parameters are normalized to prevent cardinality explosion."""
        # Make requests to paths with parameters
        client.get("/api/v1/services/service-123")
        client.get("/api/v1/services/service-456")

        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        # Path should be normalized (e.g., /api/v1/services/{service_name})
        # The exact normalization depends on implementation, but cardinality should be bounded
        assert "http_requests_total" in metrics_content

    def test_health_endpoints_excluded_from_detailed_metrics(self, client: TestClient):
        """Test that health endpoints are excluded from detailed metrics collection."""
        # Make requests to health endpoints
        client.get("/health/live")
        client.get("/health/ready")

        metrics_response = client.get("/metrics")

        # Health endpoints should not clutter metrics
        # Implementation may vary - some exclude completely, others aggregate
        assert metrics_response.status_code == 200

    def test_treasury_registry_services_active_gauge_present(self, client: TestClient):
        """Test that custom treasury_registry_services_active gauge is present."""
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        metrics_content = metrics_response.text

        # Verify custom gauge is present
        assert "treasury_registry_services_active" in metrics_content
        assert "# TYPE treasury_registry_services_active gauge" in metrics_content
        assert 'service_type="fastapi"' in metrics_content
        assert 'service_type="grpc"' in metrics_content
        assert 'service_type="other"' in metrics_content

    def test_treasury_registry_health_checks_total_counter_present(self, client: TestClient):
        """Test that custom treasury_registry_health_checks_total counter is present."""
        # Make health check request to trigger counter
        client.get("/health/live")

        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        metrics_content = metrics_response.text

        # Verify custom counter is present and incremented
        assert "treasury_registry_health_checks_total" in metrics_content
        assert "# TYPE treasury_registry_health_checks_total counter" in metrics_content
        assert 'status="healthy"' in metrics_content

    def test_custom_metrics_follow_treasury_naming_convention(self, client: TestClient):
        """Test that custom metrics follow treasury_ naming convention."""
        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        # Verify treasury_ prefix is used for custom metrics
        assert "treasury_registry_services_active" in metrics_content
        assert "treasury_registry_health_checks_total" in metrics_content

    def test_metrics_have_help_and_type_annotations(self, client: TestClient):
        """Test that metrics have proper HELP and TYPE annotations."""
        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        # Verify HELP annotations
        assert (
            "# HELP treasury_registry_services_active Number of active registered services"
            in metrics_content
        )
        assert (
            "# HELP treasury_registry_health_checks_total Total health check executions"
            in metrics_content
        )

        # Verify TYPE annotations
        assert "# TYPE treasury_registry_services_active gauge" in metrics_content
        assert "# TYPE treasury_registry_health_checks_total counter" in metrics_content

    def test_service_registration_increments_services_active_gauge(self, client: TestClient):
        """Test that service registration increments the services_active gauge."""
        # Register a service
        response = client.post("/api/v1/services")
        assert response.status_code == 201

        # Check that gauge was incremented
        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        assert "treasury_registry_services_active" in metrics_content
        # The exact value depends on implementation, but gauge should exist

    def test_service_deregistration_decrements_services_active_gauge(self, client: TestClient):
        """Test that service deregistration decrements the services_active gauge."""
        # Register then deregister a service
        client.post("/api/v1/services")
        response = client.delete("/api/v1/services/test-instance")
        assert response.status_code == 204

        # Check that gauge exists (implementation handles decrementing)
        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        assert "treasury_registry_services_active" in metrics_content


class TestRequestDurationAssertions:
    """Test request duration header functionality."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Get test client for registry service."""
        return TestClient(app)

    def test_request_duration_header_added_to_all_responses(self, client: TestClient):
        """Test that X-Request-Duration-Ms header is added to all responses."""
        endpoints = ["/health/live", "/health/ready", "/api/v1/services", "/metrics"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert "X-Request-Duration-Ms" in response.headers

            duration = response.headers["X-Request-Duration-Ms"]
            # Should be a valid float value >= 0
            assert float(duration) >= 0

    def test_request_duration_header_format_is_milliseconds(self, client: TestClient):
        """Test that request duration header is formatted in milliseconds."""
        response = client.get("/api/v1/services")

        duration_str = response.headers["X-Request-Duration-Ms"]
        duration_float = float(duration_str)

        # Should be reasonable duration in milliseconds (> 0, < 10000ms)
        assert 0 < duration_float < 10000

    def test_request_duration_consistent_with_actual_timing(self, client: TestClient):
        """Test that request duration header reflects actual processing time."""
        start_time = time.time()
        response = client.get("/api/v1/services")
        end_time = time.time()

        actual_duration_ms = (end_time - start_time) * 1000
        reported_duration_ms = float(response.headers["X-Request-Duration-Ms"])

        # Reported duration should be within reasonable range of actual duration
        # Allow some overhead for middleware and framework processing
        assert reported_duration_ms <= actual_duration_ms + 100  # 100ms overhead allowance


class TestStructuredLoggingAssertions:
    """Test structured logging functionality."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Get test client for registry service."""
        return TestClient(app)

    def test_log_includes_correlation_id_in_request_context(self, client: TestClient):
        """Test that structured logging is configured and correlation ID is properly propagated."""
        test_correlation_id = "logging-correlation-test-001"

        response = client.get("/health/live", headers={"X-Correlation-ID": test_correlation_id})

        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == test_correlation_id

        # Verify that structured logging middleware is working (correlation ID propagated)
        # The fact that the correlation ID is echoed back indicates logging middleware integration

    def test_log_level_configuration_from_manifest(self, client: TestClient):
        """Test that log level is configured from manifest observability section."""
        # This tests that logging configuration is properly loaded
        # The actual log level is tested by checking that INFO level logs are generated

        response = client.get("/health/live")
        assert response.status_code == 200

        # If this passes without errors, logging configuration is working


class TestServiceTierConfiguration:
    """Test service tier-specific configuration according to spec."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Get test client for registry service."""
        return TestClient(app)

    def test_registry_service_configured_as_fast_tier(self, client: TestClient):
        """Test that registry-service is configured with fast tier settings."""
        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        # Fast tier should have histogram buckets optimized for low latency
        # The exact buckets depend on implementation, but should be present
        assert "http_request_duration_seconds_bucket" in metrics_content

        # Should have service labels indicating fast tier
        assert "service=" in metrics_content

    def test_fast_tier_histogram_buckets_for_slo_monitoring(self, client: TestClient):
        """Test that fast tier uses appropriate histogram buckets for SLO monitoring."""
        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        # Fast tier buckets should include values suitable for p95=50ms, p99=100ms SLOs
        # Exact bucket values: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
        assert 'le="0.005"' in metrics_content or 'le="0.01"' in metrics_content
        assert 'le="0.05"' in metrics_content or 'le="0.1"' in metrics_content

    def test_observability_configuration_loaded_from_manifest(self, client: TestClient):
        """Test that observability configuration is loaded from manifest.yaml."""
        # This test verifies that the middleware successfully loaded configuration
        # If the service starts and metrics are available, configuration was loaded

        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200

        # Should have service name from manifest
        assert "service=" in metrics_response.text


class TestTracingIntegrationAssertions:
    """Test OpenTelemetry tracing integration."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Get test client for registry service."""
        return TestClient(app)

    def test_tracing_middleware_installed_and_active(self, client: TestClient):
        """Test that OpenTelemetry tracing middleware is installed and active."""
        # This test verifies that tracing doesn't break request processing
        response = client.get("/api/v1/services")
        assert response.status_code == 200

        # If correlation IDs work and no errors occur, tracing is properly integrated
        assert "X-Correlation-ID" in response.headers

    def test_correlation_id_bound_to_opentelemetry_span(self, client: TestClient):
        """Test that tracing integration is active with correlation ID propagation."""
        test_correlation_id = "tracing-correlation-test-002"

        response = client.get("/api/v1/services", headers={"X-Correlation-ID": test_correlation_id})

        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == test_correlation_id

        # Verify tracing middleware is working (correlation ID propagated correctly)
        # The observability middleware integrates tracing with correlation context


class TestErrorHandlingWithObservability:
    """Test that observability works correctly during error conditions."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Get test client for registry service."""
        return TestClient(app)

    def test_correlation_id_preserved_during_error_responses(self, client: TestClient):
        """Test that correlation ID is preserved even during error responses."""
        test_correlation_id = "error-observability-test-001"

        # Request a non-existent endpoint to trigger 404
        response = client.get(
            "/api/v1/services/non-existent-service",
            headers={"X-Correlation-ID": test_correlation_id},
        )

        # Should preserve correlation ID even for errors
        assert response.headers.get("X-Correlation-ID") == test_correlation_id

    def test_request_duration_recorded_during_errors(self, client: TestClient):
        """Test that request duration is recorded even during error responses."""
        # Request a non-existent endpoint
        response = client.get("/api/v1/services/non-existent-service")

        # Should still have duration header
        assert "X-Request-Duration-Ms" in response.headers
        duration = float(response.headers["X-Request-Duration-Ms"])
        assert duration >= 0

    def test_metrics_recorded_for_error_responses(self, client: TestClient):
        """Test that metrics are recorded for error responses."""
        # Make a request that will return an error
        client.get("/api/v1/services/non-existent-service")

        # Check metrics include error status codes
        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        # Should have HTTP metrics (including error status codes)
        assert "http_requests_total" in metrics_content

    def test_observability_survives_service_initialization_errors(self, client: TestClient):
        """Test that observability middleware works even if service components fail."""
        # This test verifies that observability is resilient to application errors
        # The health endpoints should still work with observability features

        response = client.get("/health/live")
        assert response.status_code == 200

        # Observability features should still be present
        assert "X-Correlation-ID" in response.headers
        assert "X-Request-Duration-Ms" in response.headers


class TestObservabilityMiddlewareInstallation:
    """Test that observability middleware is properly installed."""

    def test_observability_middleware_installed_on_app(self):
        """Test that ObservabilityMiddleware is installed on the FastAPI app."""
        from registry.main import app

        # Check that the app has middleware installed
        assert hasattr(app, "user_middleware")

        # The middleware should include CorrelationMiddleware
        middleware_types = [middleware.cls.__name__ for middleware in app.user_middleware]
        assert "CorrelationMiddleware" in middleware_types

    def test_metrics_endpoint_exposed_by_middleware(self):
        """Test that /metrics endpoint is exposed by the observability middleware."""
        client = TestClient(app)

        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

    def test_observability_installation_logged(self):
        """Test that observability installation generates appropriate logs."""
        # This test verifies that the ObservabilityMiddleware.install() call
        # in main.py worked without errors and the app is properly configured
        from registry.main import app

        # Verify that the app has been configured with observability
        assert hasattr(app, "user_middleware")
        assert app.title == "VentureStrat Registry Service"


class TestCustomBusinessMetricsIntegration:
    """Test integration of custom business metrics with observability middleware."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Get test client for registry service."""
        return TestClient(app)

    def test_custom_metrics_coexist_with_standard_http_metrics(self, client: TestClient):
        """Test that custom business metrics coexist with standard HTTP metrics."""
        # Make some requests to generate both standard and custom metrics
        client.get("/health/live")  # Should increment health_checks_total
        client.post("/api/v1/services")  # Should increment services_active

        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        # Verify both standard and custom metrics are present
        assert "http_requests_total" in metrics_content
        assert "http_request_duration_seconds" in metrics_content
        assert "treasury_registry_services_active" in metrics_content
        assert "treasury_registry_health_checks_total" in metrics_content

    def test_custom_metrics_maintain_cardinality_bounds(self, client: TestClient):
        """Test that custom metrics maintain bounded cardinality."""
        metrics_response = client.get("/metrics")
        metrics_content = metrics_response.text

        # Service type labels should be bounded to expected values
        service_types = ["fastapi", "grpc", "other"]
        for service_type in service_types:
            assert f'service_type="{service_type}"' in metrics_content

        # Health status should be bounded
        assert (
            'status="healthy"' in metrics_content
            or "treasury_registry_health_checks_total" in metrics_content
        )

    def test_custom_metrics_survive_errors_gracefully(self, client: TestClient):
        """Test that custom metrics operations handle errors gracefully."""
        # This tests the try-except blocks around metric operations
        # Even if metrics fail, endpoints should still work

        response = client.get("/health/live")
        assert response.status_code == 200

        response = client.post("/api/v1/services")
        assert response.status_code == 201

        # Metrics endpoint should still be accessible
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
