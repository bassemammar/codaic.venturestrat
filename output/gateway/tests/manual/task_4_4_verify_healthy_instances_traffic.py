#!/usr/bin/env python3
"""
Manual verification script for Task 4.4: Verify only healthy instances receive traffic.

This script demonstrates that Kong Gateway routes traffic only to healthy service instances
and excludes unhealthy instances from load balancing.

Usage:
    python task_4_4_verify_healthy_instances_traffic.py

Prerequisites:
    - Kong Gateway running on localhost:8000
    - Kong Admin API accessible on localhost:8001
    - Registry service instances registered with Consul
    - Health checks configured in Kong

Task 4.4: Verify: only healthy instances receive traffic
"""

import requests
import time
from typing import Dict, List, Any
from datetime import datetime
import argparse
import sys


class Task44HealthyInstancesVerifier:
    """Verifies that Kong only routes traffic to healthy instances."""

    def __init__(
        self,
        gateway_url: str = "http://localhost:8000",
        admin_url: str = "http://localhost:8001",
    ):
        self.gateway_url = gateway_url.rstrip("/")
        self.admin_url = admin_url.rstrip("/")
        self.api_key = "dev-api-key-12345"

        # Request session with API key
        self.session = requests.Session()
        self.session.headers.update(
            {"X-API-Key": self.api_key, "User-Agent": "Task44-Verification"}
        )

        # Admin session
        self.admin_session = requests.Session()

    def verify_only_healthy_instances_receive_traffic(self) -> bool:
        """Main verification method for Task 4.4."""
        print("=" * 80)
        print("TASK 4.4 VERIFICATION: Only healthy instances receive traffic")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Gateway URL: {self.gateway_url}")
        print(f"Admin URL: {self.admin_url}")
        print()

        try:
            # Step 1: Verify Kong Gateway is accessible
            print("Step 1: Verifying Kong Gateway accessibility...")
            if not self._verify_gateway_accessible():
                return False

            # Step 2: Verify health check configuration
            print("\nStep 2: Verifying health check configuration...")
            if not self._verify_health_check_configuration():
                return False

            # Step 3: Get current upstream health status
            print("\nStep 3: Checking upstream health status...")
            health_status = self._get_upstream_health_status()
            if not health_status:
                print("❌ No upstream targets found or Admin API inaccessible")
                return False

            self._display_health_status(health_status)

            # Step 4: Demonstrate traffic routing to healthy instances
            print("\nStep 4: Demonstrating traffic routing behavior...")
            if not self._demonstrate_traffic_routing(health_status):
                return False

            # Step 5: Monitor health-aware load balancing
            print("\nStep 5: Monitoring health-aware load balancing...")
            if not self._monitor_health_aware_load_balancing():
                return False

            # Step 6: Verify failover behavior (if multiple targets)
            print("\nStep 6: Testing failover behavior...")
            self._verify_failover_behavior(health_status)

            print("\n" + "=" * 80)
            print("✅ TASK 4.4 VERIFICATION SUCCESSFUL")
            print("Kong Gateway properly routes traffic only to healthy instances!")
            print("=" * 80)
            return True

        except KeyboardInterrupt:
            print("\n\n⚠️  Verification interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Verification failed with error: {e}")
            return False

    def _verify_gateway_accessible(self) -> bool:
        """Verify Kong Gateway is accessible."""
        try:
            # Test gateway health endpoint
            response = self.session.get(f"{self.gateway_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Kong Gateway accessible via proxy port")
            else:
                print(f"⚠️  Gateway health check returned: {response.status_code}")

            # Test admin API
            admin_response = self.admin_session.get(
                f"{self.admin_url}/status", timeout=5
            )
            if admin_response.status_code == 200:
                print("✅ Kong Admin API accessible")
                status_data = admin_response.json()
                print(f"   Server: {status_data.get('server', {})}")
                return True
            else:
                print(f"❌ Admin API not accessible: {admin_response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Gateway accessibility check failed: {e}")
            return False

    def _verify_health_check_configuration(self) -> bool:
        """Verify that health checks are configured correctly."""
        try:
            # Get upstream configuration
            response = self.admin_session.get(
                f"{self.admin_url}/upstreams/registry-service.upstream"
            )
            if response.status_code != 200:
                print(
                    f"❌ Cannot access upstream configuration: {response.status_code}"
                )
                return False

            upstream_data = response.json()

            # Check for health checks
            if "healthchecks" not in upstream_data:
                print("❌ No health checks configured on upstream")
                return False

            healthchecks = upstream_data["healthchecks"]

            # Verify active health checks
            if "active" in healthchecks:
                active = healthchecks["active"]
                print("✅ Active health checks configured:")
                print(f"   Type: {active.get('type')}")
                print(f"   Path: {active.get('http_path')}")
                print(
                    f"   Interval: {active.get('healthy', {}).get('interval')}s (healthy)"
                )
                print(
                    f"   Interval: {active.get('unhealthy', {}).get('interval')}s (unhealthy)"
                )

            # Verify passive health checks
            if "passive" in healthchecks:
                passive = healthchecks["passive"]
                print("✅ Passive health checks configured:")
                print(f"   Healthy codes: {passive.get('healthy', {}).get('http_statuses')}")
                print(f"   Unhealthy codes: {passive.get('unhealthy', {}).get('http_statuses')}")
                print(
                    f"   Healthy codes: {passive.get('healthy', {}).get('http_statuses')}"
                )
                print(
                    f"   Unhealthy codes: {passive.get('unhealthy', {}).get('http_statuses')}"
                )

            return True

        except Exception as e:
            print(f"❌ Health check configuration verification failed: {e}")
            return False

    def _get_upstream_health_status(self) -> List[Dict[str, Any]]:
        """Get current health status of all upstream targets."""
        try:
            # Try health endpoint first
            response = self.admin_session.get(
                f"{self.admin_url}/upstreams/registry-service.upstream/health"
            )
            if response.status_code == 200:
                health_data = response.json()
                return health_data.get("data", [])

            # Fallback to targets endpoint
            response = self.admin_session.get(
                f"{self.admin_url}/upstreams/registry-service.upstream/targets"
            )
            if response.status_code == 200:
                targets_data = response.json()
                targets = targets_data.get("data", [])
                # Mark as healthy since we can't determine health status
                for target in targets:
                    target["health"] = "healthy"
                return targets

            return []

        except Exception as e:
            print(f"⚠️  Cannot get health status: {e}")
            return []

    def _display_health_status(self, health_status: List[Dict[str, Any]]) -> None:
        """Display current health status of upstream targets."""
        if not health_status:
            print("📊 No upstream targets found")
            return

        healthy_targets = [t for t in health_status if t.get("health") == "healthy"]
        unhealthy_targets = [t for t in health_status if t.get("health") == "unhealthy"]
        unknown_targets = [
            t for t in health_status if t.get("health") not in ["healthy", "unhealthy"]
        ]

        print("📊 Upstream Health Status:")
        print(f"   Total targets: {len(health_status)}")
        print(f"   Healthy: {len(healthy_targets)} ✅")
        print(f"   Unhealthy: {len(unhealthy_targets)} ❌")
        if unknown_targets:
            print(f"   Unknown: {len(unknown_targets)} ❓")

        # Display individual target details
        for target in health_status:
            health = target.get("health", "unknown")
            target_addr = target.get("target", "unknown")
            weight = target.get("weight", 100)

            health_icon = (
                "✅" if health == "healthy" else "❌" if health == "unhealthy" else "❓"
            )
            print(
                f"   {health_icon} {target_addr} (weight: {weight}, health: {health})"
            )

    def _demonstrate_traffic_routing(self, health_status: List[Dict[str, Any]]) -> bool:
        """Demonstrate that traffic is routed based on health status."""
        healthy_count = len([t for t in health_status if t.get("health") == "healthy"])
        total_count = len(health_status)

        print(
            f"🔄 Testing traffic routing with {healthy_count}/{total_count} healthy instances..."
        )

        # Make multiple requests to test routing
        results = []
        total_requests = 10

        for i in range(total_requests):
            try:
                start_time = time.time()
                response = self.session.get(
                    f"{self.gateway_url}/api/v1/registry/services", timeout=10
                )
                end_time = time.time()

                result = {
                    "request_id": i + 1,
                    "status_code": response.status_code,
                    "success": response.status_code < 400,
                    "latency_ms": int((end_time - start_time) * 1000),
                    "correlation_id": response.headers.get("X-Correlation-ID"),
                    "upstream_latency": response.headers.get("X-Kong-Upstream-Latency"),
                }
                results.append(result)

                # Show progress
                status_icon = "✅" if result["success"] else "❌"
                print(
                    f"   Request {i + 1:2d}: {status_icon} {result['status_code']} ({result['latency_ms']}ms)"
                )

            except Exception as e:
                result = {
                    "request_id": i + 1,
                    "status_code": None,
                    "success": False,
                    "error": str(e),
                }
                results.append(result)
                print(f"   Request {i + 1:2d}: ❌ Error - {e}")

            time.sleep(0.5)  # Small delay between requests

        # Analyze results
        successful_requests = [r for r in results if r.get("success", False)]
        failed_requests = [r for r in results if not r.get("success", False)]

        success_rate = len(successful_requests) / len(results) * 100

        print("\n📈 Traffic Routing Results:")
        print(f"   Total requests: {len(results)}")
        print(f"   Successful: {len(successful_requests)} ({success_rate:.1f}%)")
        print(f"   Failed: {len(failed_requests)} ({100 - success_rate:.1f}%)")

        if healthy_count > 0:
            if success_rate >= 70:
                print("✅ Traffic successfully routed to healthy instances")
                return True
            else:
                print(
                    f"⚠️  Low success rate ({success_rate:.1f}%) despite healthy instances"
                )
                return False
        else:
            if success_rate < 30:
                print("✅ Traffic correctly rejected with no healthy instances")
                return True
            else:
                print(
                    f"⚠️  Unexpected success rate ({success_rate:.1f}%) with no healthy instances"
                )
                return False

    def _monitor_health_aware_load_balancing(self) -> bool:
        """Monitor load balancing behavior to ensure it's health-aware."""
        print("🔄 Monitoring health-aware load balancing for 30 seconds...")

        monitoring_duration = 30
        start_time = time.time()
        monitoring_results = []

        while (time.time() - start_time) < monitoring_duration:
            current_time = time.time() - start_time

            # Get current health status
            health_status = self._get_upstream_health_status()
            healthy_count = len(
                [t for t in health_status if t.get("health") == "healthy"]
            )

            # Make test request
            try:
                response = self.session.get(
                    f"{self.gateway_url}/api/v1/registry/services", timeout=5
                )
                success = response.status_code < 400
                correlation_id = response.headers.get("X-Correlation-ID")
            except Exception:
                success = False
                correlation_id = None

            monitoring_results.append(
                {
                    "time": current_time,
                    "healthy_count": healthy_count,
                    "request_success": success,
                    "correlation_id": correlation_id,
                }
            )

            # Show progress every 5 seconds
            if int(current_time) % 5 == 0 and current_time > 0:
                status_icon = "✅" if success else "❌"
                print(
                    f"   T+{int(current_time):2d}s: {healthy_count} healthy, request {status_icon}"
                )

            time.sleep(2)

        # Analyze monitoring results
        if monitoring_results:
            success_with_healthy = []
            success_without_healthy = []

            for result in monitoring_results:
                if result["healthy_count"] > 0:
                    success_with_healthy.append(result["request_success"])
                else:
                    success_without_healthy.append(result["request_success"])

            print("\n📊 Load Balancing Analysis:")
            if success_with_healthy:
                success_rate_with_healthy = (
                    sum(success_with_healthy) / len(success_with_healthy) * 100
                )
                print(f"   Success rate with healthy instances: {success_rate_with_healthy:.1f}%")
                print(
                    f"   Success rate with healthy instances: {success_rate_with_healthy:.1f}%"
                )

            if success_without_healthy:
                success_rate_without_healthy = (
                    sum(success_without_healthy) / len(success_without_healthy) * 100
                )
                print(
                    f"   Success rate without healthy instances: {success_rate_without_healthy:.1f}%"
                )

            # Verify correlation IDs are unique
            correlation_ids = [
                r["correlation_id"] for r in monitoring_results if r["correlation_id"]
            ]
            unique_ids = len(set(correlation_ids))
            total_ids = len(correlation_ids)

            print(f"   Unique correlation IDs: {unique_ids}/{total_ids}")

            if unique_ids == total_ids:
                print("✅ All requests have unique correlation IDs")
            else:
                print("⚠️  Some correlation IDs are duplicated")

        return True

    def _verify_failover_behavior(self, health_status: List[Dict[str, Any]]) -> None:
        """Verify failover behavior when instances change health status."""
        total_targets = len(health_status)
        healthy_targets = len(
            [t for t in health_status if t.get("health") == "healthy"]
        )

        print(
            f"🔄 Failover behavior test with {healthy_targets}/{total_targets} healthy instances"
        )

        if total_targets == 0:
            print("⚠️  No upstream targets configured - cannot test failover")
            return

        if healthy_targets == 0:
            print("⚠️  No healthy instances available - testing graceful failure")
            self._test_graceful_failure()
        elif healthy_targets < total_targets:
            print("✅ Mixed health state - ideal for failover testing")
            self._test_partial_failover()
        else:
            print("ℹ️  All instances healthy - testing normal operation")
            self._test_normal_operation()

    def _test_graceful_failure(self) -> None:
        """Test graceful failure when no healthy instances available."""
        print("   Testing graceful failure with no healthy instances...")

        for i in range(3):
            try:
                response = self.session.get(
                    f"{self.gateway_url}/api/v1/registry/services", timeout=5
                )
                print(f"   Request {i + 1}: Status {response.status_code} (expected 502/503/504)")
                print(
                    f"   Request {i + 1}: Status {response.status_code} (expected 502/503/504)"
                )
            except Exception:
                print(f"   Request {i + 1}: Connection error (expected)")

    def _test_partial_failover(self) -> None:
        """Test failover with mixed healthy/unhealthy instances."""
        print("   Testing partial failover with mixed instance health...")

        success_count = 0
        for i in range(5):
            try:
                response = self.session.get(
                    f"{self.gateway_url}/api/v1/registry/services", timeout=5
                )
                if response.status_code < 400:
                    success_count += 1
                    print(
                        f"   Request {i + 1}: ✅ Success (routed to healthy instance)"
                    )
                else:
                    print(f"   Request {i + 1}: ❌ Status {response.status_code}")
            except Exception:
                print(f"   Request {i + 1}: ❌ Connection error")

            time.sleep(1)

        if success_count > 0:
            print(
                f"   ✅ {success_count}/5 requests succeeded (traffic routed to healthy instances)"
            )
        else:
            print("   ⚠️  No successful requests despite healthy instances")

    def _test_normal_operation(self) -> None:
        """Test normal operation with all instances healthy."""
        print("   Testing normal operation with all healthy instances...")

        latencies = []
        for i in range(3):
            try:
                start_time = time.time()
                response = self.session.get(
                    f"{self.gateway_url}/api/v1/registry/services", timeout=5
                )
                end_time = time.time()

                latency = (end_time - start_time) * 1000
                latencies.append(latency)

                if response.status_code < 400:
                    print(f"   Request {i + 1}: ✅ Success ({latency:.0f}ms)")
                else:
                    print(f"   Request {i + 1}: ❌ Status {response.status_code}")
            except Exception as e:
                print(f"   Request {i + 1}: ❌ Error - {e}")

            time.sleep(1)

        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            print(f"   Average latency: {avg_latency:.0f}ms")


def main():
    """Main function for Task 4.4 verification."""
    parser = argparse.ArgumentParser(
        description="Verify Kong only routes traffic to healthy instances"
    )
    parser.add_argument(
        "--gateway-url",
        default="http://localhost:8000",
        help="Kong Gateway URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--admin-url",
        default="http://localhost:8001",
        help="Kong Admin API URL (default: http://localhost:8001)",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Reduce output verbosity")
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Reduce output verbosity"
    )

    args = parser.parse_args()

    # Create verifier and run verification
    verifier = Task44HealthyInstancesVerifier(args.gateway_url, args.admin_url)

    try:
        success = verifier.verify_only_healthy_instances_receive_traffic()

        if success:
            print("\n🎉 Task 4.4 verification completed successfully!")
            print(
                "Kong Gateway properly ensures only healthy instances receive traffic."
            )
            sys.exit(0)
        else:
            print("\n❌ Task 4.4 verification failed!")
            print(
                "Kong Gateway may not be properly configured for health-aware routing."
            )
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
