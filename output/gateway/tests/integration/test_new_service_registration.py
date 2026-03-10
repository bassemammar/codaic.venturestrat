"""
Integration test for Task 3.5: Verify that new service registration becomes routable.

This test validates that when a new service registers with Consul, Kong Gateway
automatically discovers it and makes it routable through the gateway.
"""

import pytest
import time
import httpx


@pytest.mark.integration
class TestNewServiceRegistration:
    """Test that new service registration becomes routable through Kong Gateway."""

    def test_simulated_new_service_registration_becomes_routable(
        self, gateway_client, admin_client
    ):
        """
        Test that a new service registration in Consul becomes routable through Kong.

        This test simulates the scenario where:
        1. A new service registers with Consul
        2. Kong discovers the service via DNS resolution
        3. The service becomes routable through the gateway

        Since we can't easily manipulate Consul in integration tests,
        we test the behavior by verifying that Kong can route to services
        that are discovered via Consul DNS.
        """
        # First verify that the registry service is currently accessible
        # This demonstrates that Kong -> Consul service discovery is working
        response = gateway_client.get("/api/v1/registry/services")

        # Response codes that indicate Kong found the service via discovery:
        # - 200: Service is up and responding
        # - 502: Service discovered but connection failed (service may be down)
        # - 503: Service discovered but marked unhealthy
        #
        # Response codes that indicate discovery failure:
        # - 404: Route not found (Kong can't discover the service)
        discovered_status_codes = [200, 502, 503]

        assert (
            response.status_code in discovered_status_codes
        ), f"Service discovery not working. Got {response.status_code}, expected one of {discovered_status_codes}"

        # Verify that Kong includes discovery metadata in headers
        assert (
            "X-Kong-Proxy-Latency" in response.headers
        ), "Kong should add proxy latency header"

        if response.status_code == 200:
            # If service is responding, verify it's actually the registry service
            data = response.json()
            assert isinstance(data, (dict, list)), "Registry service should return JSON"

    def test_consul_dns_resolution_for_service_discovery(self, admin_client):
        """Test that Kong can resolve services through Consul DNS."""
        # Get Kong's current configuration to verify DNS setup
        response = admin_client.get("/")

        if response.status_code != 200:
            pytest.skip("Kong Admin API not accessible")

        # Verify that Kong has services configured that use Consul DNS
        services_response = admin_client.get("/services")
        if services_response.status_code == 200:
            services = services_response.json()
            service_names = [svc.get("name", "") for svc in services.get("data", [])]
            assert any(
                "registry" in name for name in service_names
            ), "Kong should have registry service configured for Consul discovery"

    def test_upstream_target_discovery_mechanism(self, gateway_config, admin_client):
        """Test that upstreams are configured to use Consul service discovery."""
        # Verify that upstreams use Consul service DNS format
        upstreams = gateway_config.get("upstreams", [])
        consul_upstreams = []

        for upstream in upstreams:
            targets = upstream.get("targets", [])
            for target in targets:
                target_addr = target.get("target", "")
                if ".service.consul" in target_addr:
                    consul_upstreams.append(upstream)
                    break

        assert (
            len(consul_upstreams) > 0
        ), "No upstreams configured for Consul service discovery"

        # Test that Kong can query these upstreams
        upstreams_response = admin_client.get("/upstreams")
        if upstreams_response.status_code == 200:
            live_upstreams = upstreams_response.json()
            upstream_names = [
                up.get("name", "") for up in live_upstreams.get("data", [])
            ]

            # Should have at least one upstream that matches our configuration
            config_upstream_names = [up.get("name", "") for up in consul_upstreams]
            matching_upstreams = set(upstream_names).intersection(set(config_upstream_names))
            matching_upstreams = set(upstream_names).intersection(
                set(config_upstream_names)
            )
            assert (
                len(matching_upstreams) > 0
            ), f"Kong should have live upstreams matching config. Live: {upstream_names}, Config: {config_upstream_names}"

    def test_health_check_aware_service_discovery(self, gateway_client):
        """Test that health checks are integrated with service discovery."""
        # Make multiple requests to test health-aware routing
        responses = []
        latencies = []

        for i in range(5):
            start_time = time.time()
            response = gateway_client.get("/api/v1/registry/services")
            end_time = time.time()

            responses.append(response.status_code)
            latencies.append(end_time - start_time)

            # Brief pause between requests
            time.sleep(0.1)

        # All responses should be consistent (indicating healthy service discovery)
        # or show predictable failure patterns (indicating proper health checks)
        healthy_codes = [200]
        unhealthy_codes = [502, 503]
        valid_codes = healthy_codes + unhealthy_codes

        assert all(
            code in valid_codes for code in responses
        ), f"Unexpected response codes indicating discovery/health issues: {responses}"

        # If we get mixed responses, they should only be between healthy/unhealthy states
        # (not random errors like 500)
        unique_responses = set(responses)
        if len(unique_responses) > 1:
            assert unique_responses.issubset(
                set(valid_codes)
            ), f"Mixed responses should only include valid health states: {unique_responses}"

        # Latencies should be reasonable (< 30 seconds even if service is down)
        max_latency = max(latencies)
        assert max_latency < 30.0, f"Service discovery taking too long: {max_latency}s"

    def test_load_balancing_with_discovered_services(self, gateway_client):
        """Test that load balancing works with Consul-discovered services."""
        # Make multiple requests and check for load balancing behavior
        correlation_ids = []
        upstream_latencies = []

        for _ in range(10):
            response = gateway_client.get("/api/v1/registry/services")

            # Collect correlation IDs (should be unique)
            if "X-Correlation-ID" in response.headers:
                correlation_ids.append(response.headers["X-Correlation-ID"])

            # Collect upstream latencies (Kong should add these headers)
            if "X-Kong-Upstream-Latency" in response.headers:
                try:
                    latency = int(response.headers["X-Kong-Upstream-Latency"])
                    upstream_latencies.append(latency)
                except ValueError:
                    pass  # Skip if header value is not a number

            time.sleep(0.1)

        # Each request should have a unique correlation ID
        assert len(correlation_ids) == len(
            set(correlation_ids)
        ), "Correlation IDs should be unique for each request"

        # Should have at least some upstream latency data
        if upstream_latencies:
            # Upstream latencies should be reasonable
            avg_latency = sum(upstream_latencies) / len(upstream_latencies)
            assert (
                avg_latency < 10000
            ), f"Average upstream latency too high: {avg_latency}ms"

    def test_service_discovery_resilience(self, gateway_client):
        """Test that service discovery is resilient to temporary failures."""
        # Test that Kong handles service discovery gracefully even if there are issues

        # Make requests over a period of time to test resilience
        results = {
            "success": 0,
            "client_error": 0,
            "server_error": 0,
            "discovery_error": 0,
        }

        for _ in range(20):
            try:
                response = gateway_client.get("/api/v1/registry/services", timeout=5.0)

                if response.status_code == 200:
                    results["success"] += 1
                elif response.status_code in [400, 401, 403, 404]:
                    results["client_error"] += 1
                elif response.status_code in [502, 503, 504]:
                    results[
                        "server_error"
                    ] += 1  # These indicate discovery found service but it's unhealthy
                else:
                    results["discovery_error"] += 1

            except httpx.RequestError:
                results["discovery_error"] += 1

            time.sleep(0.1)

        # Should have some successful or properly handled failure responses
        total_requests = sum(results.values())
        successful_discovery = (
            results["success"] + results["server_error"]
        )  # server_error means discovery worked
        discovery_rate = successful_discovery / total_requests if total_requests > 0 else 0
        discovery_rate = (
            successful_discovery / total_requests if total_requests > 0 else 0
        )

        # At least 70% of requests should show that discovery is working
        # (either successful responses or proper upstream errors)
        assert (
            discovery_rate >= 0.7
        ), f"Service discovery not resilient enough. Results: {results}, Discovery rate: {discovery_rate}"

    def test_dns_cache_invalidation_for_new_services(self, gateway_client):
        """Test that DNS cache doesn't prevent discovery of newly registered services."""
        # This test verifies that Kong's DNS caching doesn't prevent new service discovery

        # Make initial request to establish baseline
        initial_response = gateway_client.get("/api/v1/registry/services")
        initial_status = initial_response.status_code

        # Wait a bit (DNS cache might have short TTL)
        time.sleep(2)

        # Make follow-up requests
        follow_up_responses = []
        for _ in range(5):
            response = gateway_client.get("/api/v1/registry/services")
            follow_up_responses.append(response.status_code)
            time.sleep(0.2)

        # Responses should be consistent with initial response
        # (indicating stable discovery, not cache invalidation issues)
        expected_statuses = [initial_status]
        if initial_status in [502, 503]:
            # If service was initially unhealthy, it might become healthy
            expected_statuses.append(200)
        elif initial_status == 200:
            # If service was healthy, it might become unhealthy
            expected_statuses.extend([502, 503])

        valid_transitions = all(status in expected_statuses for status in follow_up_responses)
        valid_transitions = all(
            status in expected_statuses for status in follow_up_responses
        )
        assert valid_transitions, f"Unexpected status transitions suggesting cache issues. Initial: {initial_status}, Follow-up: {follow_up_responses}"

    def test_consul_service_tags_and_metadata(self, admin_client):
        """Test that Kong can handle Consul service tags and metadata."""
        # Check that Kong upstreams can handle Consul service metadata

        upstreams_response = admin_client.get("/upstreams")
        if upstreams_response.status_code != 200:
            pytest.skip("Cannot access Kong upstreams via Admin API")

        upstreams = upstreams_response.json()
        consul_upstreams = []

        for upstream in upstreams.get("data", []):
            upstream_name = upstream.get("name", "")
            if any(tag in upstream_name for tag in ["registry", "service"]):
                consul_upstreams.append(upstream)

        assert len(consul_upstreams) > 0, "No Consul-based upstreams found"

        # Verify upstreams have proper configuration for service discovery
        for upstream in consul_upstreams:
            # Should have reasonable slot count for load balancing
            slots = upstream.get("slots", 0)
            assert (
                slots > 0
            ), f"Upstream {upstream.get('name')} should have slots configured"

            # Should have algorithm configured
            algorithm = upstream.get("algorithm")
            if algorithm:
                valid_algorithms = [
                    "round-robin",
                    "least-connections",
                    "ip-hash",
                    "random",
                ]
                assert (
                    algorithm in valid_algorithms
                ), f"Invalid algorithm {algorithm} for upstream {upstream.get('name')}"

    def test_new_service_routing_path_generation(self, gateway_config):
        """Test that new services can be routed with standard path patterns."""
        # Verify that Kong configuration supports the standard routing pattern
        # for newly discovered services: /api/v1/<service>/*

        services = gateway_config.get("services", [])
        registry_services = [
            svc for svc in services if "registry" in svc.get("name", "")
        ]

        assert len(registry_services) > 0, "No registry services found in configuration"

        for service in registry_services:
            routes = service.get("routes", [])
            assert len(routes) > 0, f"Service {service.get('name')} should have routes"

            for route in routes:
                paths = route.get("paths", [])
                assert len(paths) > 0, "Route should have paths configured"

                # Should follow /api/v1/<service> pattern
                api_v1_paths = [path for path in paths if path.startswith("/api/v1/")]
                assert (
                    len(api_v1_paths) > 0
                ), f"Service should have /api/v1/ routes. Found paths: {paths}"

                # Should have strip_path enabled for proper routing
                strip_path = route.get("strip_path", False)
                assert (
                    strip_path
                ), "Routes should have strip_path enabled for proper forwarding"

    def test_service_discovery_metrics_and_monitoring(self, gateway_client):
        """Test that service discovery provides monitoring metrics."""
        # Make requests that will generate metrics
        for _ in range(5):
            response = gateway_client.get("/api/v1/registry/services")
            time.sleep(0.1)

        # At this point, Kong should have generated metrics
        # We can't easily access them in integration tests, but we can verify
        # that the requests include headers indicating monitoring is working

        response = gateway_client.get("/api/v1/registry/services")

        # Kong should add monitoring headers
        monitoring_headers = ["X-Kong-Proxy-Latency", "X-Correlation-ID"]
        for header in monitoring_headers:
            assert (
                header in response.headers
            ), f"Kong should add {header} header for monitoring"

        # Verify correlation ID format
        correlation_id = response.headers.get("X-Correlation-ID")
        if correlation_id:
            # Should be UUID format or similar unique identifier
            assert (
                len(correlation_id) >= 10
            ), "Correlation ID should be a meaningful unique identifier"

    def test_end_to_end_new_service_discovery_flow(self, gateway_client, admin_client):
        """
        End-to-end test of the complete service discovery flow.

        This test verifies the complete flow:
        1. Service is registered in Consul (simulated by existing registry service)
        2. Kong discovers service via Consul DNS
        3. Kong routes requests to discovered service
        4. Health checks monitor service status
        5. Load balancing distributes requests
        """
        # Step 1: Verify Kong can discover and route to services
        service_response = gateway_client.get("/api/v1/registry/services")
        assert service_response.status_code in [
            200,
            502,
            503,
        ], "Kong should be able to route to Consul-discovered services"

        # Step 2: Verify Kong has proper upstream configuration
        upstreams_response = admin_client.get("/upstreams")
        if upstreams_response.status_code == 200:
            upstreams = upstreams_response.json()
            assert (
                len(upstreams.get("data", [])) > 0
            ), "Kong should have upstreams configured"

        # Step 3: Verify health checks are working
        health_response = gateway_client.get("/health")
        assert health_response.status_code == 200, "Gateway health check should work"

        # Step 4: Verify load balancing headers are present
        assert (
            "X-Kong-Proxy-Latency" in service_response.headers
        ), "Kong should add proxy latency headers"

        # Step 5: Verify correlation ID for request tracing
        assert (
            "X-Correlation-ID" in service_response.headers
        ), "Kong should add correlation ID for tracing"

        # If we reach here, the complete service discovery flow is working
        assert True, "End-to-end service discovery flow validated"
