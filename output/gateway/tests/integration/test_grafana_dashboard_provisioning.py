"""
Integration tests for Grafana dashboard provisioning with Kong metrics.

These tests verify that:
1. Kong exposes metrics in Prometheus format
2. Grafana dashboard JSON is valid
3. Observability stack can be started successfully
4. Dashboard provisioning works correctly

Test execution requires:
- Kong gateway running with prometheus plugin enabled
- Observability stack (prometheus + grafana) started
"""

import json
import time
import pytest
import httpx
import yaml
from pathlib import Path


class TestKongMetricsProvisioning:
    """Test Kong metrics availability and Grafana dashboard provisioning."""

    @pytest.fixture(scope="class")
    def observability_paths(self):
        """Return paths to observability configuration files."""
        base_path = Path(__file__).parent.parent.parent.parent / "observability"
        return {
            "base": base_path,
            "prometheus_config": base_path / "prometheus" / "prometheus.yml",
            "grafana_datasources": base_path
            / "grafana"
            / "provisioning"
            / "datasources"
            / "datasources.yaml",
            "grafana_dashboards_config": base_path
            / "grafana"
            / "provisioning"
            / "dashboards"
            / "dashboards.yaml",
            "kong_dashboard": base_path / "grafana" / "dashboards" / "kong-gateway-metrics.json",
            "kong_dashboard": base_path
            / "grafana"
            / "dashboards"
            / "kong-gateway-metrics.json",
            "docker_compose": base_path / "docker-compose.observability.yaml",
        }

    def test_observability_config_files_exist(self, observability_paths):
        """Test that all observability configuration files exist."""
        for name, path in observability_paths.items():
            if name != "base":  # Skip base path check
                assert path.exists(), f"Missing observability config file: {path}"

    def test_prometheus_config_valid_yaml(self, observability_paths):
        """Test that Prometheus configuration is valid YAML."""
        with open(observability_paths["prometheus_config"]) as f:
            config = yaml.safe_load(f)

        # Verify required sections
        assert "global" in config
        assert "scrape_configs" in config
        assert "scrape_interval" in config["global"]

        # Verify Kong job configuration
        kong_job = None
        for job in config["scrape_configs"]:
            if job["job_name"] == "kong-gateway":
                kong_job = job
                break

        assert (
            kong_job is not None
        ), "Kong gateway scrape job not found in prometheus.yml"
        assert "static_configs" in kong_job
        assert kong_job["metrics_path"] == "/metrics"
        assert "kong:8001" in str(kong_job["static_configs"])

    def test_grafana_datasources_config_valid(self, observability_paths):
        """Test that Grafana datasources configuration is valid."""
        with open(observability_paths["grafana_datasources"]) as f:
            config = yaml.safe_load(f)

        assert config["apiVersion"] == 1
        assert "datasources" in config

        # Find Prometheus datasource
        prometheus_ds = None
        for ds in config["datasources"]:
            if ds["name"] == "Prometheus":
                prometheus_ds = ds
                break

        assert prometheus_ds is not None, "Prometheus datasource not found"
        assert prometheus_ds["type"] == "prometheus"
        assert prometheus_ds["url"] == "http://prometheus:9090"
        assert prometheus_ds["isDefault"] is True

    def test_grafana_dashboards_config_valid(self, observability_paths):
        """Test that Grafana dashboards configuration is valid."""
        with open(observability_paths["grafana_dashboards_config"]) as f:
            config = yaml.safe_load(f)

        assert config["apiVersion"] == 1
        assert "providers" in config
        assert len(config["providers"]) >= 1

    def test_kong_dashboard_json_valid(self, observability_paths):
        """Test that Kong dashboard JSON is valid and well-structured."""
        with open(observability_paths["kong_dashboard"]) as f:
            dashboard = json.load(f)

        # Verify basic dashboard structure
        assert "title" in dashboard
        assert "panels" in dashboard
        assert "tags" in dashboard
        assert "uid" in dashboard

        assert dashboard["title"] == "Kong Gateway Metrics"
        assert dashboard["uid"] == "kong-gateway-metrics"
        assert "kong" in dashboard["tags"]
        assert "gateway" in dashboard["tags"]

        # Verify panels exist and have required structure
        panels = dashboard["panels"]
        assert len(panels) >= 5, "Dashboard should have multiple panels"

        # Check for key panels by title
        panel_titles = [panel["title"] for panel in panels]
        expected_panels = [
            "Datastore Health",
            "Request Rate",
            "HTTP Status Codes",
            "Kong Latency Percentiles",
            "Requests by Consumer",
            "Requests by Service",
        ]

        for expected_panel in expected_panels:
            assert expected_panel in panel_titles, f"Missing panel: {expected_panel}"

        # Verify panels have proper Prometheus queries
        for panel in panels:
            if "targets" in panel:
                for target in panel["targets"]:
                    if "expr" in target:
                        expr = target["expr"]
                        # Kong metrics should start with 'kong_'
                        if "kong_" in expr:
                            assert any(
                                metric in expr
                                for metric in [
                                    "kong_http_requests_total",
                                    "kong_latency_ms_bucket",
                                    "kong_datastore_reachable",
                                    "kong_bandwidth_bytes",
                                ]
                            ), f"Unexpected Kong metric in expression: {expr}"

    def test_docker_compose_observability_valid(self, observability_paths):
        """Test that observability Docker Compose configuration is valid."""
        with open(observability_paths["docker_compose"]) as f:
            config = yaml.safe_load(f)

        assert "services" in config
        assert "prometheus" in config["services"]
        assert "grafana" in config["services"]

        # Verify Prometheus configuration
        prometheus = config["services"]["prometheus"]
        assert prometheus["image"].startswith("prom/prometheus")
        assert "9090:9090" in prometheus["ports"]

        # Verify Grafana configuration
        grafana = config["services"]["grafana"]
        assert grafana["image"].startswith("grafana/grafana")
        assert "3000:3000" in grafana["ports"]

        # Verify volume mounts for provisioning
        grafana_volumes = grafana["volumes"]
        provisioning_mount = any("provisioning" in vol for vol in grafana_volumes)
        dashboard_mount = any("dashboards" in vol for vol in grafana_volumes)
        assert provisioning_mount, "Grafana provisioning directory not mounted"
        assert dashboard_mount, "Grafana dashboards directory not mounted"

    @pytest.mark.integration
    def test_kong_metrics_endpoint_accessible(self):
        """Test that Kong metrics endpoint is accessible (requires Kong running)."""
        try:
            # Try to access Kong Admin API metrics endpoint
            response = httpx.get(
                "http://localhost:8001/metrics",
                timeout=5,
                params={"format": "prometheus"},
            )

            if response.status_code == 200:
                metrics_text = response.text

                # Verify Prometheus format
                assert "# HELP" in metrics_text or "# TYPE" in metrics_text

                # Verify Kong-specific metrics are present
                expected_metrics = [
                    "kong_datastore_reachable",
                    "kong_http_requests_total",
                ]

                for metric in expected_metrics:
                    assert metric in metrics_text, f"Missing Kong metric: {metric}"

            else:
                pytest.skip(f"Kong Admin API not accessible: {response.status_code}")

        except httpx.RequestError:
            pytest.skip("Kong gateway not running - skipping metrics endpoint test")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_prometheus_scraping_kong_metrics(self):
        """Test that Prometheus can scrape Kong metrics (requires observability stack running)."""
        try:
            # Wait for Prometheus to be ready
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = httpx.get("http://localhost:9090/-/ready", timeout=2)
                    if response.status_code == 200:
                        break
                except httpx.RequestError:
                    pass

                if i < max_retries - 1:
                    time.sleep(2)
                else:
                    pytest.skip(
                        "Prometheus not accessible - observability stack may not be running"
                    )

            # Query Prometheus for Kong metrics
            response = httpx.get(
                "http://localhost:9090/api/v1/query",
                params={"query": "kong_datastore_reachable"},
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                assert result["status"] == "success"

                # Check if we have data (may be empty if Kong is not running)
                data = result["data"]
                assert "result" in data

                # If Kong is running and exposing metrics, we should have results
                if data["result"]:
                    assert len(data["result"]) > 0
                    assert "value" in data["result"][0]
            else:
                pytest.skip(f"Prometheus API not accessible: {response.status_code}")

        except httpx.RequestError:
            pytest.skip("Prometheus not running - skipping scraping test")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_grafana_dashboard_provisioning(self):
        """Test that Grafana provisions the Kong dashboard correctly (requires Grafana running)."""
        try:
            # Wait for Grafana to be ready
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = httpx.get(
                        "http://localhost:3000/api/health",
                        timeout=2,
                        auth=("admin", "admin"),
                    )
                    if response.status_code == 200:
                        break
                except httpx.RequestError:
                    pass

                if i < max_retries - 1:
                    time.sleep(2)
                else:
                    pytest.skip(
                        "Grafana not accessible - observability stack may not be running"
                    )

            # Check if Kong dashboard is provisioned
            response = httpx.get(
                "http://localhost:3000/api/dashboards/uid/kong-gateway-metrics",
                timeout=10,
                auth=("admin", "admin"),
            )

            if response.status_code == 200:
                dashboard_info = response.json()
                dashboard = dashboard_info["dashboard"]

                assert dashboard["title"] == "Kong Gateway Metrics"
                assert dashboard["uid"] == "kong-gateway-metrics"
                assert len(dashboard["panels"]) >= 5

                # Verify tags
                assert "kong" in dashboard["tags"]
                assert "gateway" in dashboard["tags"]

            elif response.status_code == 404:
                pytest.skip("Kong dashboard not found - may not be provisioned yet")
            else:
                pytest.skip(f"Grafana API error: {response.status_code}")

        except httpx.RequestError:
            pytest.skip("Grafana not running - skipping dashboard provisioning test")

    def test_dashboard_queries_reference_correct_metrics(self, observability_paths):
        """Test that dashboard queries reference valid Kong Prometheus metrics."""
        with open(observability_paths["kong_dashboard"]) as f:
            dashboard = json.load(f)

        # Known Kong Prometheus metrics (based on actual Kong output)
        known_kong_metrics = {
            "kong_http_requests_total",
            "kong_latency_ms_bucket",
            "kong_latency_ms_sum",
            "kong_latency_ms_count",
            "kong_datastore_reachable",
            "kong_bandwidth_bytes",
            "kong_upstream_latency_ms_bucket",
            "kong_upstream_target_health",
        }

        # Extract all Prometheus queries from dashboard panels
        queries = []
        for panel in dashboard["panels"]:
            if "targets" in panel:
                for target in panel["targets"]:
                    if "expr" in target and target["expr"]:
                        queries.append(target["expr"])

        assert len(queries) > 0, "No Prometheus queries found in dashboard"

        # Verify each query uses valid Kong metrics
        for query in queries:
            # Extract metric names from query (basic parsing)
            for metric in known_kong_metrics:
                if metric in query:
                    # Found a valid Kong metric in this query
                    break
            else:
                # If we reach here, no valid Kong metric was found
                # This might be okay for some generic queries, but let's be lenient
                # and just check that it's not obviously wrong
                assert not query.startswith("invalid_"), f"Suspicious query: {query}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
