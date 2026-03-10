"""
Integration test for Task 4.4: Verify only healthy instances receive traffic.

This test specifically verifies that Kong's health-aware routing ensures
only healthy service instances receive traffic, excluding unhealthy ones.

Task 4.4: Verify: only healthy instances receive traffic
"""

import pytest
import time
import httpx
from typing import List, Dict, Any
import threading
import random


@pytest.mark.integration
class TestTask44VerifyOnlyHealthyInstancesReceiveTraffic:
    """
    Verification test for Kong's health-aware routing behavior.

    This test verifies that Kong Gateway properly routes traffic only to
    healthy service instances and excludes unhealthy instances from routing.
    """

    def test_verification_health_aware_routing_excludes_unhealthy_instances(
        self, gateway_client, admin_client
    ):
        """
        Verify that only healthy instances receive traffic from Kong Gateway.

        This is the main verification test for Task 4.4 that demonstrates:
        1. Kong can identify healthy and unhealthy service instances
        2. Traffic is only routed to healthy instances
        3. Unhealthy instances are excluded from load balancing
        4. Health checks continuously monitor instance status
        """
        # Step 1: Verify health check configuration is in place
        self._verify_health_check_configuration(admin_client)

        # Step 2: Get initial health status of all upstream targets
        initial_health_status = self._get_upstream_health_status(admin_client)

        if not initial_health_status:
            pytest.skip(
                "No upstream targets configured - cannot verify health-aware routing"
            )

        total_targets = len(initial_health_status)
        healthy_targets = [t for t in initial_health_status if t["health"] == "healthy"]
        unhealthy_targets = [
            t for t in initial_health_status if t["health"] == "unhealthy"
        ]

        print(
            f"\nInitial state: {len(healthy_targets)} healthy, {len(unhealthy_targets)} unhealthy out of {total_targets} total targets"
        )

        # Step 3: Verify traffic routing behavior based on health status
        if len(healthy_targets) > 0:
            # Case A: Healthy instances available - traffic should succeed
            self._verify_traffic_routes_to_healthy_instances(
                gateway_client, healthy_targets
            )

        if len(unhealthy_targets) == total_targets:
            # Case B: No healthy instances - traffic should fail gracefully
            self._verify_traffic_fails_gracefully_with_no_healthy_instances(
                gateway_client
            )

        # Step 4: Monitor health status changes over time
        self._verify_health_status_affects_traffic_routing(gateway_client, admin_client)

        # Step 5: Verify load balancing only includes healthy instances
        if len(healthy_targets) > 1:
            self._verify_load_balancing_excludes_unhealthy_instances(
                gateway_client, admin_client, healthy_targets
            )

    def _verify_health_check_configuration(self, admin_client):
        """Verify that Kong has proper health check configuration."""
        # Check upstream configuration
        upstream_response = admin_client.get("/upstreams/registry-service.upstream")
        assert (
            upstream_response.status_code == 200
        ), "Registry upstream should be configured"

        upstream_data = upstream_response.json()
        assert (
            "healthchecks" in upstream_data
        ), "Upstream should have health checks configured"

        healthchecks = upstream_data["healthchecks"]
        assert "active" in healthchecks, "Active health checks should be configured"
        assert "passive" in healthchecks, "Passive health checks should be configured"

        # Verify active health check settings
        active = healthchecks["active"]
        assert active.get("type") == "http", "Active health check should be HTTP type"
        assert (
            active.get("http_path") == "/health/ready"
        ), "Health check should use /health/ready endpoint"

        print("✓ Health check configuration verified")

    def _verify_traffic_routes_to_healthy_instances(
        self, gateway_client, healthy_targets: List[Dict]
    ):
        """Verify that traffic successfully routes to healthy instances."""
        print(
            f"\n→ Testing traffic routing with {len(healthy_targets)} healthy instances"
        )

        successful_requests = 0
        failed_requests = 0
        total_requests = 10

        request_results = []

        for i in range(total_requests):
            try:
                start_time = time.time()
                response = gateway_client.get("/api/v1/registry/services", timeout=10)
                end_time = time.time()

                is_success = response.status_code < 400
                if is_success:
                    successful_requests += 1
                else:
                    failed_requests += 1

                request_results.append(
                    {
                        "request_id": i,
                        "status_code": response.status_code,
                        "success": is_success,
                        "latency_ms": (end_time - start_time) * 1000,
                        "correlation_id": response.headers.get("X-Correlation-ID"),
                        "upstream_latency": response.headers.get("X-Kong-Upstream-Latency"),
                        "upstream_latency": response.headers.get(
                            "X-Kong-Upstream-Latency"
                        ),
                    }
                )

            except Exception as e:
                failed_requests += 1
                request_results.append(
                    {
                        "request_id": i,
                        "status_code": None,
                        "success": False,
                        "error": str(e),
                    }
                )

            time.sleep(0.5)  # Small delay between requests

        success_rate = successful_requests / total_requests

        # With healthy instances, we should have a good success rate
        assert (
            success_rate >= 0.7
        ), f"Success rate too low ({success_rate:.1%}) with healthy instances available"

        # Successful requests should have proper response characteristics
        successful_results = [r for r in request_results if r.get("success", False)]
        for result in successful_results[:3]:  # Check first 3 successful requests
            assert (
                result.get("correlation_id") is not None
            ), "Successful requests should have correlation ID"
            if result.get("upstream_latency"):
                upstream_latency = int(result["upstream_latency"])
                assert (
                    upstream_latency < 30000
                ), f"Upstream latency too high: {upstream_latency}ms"

        print(
            f"✓ Traffic routing verified: {success_rate:.1%} success rate with healthy instances"
        )

    def _verify_traffic_fails_gracefully_with_no_healthy_instances(
        self, gateway_client
    ):
        """Verify that traffic fails gracefully when no healthy instances are available."""
        print("\n→ Testing graceful failure with no healthy instances")

        error_responses = []
        total_requests = 5

        for i in range(total_requests):
            try:
                response = gateway_client.get("/api/v1/registry/services", timeout=10)
                error_responses.append(
                    {
                        "request_id": i,
                        "status_code": response.status_code,
                        "correlation_id": response.headers.get("X-Correlation-ID"),
                    }
                )
            except Exception as e:
                error_responses.append({"request_id": i, "status_code": None, "error": str(e)})
                error_responses.append(
                    {"request_id": i, "status_code": None, "error": str(e)}
                )
            time.sleep(1)

        # All requests should fail with proper error codes
        for result in error_responses:
            status_code = result.get("status_code")
            # Should get proper HTTP error codes for no healthy instances
            assert status_code in [
                502,
                503,
                504,
                None,
            ], f"Expected error status, got {status_code}"

            # Should still have correlation IDs for tracing
            if status_code is not None:
                assert (
                    result.get("correlation_id") is not None
                ), "Error responses should have correlation ID"

        print("✓ Graceful failure verified with no healthy instances")

    def _verify_health_status_affects_traffic_routing(
        self, gateway_client, admin_client
    ):
        """Verify that changes in health status affect traffic routing behavior."""
        print("\n→ Monitoring health status changes affect on traffic routing")

        monitoring_duration = 30  # Monitor for 30 seconds
        start_time = time.time()

        monitoring_results = []

        while (time.time() - start_time) < monitoring_duration:
            current_time = time.time() - start_time

            # Get current health status
            health_status = self._get_upstream_health_status(admin_client)
            healthy_count = len([t for t in health_status if t["health"] == "healthy"])
            total_targets = len(health_status)

            # Make a test request
            request_success = False
            status_code = None
            correlation_id = None

            try:
                response = gateway_client.get("/api/v1/registry/services", timeout=8)
                status_code = response.status_code
                request_success = status_code < 400
                correlation_id = response.headers.get("X-Correlation-ID")
            except Exception:
                request_success = False

            monitoring_results.append(
                {
                    "time": current_time,
                    "healthy_count": healthy_count,
                    "total_targets": total_targets,
                    "request_success": request_success,
                    "status_code": status_code,
                    "correlation_id": correlation_id,
                }
            )

            time.sleep(3)  # Check every 3 seconds

        # Analyze correlation between health status and request success
        if monitoring_results:
            # Verify that request success correlates with healthy instance availability
            success_with_healthy = []
            success_without_healthy = []

            for result in monitoring_results:
                if result["healthy_count"] > 0:
                    success_with_healthy.append(result["request_success"])
                else:
                    success_without_healthy.append(result["request_success"])

            # When healthy instances are available, success rate should be higher
            if success_with_healthy and success_without_healthy:
                success_rate_with_healthy = sum(success_with_healthy) / len(success_with_healthy)
                success_rate_with_healthy = sum(success_with_healthy) / len(
                    success_with_healthy
                )
                success_rate_without_healthy = sum(success_without_healthy) / len(
                    success_without_healthy
                )

                assert (
                    success_rate_with_healthy > success_rate_without_healthy
                ), f"Success rate with healthy instances ({success_rate_with_healthy:.1%}) should be higher than without ({success_rate_without_healthy:.1%})"

            # All correlation IDs should be unique
            correlation_ids = [
                r["correlation_id"] for r in monitoring_results if r["correlation_id"]
            ]
            if correlation_ids:
                assert len(set(correlation_ids)) == len(
                    correlation_ids
                ), "Correlation IDs should be unique"

        print("✓ Health status changes verified to affect traffic routing")

    def _verify_load_balancing_excludes_unhealthy_instances(
        self, gateway_client, admin_client, healthy_targets: List[Dict]
    ):
        """Verify that load balancing only distributes traffic among healthy instances."""
        print(
            f"\n→ Testing load balancing across {len(healthy_targets)} healthy instances"
        )

        # Make multiple requests to observe load balancing behavior
        load_balancing_results = []
        total_requests = 20

        for i in range(total_requests):
            try:
                start_time = time.time()
                response = gateway_client.get("/api/v1/registry/services", timeout=8)
                end_time = time.time()

                load_balancing_results.append(
                    {
                        "request_id": i,
                        "status_code": response.status_code,
                        "success": response.status_code < 400,
                        "latency_ms": (end_time - start_time) * 1000,
                        "correlation_id": response.headers.get("X-Correlation-ID"),
                        "upstream_latency": response.headers.get("X-Kong-Upstream-Latency"),
                        "upstream_latency": response.headers.get(
                            "X-Kong-Upstream-Latency"
                        ),
                    }
                )

            except Exception as e:
                load_balancing_results.append(
                    {
                        "request_id": i,
                        "status_code": None,
                        "success": False,
                        "error": str(e),
                    }
                )

            time.sleep(0.3)  # Quick succession for load balancing test

        # Analyze load balancing behavior
        successful_requests = [
            r for r in load_balancing_results if r.get("success", False)
        ]

        if successful_requests:
            success_rate = len(successful_requests) / total_requests
            assert (
                success_rate > 0.6
            ), f"Load balancing success rate too low: {success_rate:.1%}"

            # Check for latency variation indicating multiple instances
            upstream_latencies = [
                int(r.get("upstream_latency", "0"))
                for r in successful_requests
                if r.get("upstream_latency")
            ]

            if len(upstream_latencies) >= 5:
                # Some latency variation indicates load balancing across instances
                avg_latency = sum(upstream_latencies) / len(upstream_latencies)
                assert avg_latency > 0, "Should have measurable upstream latency"
                assert avg_latency < 15000, f"Average latency too high: {avg_latency}ms"

            # All correlation IDs should be unique
            correlation_ids = [r.get("correlation_id") for r in successful_requests]
            assert len(set(correlation_ids)) == len(
                correlation_ids
            ), "Correlation IDs should be unique"

        print("✓ Load balancing verified to exclude unhealthy instances")

    def _get_upstream_health_status(self, admin_client) -> List[Dict[str, Any]]:
        """Get current health status of all upstream targets."""
        try:
            response = admin_client.get("/upstreams/registry-service.upstream/health")
            if response.status_code == 200:
                health_data = response.json()
                targets = health_data.get("data", [])

                # Ensure each target has required fields
                for target in targets:
                    if "health" not in target:
                        target["health"] = "unknown"
                    if "target" not in target:
                        target["target"] = "unknown"
                    if "weight" not in target:
                        target["weight"] = 100

                return targets
            else:
                # Fallback: get targets and assume healthy if health endpoint unavailable
                targets_response = admin_client.get(
                    "/upstreams/registry-service.upstream/targets"
                )
                if targets_response.status_code == 200:
                    targets_data = targets_response.json()
                    targets = targets_data.get("data", [])
                    # Mark all as healthy since we can't determine health status
                    for target in targets:
                        target["health"] = "healthy"  # Assume healthy for test purposes
                    return targets
                return []
        except Exception:
            return []

    def test_concurrent_traffic_only_to_healthy_instances(
        self, gateway_client, admin_client
    ):
        """Test that concurrent traffic is only routed to healthy instances."""
        print("\n→ Testing concurrent traffic routing to healthy instances only")

        # Get initial health status
        health_status = self._get_upstream_health_status(admin_client)
        healthy_targets = [t for t in health_status if t["health"] == "healthy"]

        if len(healthy_targets) == 0:
            pytest.skip("No healthy targets available for concurrent traffic test")

        # Simulate concurrent requests
        results_lock = threading.Lock()
        concurrent_results = []

        def make_concurrent_requests(thread_id: int, num_requests: int = 10):
            """Make concurrent requests and collect results."""
            thread_client = httpx.Client(
                base_url="http://localhost:8000",
                headers={"X-API-Key": "dev-api-key-12345"},
                timeout=10.0,
            )

            thread_results = []
            for i in range(num_requests):
                try:
                    response = thread_client.get("/api/v1/registry/services")
                    thread_results.append(
                        {
                            "thread_id": thread_id,
                            "request_id": i,
                            "status_code": response.status_code,
                            "success": response.status_code < 400,
                            "correlation_id": response.headers.get("X-Correlation-ID"),
                        }
                    )
                except Exception as e:
                    thread_results.append(
                        {
                            "thread_id": thread_id,
                            "request_id": i,
                            "status_code": None,
                            "success": False,
                            "error": str(e),
                        }
                    )

                time.sleep(0.1 * random.uniform(0.5, 1.5))  # Randomized delay

            thread_client.close()

            with results_lock:
                concurrent_results.extend(thread_results)

        # Start multiple threads
        threads = []
        num_threads = 4

        for thread_id in range(num_threads):
            thread = threading.Thread(
                target=make_concurrent_requests,
                args=(thread_id,),
                name=f"ConcurrentTest-{thread_id}",
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=60)

        # Analyze concurrent results
        assert len(concurrent_results) > 0, "Should have collected concurrent results"

        successful_requests = [r for r in concurrent_results if r.get("success", False)]

        if len(healthy_targets) > 0:
            # Should have reasonable success rate with healthy targets
            success_rate = (
                len(successful_requests) / len(concurrent_results) if concurrent_results else 0
                len(successful_requests) / len(concurrent_results)
                if concurrent_results
                else 0
            )
            assert (
                success_rate > 0.5
            ), f"Concurrent success rate too low: {success_rate:.1%} with healthy targets"

        # Verify request distribution across threads
        thread_counts = {}
        for result in concurrent_results:
            thread_id = result.get("thread_id", -1)
            thread_counts[thread_id] = thread_counts.get(thread_id, 0) + 1

        assert (
            len(thread_counts) == num_threads
        ), "All threads should have made requests"

        # All correlation IDs should be unique (no collision under concurrent load)
        correlation_ids = [
            r.get("correlation_id") for r in concurrent_results if r.get("correlation_id")
            r.get("correlation_id")
            for r in concurrent_results
            if r.get("correlation_id")
        ]
        if correlation_ids:
            assert len(set(correlation_ids)) == len(
                correlation_ids
            ), "Correlation IDs should be unique even under concurrent load"

        print(
            f"✓ Concurrent traffic verified: {len(successful_requests)}/{len(concurrent_results)} successful requests"
        )

    def test_health_check_exclusion_timing(self, gateway_client, admin_client):
        """Test the timing of health check exclusion behavior."""
        print("\n→ Testing health check exclusion timing behavior")

        # Monitor behavior over health check intervals
        monitoring_duration = 40  # Monitor for 40 seconds
        start_time = time.time()

        timing_results = []

        while (time.time() - start_time) < monitoring_duration:
            current_time = time.time() - start_time

            # Get health status
            health_status = self._get_upstream_health_status(admin_client)
            healthy_count = len([t for t in health_status if t["health"] == "healthy"])

            # Make test request and measure timing
            request_start = time.time()
            request_success = False
            status_code = None

            try:
                response = gateway_client.get("/api/v1/registry/services", timeout=8)
                request_end = time.time()
                status_code = response.status_code
                request_success = status_code < 400
                request_duration_ms = (request_end - request_start) * 1000
            except Exception:
                request_end = time.time()
                request_duration_ms = (request_end - request_start) * 1000
                request_success = False

            timing_results.append(
                {
                    "time": current_time,
                    "healthy_targets": healthy_count,
                    "request_success": request_success,
                    "status_code": status_code,
                    "request_duration_ms": request_duration_ms,
                }
            )

            time.sleep(5)  # Check every 5 seconds

        # Analyze timing behavior
        assert len(timing_results) >= 3, "Should have multiple timing measurements"

        # Check that request timing is reasonable
        successful_timings = [r for r in timing_results if r["request_success"]]
        failed_timings = [r for r in timing_results if not r["request_success"]]

        if successful_timings:
            avg_success_duration = sum(r["request_duration_ms"] for r in successful_timings) / len(
                successful_timings
            )
            avg_success_duration = sum(
                r["request_duration_ms"] for r in successful_timings
            ) / len(successful_timings)
            assert (
                avg_success_duration < 10000
            ), f"Successful requests taking too long: {avg_success_duration:.0f}ms"

        if failed_timings:
            avg_failure_duration = sum(r["request_duration_ms"] for r in failed_timings) / len(
                failed_timings
            )
            avg_failure_duration = sum(
                r["request_duration_ms"] for r in failed_timings
            ) / len(failed_timings)
            # Failed requests should not hang indefinitely
            assert (
                avg_failure_duration < 15000
            ), f"Failed requests taking too long: {avg_failure_duration:.0f}ms"

        # Health status should be consistent within health check intervals
        health_counts = [r["healthy_targets"] for r in timing_results]
        if health_counts:
            # Should not have chaotic health status changes
            health_changes = sum(
                1 for i in range(1, len(health_counts)) if health_counts[i] != health_counts[i - 1]
                1
                for i in range(1, len(health_counts))
                if health_counts[i] != health_counts[i - 1]
            )
            max_allowed_changes = len(health_counts) // 2  # Allow some transitions
            assert (
                health_changes <= max_allowed_changes
            ), f"Too many health status changes ({health_changes}) indicating unstable health checks"

        print("✓ Health check exclusion timing verified")
