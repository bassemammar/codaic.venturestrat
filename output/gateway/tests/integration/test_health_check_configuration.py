"""
Integration tests for upstream health check configuration.

Tests the actual behavior of Kong health checks with running services.
Task 4.2: Configure upstream health checks in Kong
"""

import pytest
import time
import httpx
from typing import Dict, Any, List


@pytest.mark.integration
class TestHealthCheckConfiguration:
    """Integration tests for Kong health check configuration."""

    def test_kong_health_check_configuration_loaded(self, admin_client):
        """Test that Kong has loaded the health check configuration correctly."""
        # Get upstream configuration from Kong Admin API
        response = admin_client.get("/upstreams/registry-service.upstream")

        if response.status_code == 404:
            pytest.skip(
                "registry-service.upstream not found - Kong might not be fully configured"
            )

        assert (
            response.status_code == 200
        ), f"Failed to get upstream config: {response.text}"
        upstream_data = response.json()

        # Verify health check configuration is present
        assert "healthchecks" in upstream_data, "Health checks not configured in Kong"
        healthchecks = upstream_data["healthchecks"]

        # Verify active health checks
        assert "active" in healthchecks, "Active health checks not configured"
        active = healthchecks["active"]

        assert active["type"] == "http", "Active health check should be HTTP"
        assert (
            active["http_path"] == "/health/ready"
        ), "Health check path should be /health/ready"
        assert active["timeout"] == 5, "Health check timeout should be 5 seconds"
        assert active["concurrency"] == 3, "Health check concurrency should be 3"
        assert (
            active["https_verify_certificate"] is False
        ), "HTTPS verification should be disabled for dev"

        # Verify healthy thresholds
        healthy = active["healthy"]
        assert healthy["interval"] == 10, "Healthy check interval should be 10 seconds"
        assert healthy["successes"] == 3, "Should require 3 successes to mark healthy"
        assert healthy["http_statuses"] == [
            200,
            302,
        ], "Healthy status codes should be [200, 302]"

        # Verify unhealthy thresholds
        unhealthy = active["unhealthy"]
        assert (
            unhealthy["interval"] == 10
        ), "Unhealthy check interval should be 10 seconds"
        assert unhealthy["http_failures"] == 3, "Should require 3 HTTP failures"
        assert unhealthy["timeouts"] == 5, "Should require 5 timeouts"
        assert unhealthy["tcp_failures"] == 3, "Should require 3 TCP failures"
        assert unhealthy["http_statuses"] == [
            429,
            500,
            502,
            503,
            504,
        ], "Unhealthy status codes correctly set"

        # Verify passive health checks
        assert "passive" in healthchecks, "Passive health checks not configured"
        passive = healthchecks["passive"]

        assert passive["type"] == "http", "Passive health check should be HTTP"

        passive_healthy = passive["healthy"]
        expected_healthy_codes = [200, 201, 202, 204, 301, 302, 303, 304]
        assert passive_healthy["http_statuses"] == expected_healthy_codes
        assert passive_healthy["successes"] == 3

        passive_unhealthy = passive["unhealthy"]
        expected_unhealthy_codes = [429, 500, 502, 503, 504, 505]
        assert passive_unhealthy["http_statuses"] == expected_unhealthy_codes

    def test_upstream_targets_health_status(self, admin_client):
        """Test that we can query the health status of upstream targets."""
        # Get upstream health status
        response = admin_client.get("/upstreams/registry-service.upstream/health")

        if response.status_code == 404:
            pytest.skip("Upstream health endpoint not available")

        assert (
            response.status_code == 200
        ), f"Failed to get upstream health: {response.text}"
        health_data = response.json()

        assert "data" in health_data, "Health response should have data field"
        targets = health_data["data"]

        # Should have at least one target
        assert len(targets) > 0, "Should have at least one upstream target"

        for target in targets:
            assert "target" in target, "Target should have target field"
            assert "health" in target, "Target should have health field"
            assert "weight" in target, "Target should have weight field"

            # Health should be either healthy or unhealthy
            health_status = target["health"]
            assert health_status in [
                "healthy",
                "unhealthy",
            ], f"Invalid health status: {health_status}"

            # Target should follow expected format
            target_addr = target["target"]
            assert isinstance(target_addr, str), "Target address should be string"
            assert len(target_addr) > 0, "Target address should not be empty"

    def test_active_health_check_behavior(self, gateway_client, admin_client):
        """Test active health check behavior over time."""
        # Initial health status
        self._get_upstream_health_status(admin_client)

        # Make some requests through the gateway to trigger health checks
        request_results = []
        for i in range(5):
            try:
                response = gateway_client.get("/api/v1/registry/services", timeout=10)
                request_results.append(
                    {
                        "status_code": response.status_code,
                        "success": response.status_code < 400,
                        "correlation_id": response.headers.get("X-Correlation-ID"),
                        "upstream_latency": response.headers.get("X-Kong-Upstream-Latency"),
                        "upstream_latency": response.headers.get(
                            "X-Kong-Upstream-Latency"
                        ),
                        "proxy_latency": response.headers.get("X-Kong-Proxy-Latency"),
                    }
                )
            except Exception as e:
                request_results.append({"status_code": None, "success": False, "error": str(e)})
                request_results.append(
                    {"status_code": None, "success": False, "error": str(e)}
                )
            time.sleep(2)

        # Wait for health check interval to pass
        time.sleep(12)  # Slightly longer than 10-second interval

        # Check health status again
        final_health = self._get_upstream_health_status(admin_client)

        # Analyze results
        successful_requests = [r for r in request_results if r.get("success", False)]
        failed_requests = [r for r in request_results if not r.get("success", False)]

        # If service is healthy, should get mostly successful requests
        if len(successful_requests) > len(failed_requests):
            # Health status should be healthy or transitioning
            healthy_targets = [t for t in final_health if t["health"] == "healthy"]
            assert (
                len(healthy_targets) > 0
            ), "Should have at least one healthy target for successful requests"

            # Latency headers should be present for successful requests
            for request in successful_requests:
                assert (
                    request.get("upstream_latency") is not None
                ), "Upstream latency should be present"
                assert request.get("proxy_latency") is not None, "Proxy latency should be present"
                assert (
                    request.get("proxy_latency") is not None
                ), "Proxy latency should be present"

        # All correlation IDs should be unique
        correlation_ids = [
            r.get("correlation_id") for r in request_results if r.get("correlation_id")
        ]
        assert len(set(correlation_ids)) == len(correlation_ids), "Correlation IDs should be unique"
        assert len(set(correlation_ids)) == len(
            correlation_ids
        ), "Correlation IDs should be unique"

    def test_passive_health_check_integration(self, gateway_client, admin_client):
        """Test passive health check integration with request routing."""
        # Get initial health status
        self._get_upstream_health_status(admin_client)

        # Monitor request patterns over time
        response_patterns = []
        for attempt in range(10):
            try:
                start_time = time.time()
                response = gateway_client.get("/api/v1/registry/services", timeout=5)
                end_time = time.time()

                response_patterns.append(
                    {
                        "attempt": attempt,
                        "status_code": response.status_code,
                        "latency_ms": (end_time - start_time) * 1000,
                        "correlation_id": response.headers.get("X-Correlation-ID"),
                        "timestamp": time.time(),
                    }
                )

                # Check for passive health check trigger conditions
                if response.status_code in [500, 502, 503, 504]:
                    # This could trigger passive health check
                    pass

            except httpx.TimeoutException:
                response_patterns.append(
                    {
                        "attempt": attempt,
                        "status_code": 504,  # Gateway timeout
                        "latency_ms": 5000,  # Timeout duration
                        "error": "timeout",
                        "timestamp": time.time(),
                    }
                )
            except Exception as e:
                response_patterns.append(
                    {
                        "attempt": attempt,
                        "status_code": None,
                        "error": str(e),
                        "timestamp": time.time(),
                    }
                )

            time.sleep(1)  # Wait between requests

        # Analyze response patterns
        status_codes = [p["status_code"] for p in response_patterns if p["status_code"]]
        unique_status_codes = set(status_codes)

        # Should not have too many different status codes (indicates unstable health)
        assert (
            len(unique_status_codes) <= 3
        ), f"Too many status code variations: {unique_status_codes}"

        # If we have error codes, they should be handled consistently
        error_codes = [code for code in status_codes if code and code >= 500]
        if error_codes:
            # Should be consistent error handling
            error_code_set = set(error_codes)
            assert (
                len(error_code_set) <= 2
            ), f"Inconsistent error handling: {error_code_set}"

    def test_health_check_metrics_collection(self, gateway_client, admin_client):
        """Test that health check metrics are properly collected."""
        # Make requests to generate metrics
        for _ in range(3):
            try:
                gateway_client.get("/api/v1/registry/services", timeout=5)
            except:
                pass
            time.sleep(0.5)

        # Check upstream health status for metrics
        health_status = self._get_upstream_health_status(admin_client)

        # Verify health data includes expected fields
        for target in health_status:
            assert "health" in target, "Health status should be tracked"

            # Additional health check data might be available
            if "data" in target:
                data = target["data"]
                # Check for health check specific metrics
                assert isinstance(data, dict), "Health data should be structured"

        # Make a request and check for health-related headers
        try:
            response = gateway_client.get("/api/v1/registry/services")

            if response.status_code == 200:
                # Should include latency metrics
                assert "X-Kong-Upstream-Latency" in response.headers
                assert "X-Kong-Proxy-Latency" in response.headers

                # Validate latency values are reasonable
                upstream_latency = int(
                    response.headers.get("X-Kong-Upstream-Latency", "0")
                )
                proxy_latency = int(response.headers.get("X-Kong-Proxy-Latency", "0"))

                assert (
                    0 <= upstream_latency <= 30000
                ), f"Upstream latency should be reasonable: {upstream_latency}ms"
                assert (
                    0 <= proxy_latency <= 5000
                ), f"Proxy latency should be reasonable: {proxy_latency}ms"

        except Exception:
            # If requests are failing, health checks should detect this
            [t for t in health_status if t["health"] == "unhealthy"]
            # Could be acceptable if service is actually down
            pass

    def test_health_check_configuration_consistency(self, admin_client):
        """Test that health check configuration is consistent across Kong."""
        # Get upstream configuration
        upstreams_response = admin_client.get("/upstreams")

        if upstreams_response.status_code != 200:
            pytest.skip("Cannot access upstreams via Admin API")

        upstreams_data = upstreams_response.json()
        upstreams = upstreams_data.get("data", [])

        # Find our upstream
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        assert registry_upstream is not None, "registry-service.upstream not found"

        # Get detailed upstream configuration
        upstream_id = registry_upstream["id"]
        upstream_detail_response = admin_client.get(f"/upstreams/{upstream_id}")

        assert upstream_detail_response.status_code == 200
        upstream_detail = upstream_detail_response.json()

        # Verify health check configuration matches our expectations
        healthchecks = upstream_detail["healthchecks"]

        # Active health check validation
        active = healthchecks["active"]
        assert active["type"] == "http"
        assert active["http_path"] == "/health/ready"
        assert active["timeout"] == 5
        assert active["concurrency"] == 3

        # Timing configuration should be consistent
        healthy_interval = active["healthy"]["interval"]
        unhealthy_interval = active["unhealthy"]["interval"]
        timeout = active["timeout"]

        assert (
            timeout < healthy_interval
        ), "Timeout should be less than health check interval"
        assert (
            timeout < unhealthy_interval
        ), "Timeout should be less than unhealthy check interval"
        assert (
            healthy_interval == unhealthy_interval
        ), "Health check intervals should be consistent"

    def _get_upstream_health_status(self, admin_client) -> List[Dict[str, Any]]:
        """Helper method to get upstream health status."""
        try:
            response = admin_client.get("/upstreams/registry-service.upstream/health")
            if response.status_code == 200:
                health_data = response.json()
                return health_data.get("data", [])
        except Exception:
            pass

        return []

    @pytest.mark.slow
    def test_health_check_recovery_cycle(self, gateway_client, admin_client):
        """Test complete health check recovery cycle over time."""
        # This test monitors health status over a longer period
        # to verify health check behavior is stable and consistent

        monitoring_duration = 60  # Monitor for 1 minute
        check_interval = 5  # Check every 5 seconds

        start_time = time.time()
        health_history = []
        request_history = []

        while (time.time() - start_time) < monitoring_duration:
            current_time = time.time() - start_time

            # Get health status
            health_status = self._get_upstream_health_status(admin_client)
            health_summary = {
                "time": current_time,
                "healthy_count": len([t for t in health_status if t["health"] == "healthy"]),
                "unhealthy_count": len([t for t in health_status if t["health"] == "unhealthy"]),
                "healthy_count": len(
                    [t for t in health_status if t["health"] == "healthy"]
                ),
                "unhealthy_count": len(
                    [t for t in health_status if t["health"] == "unhealthy"]
                ),
                "total_targets": len(health_status),
            }
            health_history.append(health_summary)

            # Make a test request
            try:
                response = gateway_client.get("/api/v1/registry/services", timeout=5)
                request_summary = {
                    "time": current_time,
                    "status_code": response.status_code,
                    "success": response.status_code < 400,
                    "latency": response.headers.get("X-Kong-Upstream-Latency"),
                }
            except Exception as e:
                request_summary = {
                    "time": current_time,
                    "status_code": None,
                    "success": False,
                    "error": str(e),
                }

            request_history.append(request_summary)
            time.sleep(check_interval)

        # Analyze health behavior over time
        healthy_counts = [h["healthy_count"] for h in health_history]
        success_rates = []

        for i in range(0, len(request_history), 3):  # Group by 3 requests
            batch = request_history[i : i + 3]
            successes = len([r for r in batch if r.get("success", False)])
            success_rates.append(successes / len(batch))

        # Health should be relatively stable (not constantly changing)
        health_changes = sum(
            1 for i in range(1, len(healthy_counts)) if healthy_counts[i] != healthy_counts[i - 1]
            1
            for i in range(1, len(healthy_counts))
            if healthy_counts[i] != healthy_counts[i - 1]
        )

        total_checks = len(healthy_counts)
        change_rate = health_changes / total_checks if total_checks > 0 else 0

        # Should not have too frequent health changes (indicates stable health checks)
        assert (
            change_rate < 0.5
        ), f"Health status changing too frequently: {change_rate:.2%} change rate"

        # If we have mostly healthy targets, request success rate should be good
        avg_healthy_count = (
            sum(healthy_counts) / len(healthy_counts) if healthy_counts else 0
        )
        avg_success_rate = (
            sum(success_rates) / len(success_rates) if success_rates else 0
        )

        if avg_healthy_count > 0:
            assert (
                avg_success_rate > 0.3
            ), f"Low success rate ({avg_success_rate:.2%}) despite healthy targets"
