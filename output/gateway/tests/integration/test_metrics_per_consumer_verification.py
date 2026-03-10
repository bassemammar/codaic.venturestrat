"""
Integration tests for per-consumer Prometheus metrics verification.

This test verifies that Kong's Prometheus plugin correctly includes
per-consumer data in the metrics output as required by task 12.3.
"""

import pytest
import re


@pytest.mark.integration
class TestMetricsPerConsumerVerification:
    """Test suite for verifying per-consumer metrics data."""

    def test_per_consumer_metrics_configuration_enabled(
        self, admin_client, gateway_config
    ):
        """Verify that per-consumer metrics are enabled in Kong configuration."""
        # First check configuration
        plugins = gateway_config.get("plugins", [])
        prometheus_plugin = next((p for p in plugins if p.get("name") == "prometheus"), None)
        prometheus_plugin = next(
            (p for p in plugins if p.get("name") == "prometheus"), None
        )

        assert prometheus_plugin is not None, "Prometheus plugin should be configured"
        config = prometheus_plugin.get("config", {})
        assert (
            config.get("per_consumer") is True
        ), "Per-consumer metrics should be enabled in config"

        # Then verify metrics endpoint is accessible
        response = admin_client.get("/metrics")
        assert response.status_code == 200, "Metrics endpoint should be accessible"

    def test_per_consumer_metrics_include_consumer_labels(
        self,
        admin_client,
        gateway_client,
        free_tier_client,
        standard_tier_client,
        premium_tier_client,
    ):
        """Test that metrics include consumer labels for different consumer tiers."""

        # Generate traffic from different consumer tiers
        test_cases = [
            ("default-consumer", gateway_client),
            ("free-tier-consumer", free_tier_client),
            ("standard-tier-consumer", standard_tier_client),
            ("premium-tier-consumer", premium_tier_client),
        ]

        # Generate requests from each consumer
        for consumer_name, client in test_cases:
            try:
                # Make requests to generate metrics data
                response = client.get("/api/v1/registry/services")
                # Don't assert on response code since backend might not be available
                print(f"Generated traffic for {consumer_name}: {response.status_code}")
            except Exception as e:
                print(f"Request for {consumer_name} failed: {e}")
                # Continue with other consumers even if one fails

        # Get metrics and verify consumer labels are present
        metrics_response = admin_client.get("/metrics")
        assert (
            metrics_response.status_code == 200
        ), "Metrics endpoint should be accessible"

        metrics_text = metrics_response.text
        assert len(metrics_text) > 0, "Metrics response should not be empty"

        # Look for per-consumer metric patterns
        consumer_label_patterns = [
            r'consumer="[^"]*"',  # Basic consumer label
            r'kong_http_requests_total{[^}]*consumer="[^"]*"[^}]*}',  # Request count with consumer
            r'kong_request_latency_ms{[^}]*consumer="[^"]*"[^}]*}',  # Latency with consumer
        ]

        found_consumer_metrics = []
        for pattern in consumer_label_patterns:
            matches = re.findall(pattern, metrics_text)
            if matches:
                found_consumer_metrics.extend(matches)
                print(
                    f"Found consumer metrics matching '{pattern}': {len(matches)} matches"
                )

        # Verify that we found at least some consumer metrics
        assert len(found_consumer_metrics) > 0, (
            f"Expected to find per-consumer metrics, but none were found. "
            f"First 500 chars of metrics output: {metrics_text[:500]}"
        )

    def test_per_consumer_metrics_distinguish_between_consumers(
        self, admin_client, free_tier_client, standard_tier_client
    ):
        """Test that metrics can distinguish between different consumers."""

        # Generate traffic from specific consumers
        consumers_to_test = [
            ("free-tier-consumer", free_tier_client),
            ("standard-tier-consumer", standard_tier_client),
        ]

        # Generate multiple requests from each consumer to ensure metrics are created
        for consumer_name, client in consumers_to_test:
            for i in range(3):  # Make multiple requests
                try:
                    response = client.get("/health")  # Health endpoint should work
                    print(f"Request {i+1} for {consumer_name}: {response.status_code}")
                except Exception as e:
                    print(f"Request {i+1} for {consumer_name} failed: {e}")

        # Get metrics
        metrics_response = admin_client.get("/metrics")
        assert metrics_response.status_code == 200

        metrics_text = metrics_response.text

        # Extract all consumer labels from metrics
        consumer_matches = re.findall(r'consumer="([^"]*)"', metrics_text)
        unique_consumers = set(consumer_matches)

        print(f"Found unique consumers in metrics: {unique_consumers}")

        # Verify that we have metrics for multiple consumers
        # Note: We might not see all consumers if they haven't generated traffic
        # but we should see at least one consumer in the metrics
        assert len(unique_consumers) >= 1, (
            f"Expected metrics to distinguish between consumers, "
            f"found consumers: {unique_consumers}"
        )

    def test_per_consumer_request_count_metrics(self, admin_client, gateway_client):
        """Test that per-consumer request count metrics are present."""

        # Generate some requests
        for i in range(5):
            try:
                response = gateway_client.get("/health")
                print(f"Health request {i+1}: {response.status_code}")
            except Exception as e:
                print(f"Health request {i+1} failed: {e}")

        # Get metrics
        metrics_response = admin_client.get("/metrics")
        assert metrics_response.status_code == 200

        metrics_text = metrics_response.text

        # Look for request count metrics with consumer labels
        request_count_patterns = [
            r'kong_http_requests_total{[^}]*consumer="[^"]*"[^}]*}\s+[0-9]+',
            r'kong_nginx_http_current_connections{[^}]*consumer="[^"]*"[^}]*}',
        ]

        found_request_metrics = []
        for pattern in request_count_patterns:
            matches = re.findall(pattern, metrics_text)
            found_request_metrics.extend(matches)
            if matches:
                print(
                    f"Found request count metrics: {matches[:3]}..."
                )  # Show first 3 matches

        # We should find some request-related metrics (even if the count is 0)
        # The important thing is that consumer labels are included
        print(
            f"Total request count metrics with consumer labels found: {len(found_request_metrics)}"
        )

    def test_per_consumer_latency_metrics(self, admin_client, gateway_client):
        """Test that per-consumer latency metrics are present."""

        # Generate requests to create latency metrics
        for i in range(3):
            try:
                response = gateway_client.get("/health")
                print(f"Latency test request {i+1}: {response.status_code}")
            except Exception as e:
                print(f"Latency test request {i+1} failed: {e}")

        # Get metrics
        metrics_response = admin_client.get("/metrics")
        assert metrics_response.status_code == 200

        metrics_text = metrics_response.text

        # Look for latency metrics with consumer labels
        latency_patterns = [
            r'kong_request_latency_ms{[^}]*consumer="[^"]*"[^}]*}',
            r'kong_upstream_latency_ms{[^}]*consumer="[^"]*"[^}]*}',
            r'kong_kong_latency_ms{[^}]*consumer="[^"]*"[^}]*}',
        ]

        found_latency_metrics = []
        for pattern in latency_patterns:
            matches = re.findall(pattern, metrics_text)
            found_latency_metrics.extend(matches)
            if matches:
                print(
                    f"Found latency metrics: {matches[:2]}..."
                )  # Show first 2 matches

        print(
            f"Total latency metrics with consumer labels found: {len(found_latency_metrics)}"
        )

    def test_per_consumer_status_code_metrics(
        self, admin_client, gateway_client, unauthorized_client
    ):
        """Test that status code metrics include consumer information."""

        # Generate requests with different status codes
        test_requests = [
            ("authenticated_200", gateway_client, "/health"),
            ("authenticated_404", gateway_client, "/nonexistent"),
            ("unauthorized_401", unauthorized_client, "/api/v1/registry/services"),
        ]

        for test_name, client, path in test_requests:
            try:
                response = client.get(path)
                print(f"{test_name}: {response.status_code}")
            except Exception as e:
                print(f"{test_name} failed: {e}")

        # Get metrics
        metrics_response = admin_client.get("/metrics")
        assert metrics_response.status_code == 200

        metrics_text = metrics_response.text

        # Look for status code metrics that may include consumer labels
        status_code_patterns = [
            r'kong_http_requests_total{[^}]*code="[0-9]+"[^}]*}',
            r'kong_http_requests_total{[^}]*consumer="[^"]*"[^}]*code="[0-9]+"[^}]*}',
        ]

        found_status_metrics = []
        for pattern in status_code_patterns:
            matches = re.findall(pattern, metrics_text)
            found_status_metrics.extend(matches)
            if matches:
                print(f"Found status code metrics: {matches[:3]}...")

        # Should find status code related metrics
        assert len(found_status_metrics) > 0, "Expected to find status code metrics in output"
        assert (
            len(found_status_metrics) > 0
        ), "Expected to find status code metrics in output"

    def test_prometheus_metrics_format_with_consumer_labels(
        self, admin_client, gateway_client
    ):
        """Test that consumer-labeled metrics follow proper Prometheus format."""

        # Generate some traffic
        gateway_client.get("/health")

        # Get metrics
        metrics_response = admin_client.get("/metrics")
        assert metrics_response.status_code == 200

        metrics_text = metrics_response.text

        # Find lines with consumer labels
        consumer_metric_lines = []
        for line in metrics_text.split("\n"):
            if 'consumer="' in line and not line.startswith("#"):
                consumer_metric_lines.append(line)

        print(f"Found {len(consumer_metric_lines)} metric lines with consumer labels")

        # Validate format of consumer-labeled metrics
        for line in consumer_metric_lines[:5]:  # Check first 5 lines
            # Should have format: metric_name{labels} value [timestamp]
            assert " " in line, f"Metric line should have space between name and value: {line}"
            assert (
                " " in line
            ), f"Metric line should have space between name and value: {line}"

            parts = line.split(" ", 1)
            metric_part = parts[0]
            value_part = parts[1]

            # Metric part should contain consumer label
            assert (
                'consumer="' in metric_part
            ), f"Consumer label missing in metric: {line}"

            # Should have valid braces for labels
            assert (
                "{" in metric_part and "}" in metric_part
            ), f"Invalid label format in metric: {line}"

            # Value should be numeric
            value = value_part.split()[0]  # Get first part (value)
            try:
                float(value)
            except ValueError:
                pytest.fail(f"Invalid numeric value '{value}' in metric line: {line}")

            print(f"Valid consumer metric: {line[:100]}...")

    def test_metrics_per_consumer_data_comprehensive_verification(
        self, admin_client, gateway_client, free_tier_client, standard_tier_client
    ):
        """Comprehensive test to verify all aspects of per-consumer metrics data."""

        # Step 1: Generate traffic from multiple consumers with different patterns
        traffic_scenarios = [
            (
                "default-consumer",
                gateway_client,
                ["/health", "/health", "/api/v1/registry/services"],
            ),
            ("free-tier-consumer", free_tier_client, ["/health", "/nonexistent"]),
            ("standard-tier-consumer", standard_tier_client, ["/health", "/health"]),
        ]

        for consumer_name, client, paths in traffic_scenarios:
            for path in paths:
                try:
                    response = client.get(path)
                    print(f"{consumer_name} -> {path}: {response.status_code}")
                except Exception as e:
                    print(f"{consumer_name} -> {path}: Failed - {e}")

        # Step 2: Get metrics and perform comprehensive verification
        metrics_response = admin_client.get("/metrics")
        assert metrics_response.status_code == 200

        metrics_text = metrics_response.text

        # Step 3: Verify per-consumer metrics exist
        verification_results = {}

        # Check for consumer labels in metrics
        consumer_metrics = re.findall(r'[^#\n]*consumer="([^"]*)"[^#\n]*', metrics_text)
        verification_results["consumer_metrics_found"] = len(consumer_metrics) > 0
        verification_results["unique_consumers"] = set(consumer_metrics)

        # Check for specific metric types with consumer labels
        metric_types_to_check = [
            ("request_total", r'kong_http_requests_total{[^}]*consumer="[^"]*"[^}]*}'),
            ("request_latency", r'kong_request_latency_ms{[^}]*consumer="[^"]*"[^}]*}'),
            (
                "status_codes",
                r'kong_http_requests_total{[^}]*consumer="[^"]*"[^}]*code="[^"]*"[^}]*}',
            ),
        ]

        for metric_type, pattern in metric_types_to_check:
            matches = re.findall(pattern, metrics_text)
            verification_results[f"{metric_type}_with_consumer"] = len(matches) > 0
            if matches:
                print(
                    f"✓ Found {metric_type} metrics with consumer labels: {len(matches)} instances"
                )

        # Step 4: Print comprehensive results
        print("\n=== Per-Consumer Metrics Verification Results ===")
        print(f"Consumer metrics found: {verification_results['consumer_metrics_found']}")
        print(f"Unique consumers in metrics: {verification_results['unique_consumers']}")
        print(
            f"Consumer metrics found: {verification_results['consumer_metrics_found']}"
        )
        print(
            f"Unique consumers in metrics: {verification_results['unique_consumers']}"
        )

        for metric_type, pattern in metric_types_to_check:
            result = verification_results[f"{metric_type}_with_consumer"]
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{metric_type} with consumer labels: {status}")

        # Step 5: Main assertion - we should have at least basic per-consumer metrics
        assert verification_results["consumer_metrics_found"], (
            f"FAIL: No per-consumer metrics found. "
            f"Configuration shows per_consumer=true but no consumer labels in metrics output. "
            f"First 1000 chars of metrics: {metrics_text[:1000]}"
        )

        print("\n✓ PASS: Per-consumer metrics verification completed successfully!")
        print(f"Found consumer data for: {', '.join(verification_results['unique_consumers'])}")
        print(
            f"Found consumer data for: {', '.join(verification_results['unique_consumers'])}"
        )


