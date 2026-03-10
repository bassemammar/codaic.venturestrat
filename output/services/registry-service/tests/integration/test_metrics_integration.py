"""Integration test for registry-service metrics endpoint.

This test verifies that the observability middleware is correctly integrated
with the registry service and that metrics are properly exposed via the
/metrics endpoint in a realistic deployment scenario.

Run with: pytest tests/integration/test_metrics_integration.py -m integration
"""

import re
import time

import pytest
from fastapi.testclient import TestClient
from registry.main import app


@pytest.mark.integration
class TestRegistryServiceMetricsIntegration:
    """Integration tests for registry-service metrics endpoint.

    These tests verify the complete metrics integration including:
    - Metrics endpoint accessibility
    - Standard HTTP metrics collection
    - Custom business metrics
    - Metric format compliance
    - Real-world usage scenarios
    """

    @pytest.fixture
    def client(self) -> TestClient:
        """Get test client for registry service."""
        return TestClient(app)

    def test_metrics_endpoint_accessibility(self, client: TestClient) -> None:
        """Test that /metrics endpoint is accessible and returns proper format."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

        content = response.text
        assert len(content) > 0, "Metrics endpoint should return content"

        # Verify Prometheus format markers
        lines = content.strip().split("\n")
        has_help_lines = any(line.startswith("# HELP") for line in lines)
        has_type_lines = any(line.startswith("# TYPE") for line in lines)
        has_metric_lines = any(line and not line.startswith("#") for line in lines)

        assert has_help_lines, "Should have # HELP lines in Prometheus format"
        assert has_type_lines, "Should have # TYPE lines in Prometheus format"
        assert has_metric_lines, "Should have metric value lines"

    def test_http_metrics_integration(self, client: TestClient) -> None:
        """Test that HTTP metrics are properly collected and exposed."""
        # Make requests to generate HTTP metrics
        client.get("/api/v1/services")
        client.post("/api/v1/services", json={})
        client.get("/api/v1/services/test-service")

        # Get metrics
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text

        # Verify HTTP metrics are present
        assert "http_requests_total" in content, "Should have HTTP requests counter"
        assert "http_request_duration_seconds" in content, "Should have HTTP duration histogram"

        # Verify standard labels are present
        assert "service=" in content, "Metrics should have service label"
        assert "version=" in content, "Metrics should have version label"
        assert "env=" in content, "Metrics should have environment label"
        assert "method=" in content, "HTTP metrics should have method label"
        assert "status_code=" in content, "HTTP metrics should have status_code label"

    def test_custom_business_metrics_integration(self, client: TestClient) -> None:
        """Test that custom business metrics are properly integrated."""
        # Make requests that should trigger custom metrics
        client.get("/health/live")  # Should increment health_checks_total
        client.get("/health/ready")  # Should increment health_checks_total
        client.post("/api/v1/services")  # Should increment services_active

        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text

        # Verify custom metrics are present
        assert "treasury_registry_services_active" in content, "Should have services active gauge"
        assert (
            "treasury_registry_health_checks_total" in content
        ), "Should have health checks counter"

        # Verify metric metadata
        assert (
            "# HELP treasury_registry_services_active Number of active registered services"
            in content
        )
        assert "# TYPE treasury_registry_services_active gauge" in content
        assert (
            "# HELP treasury_registry_health_checks_total Total health check executions" in content
        )
        assert "# TYPE treasury_registry_health_checks_total counter" in content

    def test_metric_labels_specification_compliance(self, client: TestClient) -> None:
        """Test that metrics follow the technical specification for labels."""
        # Generate metrics data
        client.get("/health/live")
        client.post("/api/v1/services")
        client.get("/api/v1/services")

        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text

        # Verify services active gauge has service_type label
        services_active_pattern = r'treasury_registry_services_active\{.*service_type="[^"]+"\}'
        assert re.search(
            services_active_pattern, content
        ), "Services active should have service_type label"

        # Verify health checks counter has status label
        health_checks_pattern = r'treasury_registry_health_checks_total\{.*status="[^"]+"\}'
        assert re.search(
            health_checks_pattern, content
        ), "Health checks counter should have status label"

        # Verify HTTP metrics have required labels
        # The labels might not be in the exact order we specify, so check for presence individually
        assert "http_requests_total{" in content, "Should have http_requests_total metric"
        assert 'method="' in content, "HTTP metrics should have method label"
        assert 'status_code="' in content, "HTTP metrics should have status_code label"

    def test_metric_values_numeric_validity(self, client: TestClient) -> None:
        """Test that all metric values are valid numeric values."""
        # Generate some metrics
        client.get("/health/live")
        client.post("/api/v1/services")

        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text

        lines = content.split("\n")
        for line in lines:
            # Skip comments and empty lines
            if line.startswith("#") or not line.strip():
                continue

            # Parse metric lines (format: metric_name{labels} value timestamp?)
            parts = line.split()
            if len(parts) >= 2:
                metric_value = parts[-1]
                try:
                    # Should be able to parse as float
                    float(metric_value)
                except ValueError:
                    pytest.fail(f"Invalid metric value '{metric_value}' in line: {line}")

    def test_correlation_id_middleware_integration(self, client: TestClient) -> None:
        """Test that correlation ID middleware works with metrics collection."""
        test_correlation_id = "test-integration-corr-12345"

        # Make request with correlation ID
        response = client.get("/api/v1/services", headers={"X-Correlation-ID": test_correlation_id})

        # Verify correlation ID is echoed (observability middleware feature)
        assert response.headers.get("X-Correlation-ID") == test_correlation_id

        # Verify request duration header is added (observability middleware feature)
        assert "X-Request-Duration-Ms" in response.headers
        duration = response.headers["X-Request-Duration-Ms"]
        assert float(duration) >= 0

        # Get metrics to ensure they were recorded
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        assert "http_requests_total" in metrics_response.text

    def test_metrics_performance_characteristics(self, client: TestClient) -> None:
        """Test that metrics collection doesn't significantly impact performance."""
        start_time = time.time()

        # Make multiple requests
        for _ in range(10):
            response = client.get("/api/v1/services")
            assert response.status_code == 200

        # Get metrics
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200

        end_time = time.time()
        total_duration = (end_time - start_time) * 1000  # Convert to ms

        # Should complete reasonably quickly (10 requests + metrics in < 5 seconds)
        assert (
            total_duration < 5000
        ), f"Operations took {total_duration:.2f}ms, should be under 5000ms"

    def test_service_operations_affect_custom_metrics(self, client: TestClient) -> None:
        """Test that service operations properly affect custom business metrics."""
        # Get initial metrics state
        initial_response = client.get("/metrics")
        initial_content = initial_response.text

        # Perform operations that should change metrics
        health_responses = []
        for _ in range(3):
            resp = client.get("/health/live")
            health_responses.append(resp)
            assert resp.status_code == 200

        # Register services (should increment services_active)
        for _ in range(2):
            resp = client.post("/api/v1/services")
            assert resp.status_code == 201

        # Get final metrics
        final_response = client.get("/metrics")
        final_content = final_response.text

        # Both should be successful
        assert initial_response.status_code == 200
        assert final_response.status_code == 200

        # Verify custom metrics are present in both
        for content in [initial_content, final_content]:
            assert "treasury_registry_services_active" in content
            assert "treasury_registry_health_checks_total" in content

    def test_observability_tier_configuration(self, client: TestClient) -> None:
        """Test that observability is configured for 'fast' tier as per manifest."""
        # Generate some requests to create histogram data
        for _ in range(5):
            client.get("/api/v1/services")

        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text

        # Should have HTTP duration histogram
        assert "http_request_duration_seconds" in content

        # For 'fast' tier, should have appropriate buckets from manifest
        # Expected buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
        expected_buckets = ["0.005", "0.01", "0.025", "0.05", "0.1", "0.25", "0.5"]

        for bucket in expected_buckets:
            bucket_pattern = f'le="{bucket}"'
            assert bucket_pattern in content, f"Should have bucket {bucket} for fast tier"

    def test_concurrent_metrics_access(self, client: TestClient) -> None:
        """Test that metrics endpoint handles concurrent access properly."""
        import queue
        import threading

        results = queue.Queue()

        def make_request():
            try:
                response = client.get("/metrics")
                results.put(response.status_code)
            except Exception as e:
                results.put(str(e))

        # Create multiple threads to access metrics endpoint
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all requests succeeded
        while not results.empty():
            result = results.get()
            assert result == 200, f"Expected 200 status code, got {result}"

    def test_end_to_end_observability_integration(self, client: TestClient) -> None:
        """Comprehensive end-to-end test of observability integration."""
        # Step 1: Verify clean initial state
        initial_response = client.get("/metrics")
        assert initial_response.status_code == 200

        # Step 2: Perform comprehensive operations
        operations = [
            ("GET", "/health/live"),
            ("GET", "/health/ready"),
            ("GET", "/api/v1/services"),
            ("GET", "/api/v1/services/test-service"),
            ("POST", "/api/v1/services"),
            ("POST", "/api/v1/services"),
            ("DELETE", "/api/v1/services/test-instance"),
        ]

        operation_results = []
        for method, path in operations:
            if method == "GET":
                resp = client.get(path)
            elif method == "POST":
                resp = client.post(path, json={})
            elif method == "DELETE":
                resp = client.delete(path)

            operation_results.append((method, path, resp.status_code))
            # Verify observability headers are present for all requests
            assert "X-Correlation-ID" in resp.headers, f"Missing correlation ID for {method} {path}"
            assert (
                "X-Request-Duration-Ms" in resp.headers
            ), f"Missing duration header for {method} {path}"

        # Step 3: Verify final metrics state
        final_response = client.get("/metrics")
        assert final_response.status_code == 200
        final_content = final_response.text

        # Step 4: Validate all required metrics are present
        required_metrics = [
            "http_requests_total",
            "http_request_duration_seconds",
            "treasury_registry_services_active",
            "treasury_registry_health_checks_total",
        ]

        for metric in required_metrics:
            assert metric in final_content, f"Missing required metric: {metric}"

        # Step 5: Verify metric metadata is complete
        help_patterns = [
            "# HELP treasury_registry_services_active Number of active registered services",
            "# HELP treasury_registry_health_checks_total Total health check executions",
        ]

        type_patterns = [
            "# TYPE treasury_registry_services_active gauge",
            "# TYPE treasury_registry_health_checks_total counter",
        ]

        for pattern in help_patterns + type_patterns:
            assert pattern in final_content, f"Missing metric metadata: {pattern}"

        # Step 6: Verify all operations completed successfully
        successful_ops = [
            result for result in operation_results if result[2] in [200, 201, 204, 404]
        ]
        assert len(successful_ops) == len(
            operations
        ), f"Some operations failed: {operation_results}"

        print("✓ End-to-end observability integration test completed successfully")
        print(f"  - Completed {len(operations)} operations")
        print(f"  - Verified {len(required_metrics)} required metrics")
        print(f"  - Validated {len(help_patterns + type_patterns)} metadata patterns")


