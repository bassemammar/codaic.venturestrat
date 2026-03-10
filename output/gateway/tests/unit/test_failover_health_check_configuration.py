"""
Unit tests for failover health check configuration.

Tests that the Kong configuration properly supports automatic failover
when instances become unhealthy.

Task 4.3: Test failover when instance becomes unhealthy - Unit test component
"""

import pytest


@pytest.mark.unit
class TestFailoverHealthCheckConfiguration:
    """Test that Kong configuration supports proper failover behavior."""

    def test_upstream_has_health_checks_for_failover(self, gateway_config):
        """Test that upstream is configured with health checks for failover detection."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        assert registry_upstream is not None, "registry-service.upstream not found"
        assert (
            "healthchecks" in registry_upstream
        ), "Health checks required for failover"

        healthchecks = registry_upstream["healthchecks"]
        assert (
            "active" in healthchecks
        ), "Active health checks required for failover detection"
        assert (
            "passive" in healthchecks
        ), "Passive health checks required for failover detection"

    def test_active_health_checks_support_failover(self, gateway_config):
        """Test that active health checks are configured to support failover."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        active = registry_upstream["healthchecks"]["active"]

        # Health check configuration for failover
        assert active["type"] == "http", "HTTP health checks required for proper failover detection"
        assert (
            active["type"] == "http"
        ), "HTTP health checks required for proper failover detection"
        assert (
            active["http_path"] == "/health/ready"
        ), "Health check should use proper health endpoint"

        # Timeout configuration for responsiveness
        assert "timeout" in active, "Timeout required for timely failover detection"
        timeout = active["timeout"]
        assert (
            1 <= timeout <= 10
        ), f"Health check timeout should be reasonable for failover: {timeout}s"

        # Concurrency for faster detection
        assert (
            "concurrency" in active
        ), "Concurrency required for parallel health checks"
        concurrency = active["concurrency"]
        assert (
            concurrency >= 1
        ), f"Health check concurrency should be at least 1: {concurrency}"

        # Healthy thresholds for recovery
        healthy = active["healthy"]
        assert "interval" in healthy, "Healthy check interval required"
        assert "successes" in healthy, "Success threshold required for marking healthy"

        healthy_interval = healthy["interval"]
        healthy_successes = healthy["successes"]

        assert (
            5 <= healthy_interval <= 60
        ), f"Healthy check interval should be reasonable: {healthy_interval}s"
        assert (
            1 <= healthy_successes <= 10
        ), f"Success threshold should be reasonable: {healthy_successes}"

        # Unhealthy thresholds for failure detection
        unhealthy = active["unhealthy"]
        assert "interval" in unhealthy, "Unhealthy check interval required"
        assert "http_failures" in unhealthy, "HTTP failure threshold required"
        assert "timeouts" in unhealthy, "Timeout failure threshold required"
        assert "tcp_failures" in unhealthy, "TCP failure threshold required"

        unhealthy_interval = unhealthy["interval"]
        http_failures = unhealthy["http_failures"]
        timeout_failures = unhealthy["timeouts"]
        tcp_failures = unhealthy["tcp_failures"]

        assert (
            5 <= unhealthy_interval <= 60
        ), f"Unhealthy check interval should be reasonable: {unhealthy_interval}s"
        assert (
            1 <= http_failures <= 10
        ), f"HTTP failure threshold should be reasonable: {http_failures}"
        assert (
            1 <= timeout_failures <= 10
        ), f"Timeout failure threshold should be reasonable: {timeout_failures}"
        assert (
            1 <= tcp_failures <= 10
        ), f"TCP failure threshold should be reasonable: {tcp_failures}"

    def test_passive_health_checks_support_failover(self, gateway_config):
        """Test that passive health checks are configured to support failover."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        passive = registry_upstream["healthchecks"]["passive"]

        # Passive health check type
        assert (
            passive["type"] == "http"
        ), "HTTP passive health checks required for proper failover"

        # Healthy status codes for recovery detection
        healthy = passive["healthy"]
        assert "http_statuses" in healthy, "Healthy HTTP status codes required"
        assert (
            "successes" in healthy
        ), "Success threshold required for passive health recovery"

        healthy_statuses = healthy["http_statuses"]
        healthy_successes = healthy["successes"]

        # Should include success status codes
        assert 200 in healthy_statuses, "200 OK should be considered healthy"
        assert 201 in healthy_statuses, "201 Created should be considered healthy"
        assert 202 in healthy_statuses, "202 Accepted should be considered healthy"

        # Should include redirect status codes
        assert 301 in healthy_statuses, "301 should be considered healthy"
        assert 302 in healthy_statuses, "302 should be considered healthy"

        assert (
            1 <= healthy_successes <= 10
        ), f"Healthy success threshold should be reasonable: {healthy_successes}"

        # Unhealthy status codes for failure detection
        unhealthy = passive["unhealthy"]
        assert "http_statuses" in unhealthy, "Unhealthy HTTP status codes required"
        assert "tcp_failures" in unhealthy, "TCP failure threshold required"
        assert "timeouts" in unhealthy, "Timeout threshold required"
        assert "http_failures" in unhealthy, "HTTP failure threshold required"

        unhealthy_statuses = unhealthy["http_statuses"]
        tcp_failures = unhealthy["tcp_failures"]
        timeouts = unhealthy["timeouts"]
        http_failures = unhealthy["http_failures"]

        # Should include error status codes that indicate failure
        assert (
            500 in unhealthy_statuses
        ), "500 Internal Server Error should trigger failover"
        assert 502 in unhealthy_statuses, "502 Bad Gateway should trigger failover"
        assert (
            503 in unhealthy_statuses
        ), "503 Service Unavailable should trigger failover"
        assert 504 in unhealthy_statuses, "504 Gateway Timeout should trigger failover"

        # Thresholds should be reasonable
        assert (
            1 <= tcp_failures <= 10
        ), f"TCP failure threshold should be reasonable: {tcp_failures}"
        assert 1 <= timeouts <= 10, f"Timeout threshold should be reasonable: {timeouts}"
        assert (
            1 <= timeouts <= 10
        ), f"Timeout threshold should be reasonable: {timeouts}"
        assert (
            1 <= http_failures <= 10
        ), f"HTTP failure threshold should be reasonable: {http_failures}"

    def test_upstream_load_balancing_algorithm_supports_failover(self, gateway_config):
        """Test that load balancing algorithm supports failover."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        # Load balancing algorithm
        algorithm = registry_upstream.get("algorithm", "round-robin")
        supported_algorithms = [
            "round-robin",
            "least-connections",
            "consistent-hashing",
            "hash",
        ]
        assert (
            algorithm in supported_algorithms
        ), f"Load balancing algorithm should support failover: {algorithm}"

        # Hash configuration (if using hash-based algorithms)
        if algorithm in ["consistent-hashing", "hash"]:
            hash_on = registry_upstream.get("hash_on", "none")
            hash_fallback = registry_upstream.get("hash_fallback", "none")

            # Hash fallback should be configured for failover scenarios
            if hash_on != "none":
                assert (
                    hash_fallback != "none" or hash_on == "none"
                ), "Hash fallback should be configured when using hash-based load balancing"

        # Slots configuration for consistent hashing
        if "slots" in registry_upstream:
            slots = registry_upstream["slots"]
            assert (
                slots >= 100
            ), f"Should have sufficient slots for good distribution: {slots}"

    def test_upstream_targets_configured_for_failover(self, gateway_config):
        """Test that upstream targets are configured to support failover."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        # Should have targets configured
        assert "targets" in registry_upstream, "Upstream targets required for failover"
        targets = registry_upstream["targets"]

        assert len(targets) > 0, "Should have at least one target for service"

        for i, target in enumerate(targets):
            assert "target" in target, f"Target {i} should have target address"
            assert (
                "weight" in target
            ), f"Target {i} should have weight for load balancing"

            target_addr = target["target"]
            weight = target["weight"]

            # Target address format validation
            assert isinstance(target_addr, str), f"Target {i} address should be string"
            assert len(target_addr) > 0, f"Target {i} address should not be empty"
            assert ":" in target_addr, f"Target {i} should include port: {target_addr}"

            # Weight validation for load balancing
            assert isinstance(weight, int), f"Target {i} weight should be integer"
            assert weight > 0, f"Target {i} weight should be positive: {weight}"
            assert weight <= 1000, f"Target {i} weight should be reasonable: {weight}"

            # Optional: Tags for target identification
            if "tags" in target:
                tags = target["tags"]
                assert isinstance(tags, list), f"Target {i} tags should be list"

    def test_service_configuration_supports_failover(self, gateway_config):
        """Test that service configuration supports failover behavior."""
        services = gateway_config.get("services", [])
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )

        assert registry_service is not None, "registry-service not found"

        # Service should point to upstream for load balancing and failover
        assert "host" in registry_service, "Service should have host configured"
        host = registry_service["host"]
        assert (
            host == "registry-service.upstream"
        ), f"Service should use upstream for failover: {host}"

        # Timeout configuration for failover scenarios
        timeouts = ["connect_timeout", "write_timeout", "read_timeout"]
        for timeout_key in timeouts:
            if timeout_key in registry_service:
                timeout_value = registry_service[timeout_key]
                assert isinstance(timeout_value, int), f"{timeout_key} should be integer"
                assert isinstance(
                    timeout_value, int
                ), f"{timeout_key} should be integer"
                assert (
                    1000 <= timeout_value <= 300000
                ), f"{timeout_key} should be reasonable for failover: {timeout_value}ms"

        # Retry configuration for resilience
        if "retries" in registry_service:
            retries = registry_service["retries"]
            assert isinstance(retries, int), "Retries should be integer"
            assert 0 <= retries <= 10, f"Retry count should be reasonable: {retries}"

    def test_health_check_timing_configuration_supports_responsiveness(
        self, gateway_config
    ):
        """Test that health check timing supports responsive failover."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        active = registry_upstream["healthchecks"]["active"]
        registry_upstream["healthchecks"]["passive"]

        # Active health check timing validation
        timeout = active["timeout"]
        healthy_interval = active["healthy"]["interval"]
        unhealthy_interval = active["unhealthy"]["interval"]

        # Timeout should be less than check intervals
        assert (
            timeout < healthy_interval
        ), f"Health check timeout ({timeout}s) should be less than healthy interval ({healthy_interval}s)"
        assert (
            timeout < unhealthy_interval
        ), f"Health check timeout ({timeout}s) should be less than unhealthy interval ({unhealthy_interval}s)"

        # Intervals should be consistent for predictable behavior
        assert (
            healthy_interval == unhealthy_interval
        ), f"Health check intervals should be consistent: healthy={healthy_interval}s, unhealthy={unhealthy_interval}s"

        # Failure thresholds and intervals should enable reasonable failover timing
        http_failures = active["unhealthy"]["http_failures"]
        timeout_failures = active["unhealthy"]["timeouts"]

        # Maximum time to detect failure
        max_failure_detection_time = unhealthy_interval * max(http_failures, timeout_failures)
        max_failure_detection_time = unhealthy_interval * max(
            http_failures, timeout_failures
        )
        assert (
            max_failure_detection_time <= 120
        ), f"Maximum failure detection time should be reasonable: {max_failure_detection_time}s"

        # Maximum time to recover
        healthy_successes = active["healthy"]["successes"]
        max_recovery_time = healthy_interval * healthy_successes
        assert (
            max_recovery_time <= 90
        ), f"Maximum recovery time should be reasonable: {max_recovery_time}s"

    def test_health_check_status_codes_comprehensive_coverage(self, gateway_config):
        """Test that health check status codes provide comprehensive coverage for failover."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        active = registry_upstream["healthchecks"]["active"]
        passive = registry_upstream["healthchecks"]["passive"]

        # Active health check status codes
        active_healthy_codes = active["healthy"].get("http_statuses", [200])
        active_unhealthy_codes = active["unhealthy"].get("http_statuses", [])

        # Should include basic success status for active checks
        assert (
            200 in active_healthy_codes
        ), "Active health checks should consider 200 as healthy"

        # Should include server errors for active unhealthy detection
        server_errors = [500, 502, 503, 504]
        for error_code in server_errors:
            assert (
                error_code in active_unhealthy_codes
            ), f"Active health checks should consider {error_code} as unhealthy"

        # Passive health check status codes
        passive_healthy_codes = passive["healthy"]["http_statuses"]
        passive_unhealthy_codes = passive["unhealthy"]["http_statuses"]

        # Comprehensive healthy status codes for passive checks
        expected_healthy = [200, 201, 202, 204, 301, 302, 303, 304]
        for healthy_code in expected_healthy:
            assert (
                healthy_code in passive_healthy_codes
            ), f"Passive health checks should consider {healthy_code} as healthy"

        # Comprehensive unhealthy status codes for passive checks
        expected_unhealthy = [429, 500, 502, 503, 504, 505]
        for unhealthy_code in expected_unhealthy:
            assert (
                unhealthy_code in passive_unhealthy_codes
            ), f"Passive health checks should consider {unhealthy_code} as unhealthy"

        # No overlap between healthy and unhealthy status codes
        healthy_set = set(passive_healthy_codes)
        unhealthy_set = set(passive_unhealthy_codes)
        overlap = healthy_set.intersection(unhealthy_set)
        assert (
            len(overlap) == 0
        ), f"Healthy and unhealthy status codes should not overlap: {overlap}"

    def test_failover_configuration_consistency(self, gateway_config):
        """Test that failover configuration is consistent across all components."""
        upstreams = gateway_config.get("upstreams", [])
        services = gateway_config.get("services", [])

        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )
        registry_service = next(
            (s for s in services if s.get("name") == "registry-service"), None
        )
        registry_service = next((s for s in services if s.get("name") == "registry-service"), None)

        # Service should reference the upstream
        assert (
            registry_service["host"] == registry_upstream["name"]
        ), "Service host should match upstream name for failover"

        # Health check configuration should be consistent with service timeouts
        active_timeout = registry_upstream["healthchecks"]["active"]["timeout"]
        service_connect_timeout = registry_service.get("connect_timeout", 60000)

        # Health check timeout should be less than or equal to service connection timeout
        assert (
            active_timeout * 1000 <= service_connect_timeout
        ), f"Health check timeout ({active_timeout}s) should be less than or equal to service connect timeout ({service_connect_timeout}ms)"

        # Retry configuration should complement health checks
        service_retries = registry_service.get("retries", 3)
        unhealthy_failures = registry_upstream["healthchecks"]["active"]["unhealthy"][
            "http_failures"
        ]

        # Service retries should not exceed health check failure threshold
        # to avoid masking failures that should trigger health check changes
        assert (
            service_retries <= unhealthy_failures
        ), f"Service retries ({service_retries}) should not exceed health check failure threshold ({unhealthy_failures})"

    def test_health_check_configuration_file_structure(self, gateway_config):
        """Test that health check configuration follows proper structure for maintainability."""
        upstreams = gateway_config.get("upstreams", [])
        registry_upstream = next(
            (u for u in upstreams if u.get("name") == "registry-service.upstream"), None
        )

        healthchecks = registry_upstream["healthchecks"]

        # Required top-level structure
        assert isinstance(healthchecks, dict), "Health checks should be dictionary"
        assert "active" in healthchecks, "Active health checks section required"
        assert "passive" in healthchecks, "Passive health checks section required"

        # Active health checks structure
        active = healthchecks["active"]
        required_active_fields = [
            "type",
            "http_path",
            "timeout",
            "concurrency",
            "healthy",
            "unhealthy",
        ]
        for field in required_active_fields:
            assert field in active, f"Active health checks should have {field} field"

        # Healthy and unhealthy subsections
        for section_name in ["healthy", "unhealthy"]:
            section = active[section_name]
            assert isinstance(
                section, dict
            ), f"Active {section_name} should be dictionary"
            assert "interval" in section, f"Active {section_name} should have interval"

            if section_name == "healthy":
                assert (
                    "successes" in section
                ), f"Active {section_name} should have successes"
            else:  # unhealthy
                required_unhealthy_fields = [
                    "http_failures",
                    "timeouts",
                    "tcp_failures",
                ]
                for field in required_unhealthy_fields:
                    assert (
                        field in section
                    ), f"Active {section_name} should have {field}"

        # Passive health checks structure
        passive = healthchecks["passive"]
        required_passive_fields = ["type", "healthy", "unhealthy"]
        for field in required_passive_fields:
            assert field in passive, f"Passive health checks should have {field} field"

        # Passive healthy and unhealthy subsections
        for section_name in ["healthy", "unhealthy"]:
            section = passive[section_name]
            assert isinstance(
                section, dict
            ), f"Passive {section_name} should be dictionary"
            assert (
                "http_statuses" in section
            ), f"Passive {section_name} should have http_statuses"

            http_statuses = section["http_statuses"]
            assert isinstance(
                http_statuses, list
            ), f"Passive {section_name} http_statuses should be list"
            assert (
                len(http_statuses) > 0
            ), f"Passive {section_name} should have at least one status code"

            # All status codes should be valid HTTP status codes
            for status_code in http_statuses:
                assert isinstance(status_code, int), f"Status code should be integer: {status_code}"
                assert isinstance(
                    status_code, int
                ), f"Status code should be integer: {status_code}"
                assert (
                    100 <= status_code <= 599
                ), f"Status code should be valid HTTP status: {status_code}"