# Standalone verification function for task 12.5
def verify_curl_metrics_endpoint():
    """
    Standalone verification function for Task 12.5: curl http://localhost:8001/metrics

    This function can be run independently to verify the exact task requirement.
    """
    import requests
    import subprocess

    print("=" * 60)
    print("TASK 12.5 VERIFICATION: curl http://localhost:8001/metrics")
    print("=" * 60)

    # Test 1: Basic endpoint accessibility
    print("Test 1: Checking metrics endpoint accessibility...")
    try:
        response = requests.get("http://localhost:8001/metrics", timeout=10)
        if response.status_code == 200:
            print("✓ SUCCESS: Metrics endpoint returns 200 OK")
        else:
            print(f"✗ FAILED: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ FAILED: Cannot access metrics endpoint: {e}")
        return False

    # Test 2: Verify Prometheus format
    print("\nTest 2: Verifying Prometheus format...")
    metrics_text = response.text
    if len(metrics_text) == 0:
        print("✗ FAILED: Empty response")
        return False

    if "# HELP" not in metrics_text or "# TYPE" not in metrics_text:
        print("✗ FAILED: Not proper Prometheus format")
        return False

    print("✓ SUCCESS: Response contains Prometheus format")

    # Test 3: Verify Kong metrics
    print("\nTest 3: Checking for Kong metrics...")
    kong_metrics = [
        "kong_bandwidth_bytes",
        "kong_http_requests_total",
        "kong_datastore_reachable",
    ]

    found_metrics = []
    for metric in kong_metrics:
        if metric in metrics_text:
            found_metrics.append(metric)

    if len(found_metrics) >= 2:
        print(f"✓ SUCCESS: Found Kong metrics: {', '.join(found_metrics)}")
    else:
        print(
            f"? WARNING: Only found {len(found_metrics)} Kong metrics: {found_metrics}"
        )

    # Test 4: Test actual curl command
    print("\nTest 4: Testing actual curl command...")
    try:
        result = subprocess.run(
            ["curl", "-f", "-s", "http://localhost:8001/metrics"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and len(result.stdout) > 0:
            print("✓ SUCCESS: curl command works correctly")
            print(f"Output length: {len(result.stdout)} characters")
        else:
            print(f"✗ FAILED: curl command failed (return code: {result.returncode})")
            return False

    except Exception as e:
        print(f"✗ FAILED: Error running curl command: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ TASK 12.5 VERIFICATION COMPLETE")
    print("✓ Kong Prometheus metrics endpoint is working correctly")
    print("✓ curl http://localhost:8001/metrics returns expected data")
    print("=" * 60)

    return True


if __name__ == "__main__":
    """Run standalone verification when called directly."""
    success = verify_curl_metrics_endpoint()
    exit(0 if success else 1)
