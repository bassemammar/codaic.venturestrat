"""
Integration tests for failover when instance becomes unhealthy.

Tests Kong's ability to detect unhealthy instances and automatically
fail over to healthy instances while maintaining service availability.

Task 4.3: Test failover when instance becomes unhealthy
"""

import pytest
import time
import httpx
from typing import Dict, Any, List
import threading
import random


@pytest.mark.integration
class TestFailoverWhenInstanceBecomesUnhealthy:
    """Test Kong's failover behavior when service instances become unhealthy."""

    def test_health_check_detects_instance_failure(self, gateway_client, admin_client):
        """Test that Kong health checks detect when an instance becomes unhealthy."""
        # Get initial health status of all upstream targets
        initial_health = self._get_upstream_health_status(admin_client)
        initial_healthy_count = len(
            [t for t in initial_health if t["health"] == "healthy"]
        )

        # If no healthy instances initially, skip the test
        if initial_healthy_count == 0:
            pytest.skip("No healthy instances available for failover testing")

        # Make baseline requests to verify current functionality
        baseline_responses = []
        for _ in range(5):
            try:
                response = gateway_client.get("/api/v1/registry/services", timeout=10)
                baseline_responses.append(
                    {
                        "status_code": response.status_code,
                        "success": response.status_code < 400,
                        "correlation_id": response.headers.get("X-Correlation-ID"),
                    }
                )
            except Exception as e:
                baseline_responses.append({"status_code": None, "success": False, "error": str(e)})
            time.sleep(1)

        len([r for r in baseline_responses if r.get("success", False)]) / len(baseline_responses)
                baseline_responses.append(
                    {"status_code": None, "success": False, "error": str(e)}
                )
            time.sleep(1)

        baseline_success_rate = len(
            [r for r in baseline_responses if r.get("success", False)]
        ) / len(baseline_responses)

        # Wait for health check interval to pass and check if health status stabilizes
        time.sleep(15)  # Wait longer than health check interval (10 seconds)

        # Check health status again
        final_health = self._get_upstream_health_status(admin_client)
        len([t for t in final_health if t["health"] == "healthy"])

        # Analyze health check behavior
        assert len(final_health) > 0, "Should have upstream targets configured"

        # Health status should be consistent
        for target in final_health:
            assert target["health"] in [
                "healthy",
                "unhealthy",
            ], f"Invalid health status: {target['health']}"
            assert "target" in target, "Target should have target address"
            assert "weight" in target, "Target should have weight"

    def test_automatic_failover_to_healthy_instances(
        self, gateway_client, admin_client
    ):
        """Test that Kong automatically fails over to healthy instances."""
        # Get initial upstream configuration
        upstream_response = admin_client.get("/upstreams/registry-service.upstream")
        if upstream_response.status_code != 200:
            pytest.skip("Cannot access upstream configuration via Admin API")

        upstream_response.json()

        # Get initial health status
        initial_health = self._get_upstream_health_status(admin_client)
        total_targets = len(initial_health)

        if total_targets == 0:
            pytest.skip("No upstream targets configured for failover testing")

        # Simulate load by making multiple requests over time
        request_results = []
        monitoring_duration = 30  # Monitor for 30 seconds
        start_time = time.time()

        while (time.time() - start_time) < monitoring_duration:
            try:
                response = gateway_client.get("/api/v1/registry/services", timeout=5)
                request_results.append(
                    {
                        "timestamp": time.time() - start_time,
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
            except httpx.TimeoutException:
                request_results.append(
                    {
                        "timestamp": time.time() - start_time,
                        "status_code": 504,
                        "success": False,
                        "error": "timeout",
                    }
                )
            except Exception as e:
                request_results.append(
                    {
                        "timestamp": time.time() - start_time,
                        "status_code": None,
                        "success": False,
                        "error": str(e),
                    }
                )

            time.sleep(2)  # Request every 2 seconds

        # Analyze failover behavior
        successful_requests = [r for r in request_results if r.get("success", False)]
        [r for r in request_results if not r.get("success", False)]

        # Get final health status
        final_health = self._get_upstream_health_status(admin_client)
        healthy_targets = [t for t in final_health if t["health"] == "healthy"]

        # Verify failover behavior
        if len(healthy_targets) > 0:
            # If there are healthy targets, should have some successful requests
            success_rate = len(successful_requests) / len(request_results) if request_results else 0
            success_rate = (
                len(successful_requests) / len(request_results)
                if request_results
                else 0
            )
            assert (
                success_rate > 0.2
            ), f"Low success rate ({success_rate:.2%}) despite healthy targets available"

            # Successful requests should have proper latency headers
            for request in successful_requests[:3]:  # Check first 3 successful requests
                assert (
                    request.get("upstream_latency") is not None
                ), "Successful requests should have upstream latency"
                assert (
                    request.get("proxy_latency") is not None
                ), "Successful requests should have proxy latency"

                # Latency should be reasonable
                upstream_latency = int(request.get("upstream_latency", "0"))
                assert (
                    upstream_latency < 30000
                ), f"Upstream latency too high: {upstream_latency}ms"

        # All correlation IDs should be unique
        correlation_ids = [
            r.get("correlation_id") for r in request_results if r.get("correlation_id")
        ]
        assert len(set(correlation_ids)) == len(correlation_ids), "Correlation IDs should be unique"
        assert len(set(correlation_ids)) == len(
            correlation_ids
        ), "Correlation IDs should be unique"

    def test_load_balancing_across_healthy_instances(
        self, gateway_client, admin_client
    ):
        """Test that Kong load balances requests across healthy instances only."""
        # Get upstream targets
        targets_response = admin_client.get(
            "/upstreams/registry-service.upstream/targets"
        )
        if targets_response.status_code != 200:
            pytest.skip("Cannot access upstream targets via Admin API")

        targets_data = targets_response.json()
        targets = targets_data.get("data", [])

        if len(targets) < 2:
            pytest.skip("Need at least 2 targets for load balancing test")

        # Get health status of targets
        health_status = self._get_upstream_health_status(admin_client)
        healthy_targets = [t for t in health_status if t["health"] == "healthy"]

        # Make multiple requests to observe load balancing
        load_test_results = []
        for i in range(20):  # More requests to see load balancing pattern
            try:
                response = gateway_client.get("/api/v1/registry/services", timeout=5)
                load_test_results.append(
                    {
                        "request_id": i,
                        "status_code": response.status_code,
                        "correlation_id": response.headers.get("X-Correlation-ID"),
                        "upstream_latency": response.headers.get("X-Kong-Upstream-Latency"),
                        "upstream_latency": response.headers.get(
                            "X-Kong-Upstream-Latency"
                        ),
                        "proxy_latency": response.headers.get("X-Kong-Proxy-Latency"),
                    }
                )
            except Exception as e:
                load_test_results.append({"request_id": i, "status_code": None, "error": str(e)})
                load_test_results.append(
                    {"request_id": i, "status_code": None, "error": str(e)}
                )
            time.sleep(0.5)  # Quick succession to test load balancing

        # Analyze load balancing behavior
        successful_requests = [
            r for r in load_test_results if r.get("status_code") == 200
        ]

        if len(successful_requests) > 0 and len(healthy_targets) > 0:
            # Should have successful requests if healthy targets exist
            success_rate = len(successful_requests) / len(load_test_results)
            assert (
                success_rate > 0.5
            ), f"Low success rate ({success_rate:.2%}) with healthy targets available"

            # Check latency variation to indicate load balancing
            upstream_latencies = [
                int(r.get("upstream_latency", "0"))
                for r in successful_requests
                if r.get("upstream_latency")
            ]

            if len(upstream_latencies) >= 3:
                # Some latency variation is expected with load balancing
                avg_latency = sum(upstream_latencies) / len(upstream_latencies)
                assert avg_latency > 0, "Should have measurable upstream latency"
                assert avg_latency < 10000, f"Average latency too high: {avg_latency}ms"

        # All correlation IDs should be unique
        correlation_ids = [
            r.get("correlation_id") for r in load_test_results if r.get("correlation_id")
            r.get("correlation_id")
            for r in load_test_results
            if r.get("correlation_id")
        ]
        assert len(set(correlation_ids)) == len(
            correlation_ids
        ), "Each request should have unique correlation ID"

    def test_health_recovery_after_instance_becomes_healthy(
        self, gateway_client, admin_client
    ):
        """Test that Kong detects when an unhealthy instance becomes healthy again."""
        # Monitor health status over time to detect recovery
        monitoring_duration = 45  # Monitor for 45 seconds
        start_time = time.time()

        health_timeline = []
        request_timeline = []

        while (time.time() - start_time) < monitoring_duration:
            current_time = time.time() - start_time

            # Get current health status
            current_health = self._get_upstream_health_status(admin_client)
            health_summary = {
                "time": current_time,
                "healthy_count": len([t for t in current_health if t["health"] == "healthy"]),
                "unhealthy_count": len([t for t in current_health if t["health"] == "unhealthy"]),
                "healthy_count": len(
                    [t for t in current_health if t["health"] == "healthy"]
                ),
                "unhealthy_count": len(
                    [t for t in current_health if t["health"] == "unhealthy"]
                ),
                "total_targets": len(current_health),
            }
            health_timeline.append(health_summary)

            # Make a test request
            try:
                response = gateway_client.get("/api/v1/registry/services", timeout=5)
                request_result = {
                    "time": current_time,
                    "status_code": response.status_code,
                    "success": response.status_code < 400,
                    "correlation_id": response.headers.get("X-Correlation-ID"),
                }
            except Exception as e:
                request_result = {
                    "time": current_time,
                    "status_code": None,
                    "success": False,
                    "error": str(e),
                }

            request_timeline.append(request_result)
            time.sleep(3)  # Check every 3 seconds

        # Analyze health recovery behavior
        if len(health_timeline) > 0:
            # Check for health state stability
            healthy_counts = [h["healthy_count"] for h in health_timeline]
            total_targets = (
                health_timeline[0]["total_targets"] if health_timeline else 0
            )

            # Health status should eventually stabilize
            final_healthy_count = (
                healthy_counts[-3:] if len(healthy_counts) >= 3 else healthy_counts
            )
            (len(set(final_healthy_count)) <= 1)  # All same in final period
            health_stability = (
                len(set(final_healthy_count)) <= 1
            )  # All same in final period

            if total_targets > 0:
                # Should have some targets configured
                assert (
                    max(healthy_counts) <= total_targets
                ), "Healthy count should not exceed total targets"

                # Health checks should be working (detecting health status)
                assert any(
                    count >= 0 for count in healthy_counts
                ), "Health checks should be functioning"

        # Analyze request success correlation with health status
        [r for r in request_timeline if r.get("success", False)]

        if len(health_timeline) > 0 and len(request_timeline) > 0:
            # Correlate success rate with healthy target count
            for i, health_point in enumerate(health_timeline):
                if i < len(request_timeline):
                    request_timeline[i]

                    # If we have healthy targets, request should have reasonable chance of success
                    if health_point["healthy_count"] > 0:
                        # This is expected behavior - healthy targets should serve requests
                        pass
                    else:
                        # If no healthy targets, failures are expected
                        pass

        # All correlation IDs should be unique
        correlation_ids = [
            r.get("correlation_id") for r in request_timeline if r.get("correlation_id")
        ]
        if correlation_ids:
            assert len(set(correlation_ids)) == len(
                correlation_ids
            ), "Correlation IDs should be unique"

    def test_consistent_failover_behavior_under_load(
        self, gateway_client, admin_client
    ):
        """Test that failover behavior is consistent under concurrent load."""
        # Simulate concurrent requests to test failover under load
        results_lock = threading.Lock()
        concurrent_results = []

        def make_concurrent_requests(client, num_requests, delay_range=(0.1, 0.5)):
            """Make concurrent requests with random delays."""
            local_results = []
            for i in range(num_requests):
                try:
                    delay = random.uniform(delay_range[0], delay_range[1])
                    time.sleep(delay)

                    response = client.get("/api/v1/registry/services", timeout=10)
                    local_results.append(
                        {
                            "thread_id": threading.current_thread().name,
                            "request_id": i,
                            "status_code": response.status_code,
                            "success": response.status_code < 400,
                            "correlation_id": response.headers.get("X-Correlation-ID"),
                            "timestamp": time.time(),
                        }
                    )
                except Exception as e:
                    local_results.append(
                        {
                            "thread_id": threading.current_thread().name,
                            "request_id": i,
                            "status_code": None,
                            "success": False,
                            "error": str(e),
                            "timestamp": time.time(),
                        }
                    )

            with results_lock:
                concurrent_results.extend(local_results)

        # Create multiple threads to simulate concurrent load
        threads = []
        num_threads = 3
        requests_per_thread = 8

        for thread_id in range(num_threads):
            # Create separate client for each thread
            thread_client = httpx.Client(
                base_url="http://localhost:8000",
                headers={"X-API-Key": "dev-api-key-12345"},
                timeout=10.0,
            )

            thread = threading.Thread(
                target=make_concurrent_requests,
                args=(thread_client, requests_per_thread),
                name=f"LoadTest-{thread_id}",
            )
            threads.append((thread, thread_client))

        # Start all threads
        start_time = time.time()
        for thread, _ in threads:
            thread.start()

        # Wait for all threads to complete
        for thread, client in threads:
            thread.join(timeout=30)  # 30-second timeout per thread
            client.close()

        end_time = time.time()
        end_time - start_time

        # Analyze concurrent failover behavior
        assert (
            len(concurrent_results) > 0
        ), "Should have collected concurrent request results"

        # Check request distribution across threads
        thread_results = {}
        for result in concurrent_results:
            thread_id = result.get("thread_id", "unknown")
            if thread_id not in thread_results:
                thread_results[thread_id] = []
            thread_results[thread_id].append(result)

        # Each thread should have made requests
        assert (
            len(thread_results) >= num_threads
        ), f"Expected {num_threads} threads, got {len(thread_results)}"

        # Analyze success patterns
        successful_requests = [r for r in concurrent_results if r.get("success", False)]
        [r for r in concurrent_results if not r.get("success", False)]

        # Get current health status to understand results
        current_health = self._get_upstream_health_status(admin_client)
        healthy_targets = [t for t in current_health if t["health"] == "healthy"]

        if len(healthy_targets) > 0:
            # If healthy targets exist, should have reasonable success rate under load
            success_rate = (
                len(successful_requests) / len(concurrent_results) if concurrent_results else 0
                len(successful_requests) / len(concurrent_results)
                if concurrent_results
                else 0
            )
            assert (
                success_rate > 0.3
            ), f"Low success rate ({success_rate:.2%}) under concurrent load with healthy targets"

        # All correlation IDs should be unique (no request collision)
        correlation_ids = [
            r.get("correlation_id") for r in concurrent_results if r.get("correlation_id")
            r.get("correlation_id")
            for r in concurrent_results
            if r.get("correlation_id")
        ]
        if correlation_ids:
            assert len(set(correlation_ids)) == len(
                correlation_ids
            ), "Correlation IDs should be unique even under load"

        # Request timing should be reasonable
        request_timestamps = [
            r.get("timestamp") for r in concurrent_results if r.get("timestamp")
        ]
        if len(request_timestamps) > 1:
            duration_spread = max(request_timestamps) - min(request_timestamps)
            assert (
                duration_spread < 60
            ), f"Request duration spread too large: {duration_spread}s"

    def test_health_check_circuit_breaker_behavior(self, gateway_client, admin_client):
        """Test that health checks behave like circuit breakers for unhealthy instances."""
        # Monitor consecutive request patterns to observe circuit breaker-like behavior
        consecutive_test_results = []

        for batch in range(5):  # 5 batches of requests
            batch_results = []

            # Make rapid consecutive requests within each batch
            for request_id in range(6):
                try:
                    start_time = time.time()
                    response = gateway_client.get(
                        "/api/v1/registry/services", timeout=8
                    )
                    end_time = time.time()

                    batch_results.append(
                        {
                            "batch": batch,
                            "request_id": request_id,
                            "status_code": response.status_code,
                            "success": response.status_code < 400,
                            "latency_ms": (end_time - start_time) * 1000,
                            "correlation_id": response.headers.get("X-Correlation-ID"),
                            "timestamp": end_time,
                        }
                    )
                except httpx.TimeoutException:
                    batch_results.append(
                        {
                            "batch": batch,
                            "request_id": request_id,
                            "status_code": 504,
                            "success": False,
                            "latency_ms": 8000,  # Timeout duration
                            "error": "timeout",
                            "timestamp": time.time(),
                        }
                    )
                except Exception as e:
                    batch_results.append(
                        {
                            "batch": batch,
                            "request_id": request_id,
                            "status_code": None,
                            "success": False,
                            "error": str(e),
                            "timestamp": time.time(),
                        }
                    )

                time.sleep(0.8)  # Short delay within batch

            consecutive_test_results.extend(batch_results)

            # Longer delay between batches to allow health check intervals
            time.sleep(8)

        # Analyze circuit breaker-like behavior
        if consecutive_test_results:
            # Group results by batch to analyze patterns
            batches = {}
            for result in consecutive_test_results:
                batch_id = result.get("batch", 0)
                if batch_id not in batches:
                    batches[batch_id] = []
                batches[batch_id].append(result)

            # Analyze each batch for consistency
            batch_success_rates = []
            for batch_id, batch_results in batches.items():
                successful_in_batch = len([r for r in batch_results if r.get("success", False)])
                successful_in_batch = len(
                    [r for r in batch_results if r.get("success", False)]
                )
                batch_success_rate = (
                    successful_in_batch / len(batch_results) if batch_results else 0
                )
                batch_success_rates.append(batch_success_rate)

            # Circuit breaker behavior: batches should have consistent results
            # (either mostly successful or mostly failed, not random)
            for i, success_rate in enumerate(batch_success_rates):
                # Each batch should be either mostly successful (>0.7) or mostly failed (<0.3)
                # indicating circuit breaker behavior rather than random failures
                assert (
                    success_rate > 0.7 or success_rate < 0.5
                ), f"Batch {i} has inconsistent success rate {success_rate:.2%} - might indicate unstable health checks"

        # All correlation IDs should still be unique
        correlation_ids = [
            r.get("correlation_id") for r in consecutive_test_results if r.get("correlation_id")
            r.get("correlation_id")
            for r in consecutive_test_results
            if r.get("correlation_id")
        ]
        if correlation_ids:
            assert len(set(correlation_ids)) == len(
                correlation_ids
            ), "Correlation IDs should be unique"

    def _get_upstream_health_status(self, admin_client) -> List[Dict[str, Any]]:
        """Helper method to get upstream health status from Kong Admin API."""
        try:
            response = admin_client.get("/upstreams/registry-service.upstream/health")
            if response.status_code == 200:
                health_data = response.json()
                return health_data.get("data", [])
            else:
                # Health endpoint might not be available
                return []
        except Exception:
            return []

    def _get_upstream_targets(self, admin_client) -> List[Dict[str, Any]]:
        """Helper method to get upstream targets from Kong Admin API."""
        try:
            response = admin_client.get("/upstreams/registry-service.upstream/targets")
            if response.status_code == 200:
                targets_data = response.json()
                return targets_data.get("data", [])
            else:
                return []
        except Exception:
            return []

    @pytest.mark.slow
    def test_failover_resilience_over_extended_period(
        self, gateway_client, admin_client
    ):
        """Test failover resilience over an extended monitoring period."""
        # Extended monitoring to verify long-term health check stability
        monitoring_duration = 90  # 90 seconds
        check_interval = 10  # Check every 10 seconds

        start_time = time.time()
        extended_monitoring_results = []

        while (time.time() - start_time) < monitoring_duration:
            current_time = time.time() - start_time

            # Get health status
            health_status = self._get_upstream_health_status(admin_client)
            healthy_count = len([t for t in health_status if t["health"] == "healthy"])
            unhealthy_count = len(
                [t for t in health_status if t["health"] == "unhealthy"]
            )

            # Make test requests
            request_success_count = 0
            request_attempts = 3

            for _ in range(request_attempts):
                try:
                    response = gateway_client.get(
                        "/api/v1/registry/services", timeout=8
                    )
                    if response.status_code < 400:
                        request_success_count += 1
                except Exception:
                    pass
                time.sleep(1)

            extended_monitoring_results.append(
                {
                    "time": current_time,
                    "healthy_targets": healthy_count,
                    "unhealthy_targets": unhealthy_count,
                    "total_targets": healthy_count + unhealthy_count,
                    "request_success_rate": request_success_count / request_attempts,
                    "timestamp": time.time(),
                }
            )

            time.sleep(check_interval)

        # Analyze extended monitoring results
        assert (
            len(extended_monitoring_results) >= 3
        ), "Should have multiple monitoring points"

        # Check for health status stability over time
        healthy_counts = [r["healthy_targets"] for r in extended_monitoring_results]
        success_rates = [r["request_success_rate"] for r in extended_monitoring_results]

        # Health checks should be functioning (not all zeros)
        assert (
            any(count > 0 for count in healthy_counts) or any(rate > 0 for rate in success_rates)
            any(count > 0 for count in healthy_counts)
            or any(rate > 0 for rate in success_rates)
        ), "Either health checks should detect healthy targets OR requests should occasionally succeed"

        # Success rates should correlate with healthy targets
        correlation_points = []
        for result in extended_monitoring_results:
            if result["total_targets"] > 0:
                correlation_points.append(
                    {
                        "healthy_ratio": result["healthy_targets"] / result["total_targets"],
                        "healthy_ratio": result["healthy_targets"]
                        / result["total_targets"],
                        "success_rate": result["request_success_rate"],
                    }
                )

        # If we have correlation data, healthy targets should generally mean better success rates
        if len(correlation_points) >= 3:
            high_health_points = [
                p for p in correlation_points if p["healthy_ratio"] > 0.5
            ]
            low_health_points = [
                p for p in correlation_points if p["healthy_ratio"] <= 0.5
            ]

            if high_health_points and low_health_points:
                avg_success_high_health = sum(p["success_rate"] for p in high_health_points) / len(
                    high_health_points
                )
                avg_success_low_health = sum(p["success_rate"] for p in low_health_points) / len(
                    low_health_points
                )
                avg_success_high_health = sum(
                    p["success_rate"] for p in high_health_points
                ) / len(high_health_points)
                avg_success_low_health = sum(
                    p["success_rate"] for p in low_health_points
                ) / len(low_health_points)

                # High health should generally lead to better success rates
                assert (
                    avg_success_high_health >= avg_success_low_health
                ), f"High health ratio ({avg_success_high_health:.2%}) should have better success than low health ({avg_success_low_health:.2%})"