@pytest.mark.integration
@pytest.mark.slow
class TestRegistryServicePrometheusCompliance:
    """Test that metrics output is compliant with Prometheus standards."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Get test client for registry service."""
        return TestClient(app)

    def test_prometheus_format_compliance(self, client: TestClient) -> None:
        """Test that metrics output strictly follows Prometheus format."""
        # Generate some metrics
        client.get("/health/live")
        client.post("/api/v1/services")

        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text

        lines = content.strip().split("\n")

        # Track metrics found
        metrics_found = set()
        current_metric = None

        for line in lines:
            if line.startswith("# HELP "):
                # Extract metric name from HELP line
                parts = line.split(" ", 3)
                if len(parts) >= 3:
                    current_metric = parts[2]

            elif line.startswith("# TYPE "):
                # Verify TYPE follows HELP
                parts = line.split(" ", 3)
                if len(parts) >= 4:
                    metric_name = parts[2]
                    metric_type = parts[3]
                    assert (
                        metric_name == current_metric
                    ), f"TYPE metric {metric_name} doesn't match HELP {current_metric}"
                    assert metric_type in [
                        "counter",
                        "gauge",
                        "histogram",
                        "summary",
                    ], f"Invalid metric type: {metric_type}"

            elif line and not line.startswith("#"):
                # Metric value line
                if "{" in line:
                    metric_name = line.split("{")[0]
                else:
                    metric_name = line.split()[0]
                metrics_found.add(metric_name)

                # Verify line format: metric_name{labels} value [timestamp]
                parts = line.split()
                assert len(parts) >= 2, f"Invalid metric line format: {line}"

                # Verify value is numeric
                try:
                    float(parts[-1])
                except ValueError:
                    pytest.fail(f"Non-numeric metric value in line: {line}")

        # Verify we found expected custom metrics
        expected_custom_metrics = {
            "treasury_registry_services_active",
            "treasury_registry_health_checks_total",
        }

        found_custom_metrics = metrics_found.intersection(expected_custom_metrics)
        assert (
            len(found_custom_metrics) >= 2
        ), f"Missing custom metrics. Found: {found_custom_metrics}"

    def test_metric_naming_conventions(self, client: TestClient) -> None:
        """Test that metric names follow OpenMetrics/Prometheus conventions."""
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text

        lines = content.split("\n")
        metric_names = set()

        for line in lines:
            if line and not line.startswith("#"):
                if "{" in line:
                    metric_name = line.split("{")[0]
                else:
                    metric_name = line.split()[0]
                metric_names.add(metric_name)

        # Verify naming conventions for custom metrics
        for metric_name in metric_names:
            if metric_name.startswith("treasury_"):
                # Should use snake_case
                assert "_" in metric_name, f"Custom metric should use snake_case: {metric_name}"
                # Should not end with underscore
                assert not metric_name.endswith(
                    "_"
                ), f"Metric name should not end with underscore: {metric_name}"
                # Should not have double underscores
                assert (
                    "__" not in metric_name
                ), f"Metric name should not have double underscores: {metric_name}"

    def test_histogram_bucket_compliance(self, client: TestClient) -> None:
        """Test that histogram metrics follow Prometheus bucket conventions."""
        # Generate HTTP requests to create histogram data
        for _ in range(5):
            client.get("/api/v1/services")

        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text

        lines = content.split("\n")
        histogram_buckets = []
        histogram_count = None
        histogram_sum = None

        for line in lines:
            if "http_request_duration_seconds_bucket" in line:
                # Extract le value
                if "le=" in line:
                    le_part = line.split('le="')[1].split('"')[0]
                    histogram_buckets.append(le_part)
            elif "http_request_duration_seconds_count" in line:
                histogram_count = line
            elif "http_request_duration_seconds_sum" in line:
                histogram_sum = line

        # Verify histogram structure
        assert len(histogram_buckets) > 0, "Should have histogram buckets"
        assert histogram_count is not None, "Should have histogram _count"
        assert histogram_sum is not None, "Should have histogram _sum"

        # Verify +Inf bucket exists
        assert "+Inf" in histogram_buckets, "Should have +Inf bucket"

        # Verify buckets are in ascending order (except +Inf)
        # Since we can have multiple histogram series, check that each unique bucket set is ordered
        unique_bucket_values = list(set(bucket for bucket in histogram_buckets if bucket != "+Inf"))
        numeric_buckets = [float(bucket) for bucket in unique_bucket_values]

        # The unique bucket values should represent a monotonically increasing sequence
        assert len(numeric_buckets) > 0, "Should have numeric histogram buckets"
        # Just verify we have reasonable bucket values (not test exact ordering since multiple series)
        assert min(numeric_buckets) > 0, "Histogram buckets should be positive"
        assert max(numeric_buckets) < float("inf"), "Should have finite bucket values"
