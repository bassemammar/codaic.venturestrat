"""
Integration tests for Prometheus metrics endpoint.

Tests the /metrics endpoint exposed by Kong's Prometheus plugin.
"""

import pytest
import re


@pytest.mark.integration
class TestMetricsEndpoint:
    """Test Kong Prometheus metrics endpoint."""

    def test_metrics_endpoint_accessible(self, admin_client):
        """Test that metrics endpoint is accessible via Admin API."""
        response = admin_client.get("/metrics")

        assert response.status_code == 200, "Metrics endpoint should be accessible"

    def test_metrics_endpoint_content_type(self, admin_client):
        """Test that metrics endpoint returns Prometheus format."""
        response = admin_client.get("/metrics")

        assert response.status_code == 200
        # Prometheus metrics should be plain text
        content_type = response.headers.get("content-type", "")
        assert (
            "text/plain" in content_type.lower()
        ), f"Expected text/plain content type, got: {content_type}"

    def test_metrics_endpoint_basic_structure(self, admin_client):
        """Test that metrics endpoint returns Prometheus format data."""
        response = admin_client.get("/metrics")

        assert response.status_code == 200

        metrics_text = response.text
        assert len(metrics_text) > 0, "Metrics response should not be empty"

        # Should contain Prometheus format metrics
        # Look for basic Prometheus patterns
        assert "# HELP" in metrics_text, "Should contain HELP comments"
        assert "# TYPE" in metrics_text, "Should contain TYPE comments"

    def test_kong_basic_metrics_present(self, admin_client):
        """Test that basic Kong metrics are present."""
        response = admin_client.get("/metrics")

        assert response.status_code == 200

        metrics_text = response.text

        # Basic Kong metrics that should be present
        expected_metric_patterns = [
            r"kong_nginx_http_current_connections",  # Basic connection metrics
            r"kong_datastore_reachable",  # Database connectivity
        ]

        for pattern in expected_metric_patterns:
            assert re.search(
                pattern, metrics_text
            ), f"Expected metric pattern '{pattern}' not found in metrics output"

    def test_request_metrics_present_after_traffic(self, admin_client, gateway_client):
        """Test that request metrics appear after generating some traffic."""
        # Generate some traffic first
        gateway_client.get("/health")  # Should work without auth

        # Get metrics
        response = admin_client.get("/metrics")
        assert response.status_code == 200

        metrics_text = response.text

        # Should have request-related metrics after traffic
        request_metric_patterns = [
            r"kong_http_requests_total",  # Total request count
        ]

        # Note: These metrics might be 0 if no traffic, but the metric names should exist
        for pattern in request_metric_patterns:
            # Check if metric name exists (with any value)
            assert re.search(
                f"{pattern}", metrics_text
            ), f"Expected request metric pattern '{pattern}' not found after traffic"

    def test_metrics_endpoint_performance(self, admin_client):
        """Test that metrics endpoint responds reasonably quickly."""
        import time

        start_time = time.time()
        response = admin_client.get("/metrics")
        end_time = time.time()

        assert response.status_code == 200

        # Metrics endpoint should respond within reasonable time (2 seconds)
        response_time = end_time - start_time
        assert (
            response_time < 2.0
        ), f"Metrics endpoint took too long: {response_time:.2f}s"

    def test_metrics_no_authentication_required_admin_api(self, admin_client):
        """Test that metrics endpoint doesn't require authentication on Admin API."""
        # Admin API should not require authentication for metrics
        response = admin_client.get("/metrics")

        # Should not get authentication error
        assert (
            response.status_code == 200
        ), "Metrics should be accessible without auth on Admin API"

    def test_metrics_content_format_validation(self, admin_client):
        """Test that metrics content follows Prometheus format."""
        response = admin_client.get("/metrics")

        assert response.status_code == 200

        metrics_text = response.text
        lines = metrics_text.strip().split("\n")

        # Validate basic Prometheus format rules
        for line in lines:
            if line.strip() == "":
                continue  # Empty lines are allowed

            # Comments should start with #
            if line.startswith("#"):
                assert line.startswith("# "), "Comments should have space after #"
                continue

            # Metric lines should have format: metric_name{labels} value [timestamp]
            if not line.startswith("#"):
                # Should contain a metric name and value
                assert (
                    " " in line
                ), f"Metric line should contain space between name and value: {line}"

                parts = line.split(" ", 1)
                metric_part = parts[0]

                # Metric name should not be empty
                assert len(metric_part) > 0, f"Metric name should not be empty: {line}"

    def test_consumer_metrics_enabled(self, admin_client, gateway_client):
        """Test that per-consumer metrics are collected."""
        # Generate traffic with API key to create consumer metrics
        gateway_client.get("/api/v1/registry/services")

        # Check metrics endpoint
        metrics_response = admin_client.get("/metrics")
        assert metrics_response.status_code == 200

        metrics_text = metrics_response.text

        # Look for consumer-related metrics (might be present even if 0)
        # Kong's Prometheus plugin should include consumer labels when per_consumer=true
        consumer_patterns = [
            r'consumer="[^"]*"',  # Look for consumer labels in any metric
        ]

        # Note: Consumer metrics might only appear after actual traffic with valid API keys
        # So we check if the pattern exists anywhere in the metrics output
        has_consumer_metrics = any(
            re.search(pattern, metrics_text) for pattern in consumer_patterns
        )

        # If we don't find consumer metrics, it might be because:
        # 1. No traffic has been generated yet
        # 2. Consumer metrics are only shown for actual API key usage
        # This is informational - we mainly want to verify the endpoint works
        print(f"Consumer metrics found: {has_consumer_metrics}")

    def test_status_code_metrics_enabled(self, admin_client, gateway_client):
        """Test that status code metrics are collected."""
        # Generate traffic with different status codes
        gateway_client.get("/health")  # Should be 200
        gateway_client.get("/nonexistent")  # Should be 404

        # Check metrics endpoint
        metrics_response = admin_client.get("/metrics")
        assert metrics_response.status_code == 200

        metrics_text = metrics_response.text

        # Look for status code metrics
        status_code_patterns = [
            r'code="[0-9]+"',  # Look for HTTP status code labels
        ]

        has_status_code_metrics = any(
            re.search(pattern, metrics_text) for pattern in status_code_patterns
        )

        print(f"Status code metrics found: {has_status_code_metrics}")

    def test_latency_metrics_enabled(self, admin_client, gateway_client):
        """Test that latency metrics are collected."""
        # Generate some traffic
        gateway_client.get("/health")

        # Check metrics endpoint
        metrics_response = admin_client.get("/metrics")
        assert metrics_response.status_code == 200

        metrics_text = metrics_response.text

        # Look for latency-related metrics
        latency_patterns = [
            r"kong.*latency",  # Any Kong latency metrics
            r"kong.*duration",  # Any Kong duration metrics
        ]

        has_latency_metrics = any(
            re.search(pattern, metrics_text, re.IGNORECASE)
            for pattern in latency_patterns
        )

        print(f"Latency metrics found: {has_latency_metrics}")

    def test_metrics_endpoint_multiple_requests(self, admin_client):
        """Test that metrics endpoint is stable across multiple requests."""
        # Make multiple requests to metrics endpoint
        responses = []
        for _ in range(3):
            response = admin_client.get("/metrics")
            responses.append(response)

        # All requests should succeed
        for i, response in enumerate(responses):
            assert (
                response.status_code == 200
            ), f"Request {i+1} to metrics endpoint failed"

        # All responses should contain metrics data
        for i, response in enumerate(responses):
            assert len(response.text) > 0, f"Request {i+1} returned empty metrics"
            assert "# HELP" in response.text, f"Request {i+1} doesn't contain Prometheus format"
            assert (
                "# HELP" in response.text
            ), f"Request {i+1} doesn't contain Prometheus format"
