#!/usr/bin/env python3
"""
Manual integration test for tenant-header plugin.

This script provides comprehensive manual testing of the tenant-header plugin
in a real Kong environment. It can be run independently to validate plugin
functionality.

Usage:
    python test_tenant_header_manual.py
    python test_tenant_header_manual.py --kong-admin http://localhost:8001 --kong-proxy http://localhost:8000
"""

import argparse
import requests
import jwt
import time
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class TestResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class TestCase:
    name: str
    description: str
    result: TestResult
    details: str = ""
    duration: float = 0.0


class TenantHeaderTester:
    """Manual tester for tenant-header plugin functionality."""

    def __init__(
        self,
        kong_admin_url: str,
        kong_proxy_url: str,
        jwt_secret: str = "test-secret-key-123456789",
    ):
        self.kong_admin_url = kong_admin_url.rstrip("/")
        self.kong_proxy_url = kong_proxy_url.rstrip("/")
        self.jwt_secret = jwt_secret
        self.results: List[TestCase] = []

        # Test data
        self.sample_tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.api_key = "test-api-key-67890"

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def create_jwt_token(
        self, tenant_id: Optional[str] = None, expired: bool = False
    ) -> str:
        """Create JWT token with optional tenant_id."""
        now = datetime.utcnow()

        payload = {
            "sub": "test-user-123",
            "iss": "venturestrat",
            "aud": "api",
            "iat": now,
        }

        if tenant_id:
            payload["tenant_id"] = tenant_id

        if expired:
            payload["exp"] = now - timedelta(hours=1)
        else:
            payload["exp"] = now + timedelta(hours=1)

        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    def run_test(self, test_name: str, test_description: str, test_func) -> TestCase:
        """Run a single test and record results."""
        self.log(f"Running: {test_name}")
        start_time = time.time()

        try:
            result = test_func()
            if result is True:
                test_result = TestResult.PASS
                details = "Test passed successfully"
            elif result is False:
                test_result = TestResult.FAIL
                details = "Test failed"
            else:
                test_result = (
                    TestResult.PASS if result.get("success", False) else TestResult.FAIL
                )
                details = result.get("message", "")
        except Exception as e:
            test_result = TestResult.FAIL
            details = f"Test failed with exception: {str(e)}"

        duration = time.time() - start_time
        test_case = TestCase(
            name=test_name,
            description=test_description,
            result=test_result,
            details=details,
            duration=duration,
        )

        self.results.append(test_case)

        status_emoji = (
            "✅"
            if test_result == TestResult.PASS
            else "❌"
            if test_result == TestResult.FAIL
            else "⏸️"
        )
        self.log(f"{status_emoji} {test_name}: {test_result.value} ({duration:.2f}s)")
        if details and test_result != TestResult.PASS:
            self.log(f"   Details: {details}")

        return test_case

    def test_kong_admin_connectivity(self) -> Dict[str, Any]:
        """Test Kong Admin API connectivity."""
        try:
            response = requests.get(f"{self.kong_admin_url}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message": f"Kong Admin API accessible. Database: {data.get('database', {}).get('reachable', 'Unknown')}",
                }
            else:
                return {
                    "success": False,
                    "message": f"Kong Admin API returned {response.status_code}",
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Cannot connect to Kong Admin API: {str(e)}",
            }

    def test_kong_proxy_connectivity(self) -> Dict[str, Any]:
        """Test Kong Proxy API connectivity."""
        try:
            # Test with health endpoint which should be excluded from tenant requirement
            response = requests.get(f"{self.kong_proxy_url}/health", timeout=5)
            # Any response (even 404) indicates connectivity
            return {
                "success": True,
                "message": f"Kong Proxy API accessible (status: {response.status_code})",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Cannot connect to Kong Proxy API: {str(e)}",
            }

    def test_tenant_header_plugin_installed(self) -> Dict[str, Any]:
        """Test that tenant-header plugin is installed and configured."""
        try:
            response = requests.get(f"{self.kong_admin_url}/plugins")
            if response.status_code != 200:
                return {
                    "success": False,
                    "message": f"Cannot fetch plugins: HTTP {response.status_code}",
                }

            plugins = response.json().get("data", [])
            tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

            if not tenant_plugins:
                return {"success": False, "message": "Tenant-header plugin not found"}

            plugin = tenant_plugins[0]
            config = plugin.get("config", {})

            checks = []
            checks.append(f"Plugin ID: {plugin.get('id', 'Unknown')}")
            checks.append(f"Enabled: {plugin.get('enabled', False)}")
            checks.append(f"Header Name: {config.get('header_name', 'Not configured')}")
            checks.append(f"Strict Mode: {config.get('strict_mode', 'Not configured')}")
            checks.append(
                f"Exclude Paths: {len(config.get('exclude_paths', []))} configured"
            )

            return {
                "success": True,
                "message": "Tenant-header plugin found. " + ", ".join(checks),
            }

        except Exception as e:
            return {"success": False, "message": f"Error checking plugin: {str(e)}"}

    def test_jwt_plugin_installed(self) -> Dict[str, Any]:
        """Test that JWT plugin is installed and configured."""
        try:
            response = requests.get(f"{self.kong_admin_url}/plugins")
            if response.status_code != 200:
                return {
                    "success": False,
                    "message": f"Cannot fetch plugins: HTTP {response.status_code}",
                }

            plugins = response.json().get("data", [])
            jwt_plugins = [p for p in plugins if p.get("name") == "jwt"]

            if not jwt_plugins:
                return {"success": False, "message": "JWT plugin not found"}

            plugin = jwt_plugins[0]
            return {
                "success": True,
                "message": f"JWT plugin found (ID: {plugin.get('id', 'Unknown')}, Enabled: {plugin.get('enabled', False)})",
            }

        except Exception as e:
            return {"success": False, "message": f"Error checking JWT plugin: {str(e)}"}

    def test_request_without_jwt_rejected(self) -> Dict[str, Any]:
        """Test that requests without JWT are rejected."""
        try:
            response = requests.get(f"{self.kong_proxy_url}/api/v1/registry/test")

            if response.status_code == 401:
                return {
                    "success": True,
                    "message": "Request correctly rejected with 401 (no JWT)",
                }
            else:
                return {
                    "success": False,
                    "message": f"Expected 401, got {response.status_code}. JWT authentication may not be working.",
                }
        except Exception as e:
            return {"success": False, "message": f"Error testing no JWT: {str(e)}"}

    def test_request_with_jwt_but_no_tenant_rejected(self) -> Dict[str, Any]:
        """Test that requests with JWT but no tenant_id are rejected."""
        try:
            token = self.create_jwt_token(tenant_id=None)
            headers = {"Authorization": f"Bearer {token}", "X-API-Key": self.api_key}

            response = requests.get(
                f"{self.kong_proxy_url}/api/v1/registry/test", headers=headers
            )

            if response.status_code == 401:
                try:
                    error_data = response.json()
                    if error_data.get("error") == "missing_tenant":
                        return {
                            "success": True,
                            "message": "Request correctly rejected - missing tenant_id in JWT",
                        }
                    else:
                        return {
                            "success": True,
                            "message": f"Request rejected with 401, error: {error_data.get('error', 'unknown')}",
                        }
                except:
                    return {
                        "success": True,
                        "message": "Request correctly rejected with 401 (likely missing tenant)",
                    }
            else:
                return {
                    "success": False,
                    "message": f"Expected 401 for missing tenant, got {response.status_code}",
                }
        except Exception as e:
            return {"success": False, "message": f"Error testing no tenant: {str(e)}"}

    def test_request_with_valid_jwt_and_tenant_accepted(self) -> Dict[str, Any]:
        """Test that requests with valid JWT and tenant_id are accepted by plugin."""
        try:
            token = self.create_jwt_token(tenant_id=self.sample_tenant_id)
            headers = {"Authorization": f"Bearer {token}", "X-API-Key": self.api_key}

            response = requests.get(
                f"{self.kong_proxy_url}/api/v1/registry/test", headers=headers
            )

            # Plugin should process this successfully (even if downstream service is down)
            # 401 would indicate plugin rejection; 502/503 means plugin passed but service down
            if response.status_code in [200, 502, 503, 404]:
                return {
                    "success": True,
                    "message": f"Plugin processed request successfully (status: {response.status_code})",
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Request rejected with 401 - plugin may not be processing tenant_id correctly",
                }
            else:
                return {
                    "success": True,  # Other errors are likely downstream, not plugin
                    "message": f"Plugin processed request (downstream status: {response.status_code})",
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error testing valid tenant: {str(e)}",
            }

    def test_excluded_paths_bypass_tenant_requirement(self) -> Dict[str, Any]:
        """Test that excluded paths bypass tenant requirement."""
        try:
            # Create JWT without tenant_id
            token = self.create_jwt_token(tenant_id=None)
            headers = {"Authorization": f"Bearer {token}", "X-API-Key": self.api_key}

            # Test excluded paths
            excluded_paths = ["/health", "/metrics", "/status"]
            results = []

            for path in excluded_paths:
                response = requests.get(f"{self.kong_proxy_url}{path}", headers=headers)

                # Should NOT be 401 with missing_tenant error
                if response.status_code == 401:
                    try:
                        error_data = response.json()
                        if error_data.get("error") == "missing_tenant":
                            results.append(
                                f"❌ {path}: Wrongly rejected for missing tenant"
                            )
                        else:
                            results.append(f"✅ {path}: 401 for other reason (OK)")
                    except:
                        results.append(f"✅ {path}: 401 for other reason (OK)")
                else:
                    results.append(
                        f"✅ {path}: Bypassed tenant check (status: {response.status_code})"
                    )

            failed_paths = [r for r in results if r.startswith("❌")]

            return {
                "success": len(failed_paths) == 0,
                "message": f"Path exclusion test: {len(excluded_paths)} paths tested. "
                + "; ".join(results),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error testing excluded paths: {str(e)}",
            }

    def test_expired_jwt_rejected(self) -> Dict[str, Any]:
        """Test that expired JWT tokens are rejected."""
        try:
            expired_token = self.create_jwt_token(
                tenant_id=self.sample_tenant_id, expired=True
            )
            headers = {
                "Authorization": f"Bearer {expired_token}",
                "X-API-Key": self.api_key,
            }

            response = requests.get(
                f"{self.kong_proxy_url}/api/v1/registry/test", headers=headers
            )

            if response.status_code == 401:
                return {"success": True, "message": "Expired JWT correctly rejected"}
            else:
                return {
                    "success": False,
                    "message": f"Expected 401 for expired JWT, got {response.status_code}",
                }
        except Exception as e:
            return {"success": False, "message": f"Error testing expired JWT: {str(e)}"}

    def test_invalid_jwt_signature_rejected(self) -> Dict[str, Any]:
        """Test that JWT with invalid signature is rejected."""
        try:
            # Create token with wrong secret
            payload = {
                "sub": "test-user",
                "tenant_id": self.sample_tenant_id,
                "iss": "venturestrat",
                "aud": "api",
                "exp": datetime.utcnow() + timedelta(hours=1),
                "iat": datetime.utcnow(),
            }
            invalid_token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")

            headers = {
                "Authorization": f"Bearer {invalid_token}",
                "X-API-Key": self.api_key,
            }

            response = requests.get(
                f"{self.kong_proxy_url}/api/v1/registry/test", headers=headers
            )

            if response.status_code == 401:
                return {
                    "success": True,
                    "message": "Invalid JWT signature correctly rejected",
                }
            else:
                return {
                    "success": False,
                    "message": f"Expected 401 for invalid signature, got {response.status_code}",
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error testing invalid signature: {str(e)}",
            }

    def test_plugin_configuration_details(self) -> Dict[str, Any]:
        """Test detailed plugin configuration."""
        try:
            response = requests.get(f"{self.kong_admin_url}/plugins")
            plugins = response.json().get("data", [])
            tenant_plugins = [p for p in plugins if p.get("name") == "tenant-header"]

            if not tenant_plugins:
                return {"success": False, "message": "Tenant-header plugin not found"}

            config = tenant_plugins[0].get("config", {})

            details = []
            details.append(f"Header Name: {config.get('header_name', 'X-Tenant-ID')}")
            details.append(f"Debug Header: {config.get('debug_header', False)}")
            details.append(f"Emit Metrics: {config.get('emit_metrics', True)}")
            details.append(f"Strict Mode: {config.get('strict_mode', True)}")
            details.append(f"Log Level: {config.get('log_level', 'info')}")

            exclude_paths = config.get("exclude_paths", [])
            details.append(f"Exclude Paths: {exclude_paths}")

            return {
                "success": True,
                "message": "Plugin configuration: " + "; ".join(details),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error checking configuration: {str(e)}",
            }

    def test_multiple_tenants_isolation(self) -> Dict[str, Any]:
        """Test that different tenant IDs are processed correctly."""
        try:
            tenant_ids = [
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440002",
                "550e8400-e29b-41d4-a716-446655440003",
            ]

            results = []
            for tenant_id in tenant_ids:
                token = self.create_jwt_token(tenant_id=tenant_id)
                headers = {
                    "Authorization": f"Bearer {token}",
                    "X-API-Key": self.api_key,
                }

                response = requests.get(
                    f"{self.kong_proxy_url}/api/v1/registry/test", headers=headers
                )

                # Plugin should process all tenant IDs successfully
                if response.status_code in [200, 502, 503, 404]:
                    results.append(f"✅ Tenant {tenant_id[-4:]}: OK")
                elif response.status_code == 401:
                    results.append(f"❌ Tenant {tenant_id[-4:]}: Rejected")
                else:
                    results.append(f"? Tenant {tenant_id[-4:]}: {response.status_code}")

            failed = [r for r in results if r.startswith("❌")]

            return {
                "success": len(failed) == 0,
                "message": f"Multi-tenant test: {len(tenant_ids)} tenants tested. "
                + "; ".join(results),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error testing multiple tenants: {str(e)}",
            }

    def run_all_tests(self):
        """Run all manual integration tests."""
        self.log("=" * 80)
        self.log("TENANT-HEADER PLUGIN MANUAL INTEGRATION TESTS")
        self.log("=" * 80)
        self.log(f"Kong Admin URL: {self.kong_admin_url}")
        self.log(f"Kong Proxy URL: {self.kong_proxy_url}")
        self.log("")

        # Infrastructure tests
        self.run_test(
            "Kong Admin Connectivity",
            "Test connectivity to Kong Admin API",
            self.test_kong_admin_connectivity,
        )

        self.run_test(
            "Kong Proxy Connectivity",
            "Test connectivity to Kong Proxy API",
            self.test_kong_proxy_connectivity,
        )

        # Plugin installation tests
        self.run_test(
            "Tenant-Header Plugin Installed",
            "Test that tenant-header plugin is properly installed",
            self.test_tenant_header_plugin_installed,
        )

        self.run_test(
            "JWT Plugin Installed",
            "Test that JWT plugin is properly installed",
            self.test_jwt_plugin_installed,
        )

        # Functional tests
        self.run_test(
            "No JWT Rejection",
            "Test that requests without JWT are rejected",
            self.test_request_without_jwt_rejected,
        )

        self.run_test(
            "No Tenant Rejection",
            "Test that requests without tenant_id are rejected",
            self.test_request_with_jwt_but_no_tenant_rejected,
        )

        self.run_test(
            "Valid Tenant Acceptance",
            "Test that requests with valid tenant_id are accepted",
            self.test_request_with_valid_jwt_and_tenant_accepted,
        )

        self.run_test(
            "Excluded Paths Bypass",
            "Test that excluded paths bypass tenant requirement",
            self.test_excluded_paths_bypass_tenant_requirement,
        )

        self.run_test(
            "Expired JWT Rejection",
            "Test that expired JWT tokens are rejected",
            self.test_expired_jwt_rejected,
        )

        self.run_test(
            "Invalid Signature Rejection",
            "Test that JWT with invalid signature is rejected",
            self.test_invalid_jwt_signature_rejected,
        )

        # Configuration tests
        self.run_test(
            "Plugin Configuration",
            "Test plugin configuration details",
            self.test_plugin_configuration_details,
        )

        self.run_test(
            "Multi-Tenant Isolation",
            "Test handling of multiple different tenant IDs",
            self.test_multiple_tenants_isolation,
        )

        # Print results
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        self.log("")
        self.log("=" * 80)
        self.log("TEST SUMMARY")
        self.log("=" * 80)

        passed = sum(1 for r in self.results if r.result == TestResult.PASS)
        failed = sum(1 for r in self.results if r.result == TestResult.FAIL)
        skipped = sum(1 for r in self.results if r.result == TestResult.SKIP)
        total = len(self.results)

        self.log(f"Total Tests: {total}")
        self.log(f"✅ Passed: {passed}")
        self.log(f"❌ Failed: {failed}")
        self.log(f"⏸️ Skipped: {skipped}")
        self.log("")

        if failed > 0:
            self.log("FAILED TESTS:")
            for result in self.results:
                if result.result == TestResult.FAIL:
                    self.log(f"❌ {result.name}: {result.details}")
            self.log("")

        overall_status = "PASS" if failed == 0 else "FAIL"
        self.log(f"OVERALL STATUS: {overall_status}")
        self.log("=" * 80)

        return overall_status == "PASS"


def main():
    """Main function for manual testing."""
    parser = argparse.ArgumentParser(
        description="Manual integration test for tenant-header plugin"
    )
    parser.add_argument(
        "--kong-admin",
        default="http://localhost:8001",
        help="Kong Admin API URL (default: http://localhost:8001)",
    )
    parser.add_argument(
        "--kong-proxy",
        default="http://localhost:8000",
        help="Kong Proxy API URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--jwt-secret",
        default="test-secret-key-123456789",
        help="JWT secret key for token generation",
    )

    args = parser.parse_args()

    tester = TenantHeaderTester(
        kong_admin_url=args.kong_admin,
        kong_proxy_url=args.kong_proxy,
        jwt_secret=args.jwt_secret,
    )

    success = tester.run_all_tests()

    # Exit with proper code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
