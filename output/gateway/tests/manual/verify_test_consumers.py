#!/usr/bin/env python3
"""
Manual verification script for test consumers with API keys.

This script demonstrates the usage of all test consumers created in task 5.6.
Run this script when the gateway is running to verify API key authentication.

Usage:
    python gateway/tests/manual/verify_test_consumers.py
"""

import httpx
import sys
from typing import Dict


def test_consumer(
    name: str, api_key: str, base_url: str = "http://localhost:8000"
) -> Dict:
    """Test a single consumer with its API key."""
    print(f"\n🔑 Testing {name} with API key: {api_key[:10]}...")

    result = {
        "consumer": name,
        "api_key": api_key,
        "status": "unknown",
        "response_code": None,
        "headers": {},
        "error": None,
    }

    try:
        client = httpx.Client(base_url=base_url, headers={"X-API-Key": api_key}, timeout=10.0)
        client = httpx.Client(
            base_url=base_url, headers={"X-API-Key": api_key}, timeout=10.0
        )

        response = client.get("/api/v1/registry/services")
        result["response_code"] = response.status_code
        result["headers"] = dict(response.headers)

        if response.status_code in [401, 403]:
            result["status"] = "❌ AUTHENTICATION FAILED"
            result["error"] = f"HTTP {response.status_code}: {response.text}"
        elif response.status_code in [200, 404, 502, 503]:
            result["status"] = "✅ AUTHENTICATION SUCCESS"
            if response.status_code == 200:
                result["status"] += " (Service Available)"
            elif response.status_code == 404:
                result["status"] += " (Service Not Found)"
            elif response.status_code in [502, 503]:
                result["status"] += " (Service Unavailable)"
        else:
            result["status"] = f"⚠️ UNEXPECTED STATUS: {response.status_code}"

        client.close()

    except httpx.ConnectError:
        result["status"] = "🔌 CONNECTION FAILED"
        result["error"] = "Gateway not running at " + base_url
    except Exception as e:
        result["status"] = "💥 ERROR"
        result["error"] = str(e)

    return result


def print_result(result: Dict):
    """Pretty print test result."""
    print(f"   Status: {result['status']}")
    print(f"   Response Code: {result['response_code']}")

    # Show important headers
    headers = result["headers"]
    important_headers = [
        "X-Correlation-ID",
        "X-Kong-Proxy-Latency",
        "X-Kong-Upstream-Latency",
        "X-RateLimit-Limit-Minute",
        "X-RateLimit-Remaining-Minute",
    ]

    for header in important_headers:
        if header in headers:
            print(f"   {header}: {headers[header]}")

    if result["error"]:
        print(f"   Error: {result['error']}")


def main():
    """Test all configured consumers."""
    print("🚀 VentureStrat Gateway - Test Consumer Verification")
    print("=" * 60)

    # Test consumers as defined in kong.yaml
    consumers = [
        {
            "name": "Default Development Consumer",
            "api_key": "dev-api-key-12345",
            "description": "Primary development testing (1000/min)",
        },
        {
            "name": "Test Integration Consumer",
            "api_key": "test-api-key-67890",
            "description": "Integration testing (1000/min)",
        },
        {
            "name": "Free Tier Consumer",
            "api_key": "free-api-key-11111",
            "description": "External API simulation - free tier (100/min)",
        },
        {
            "name": "Standard Tier Consumer",
            "api_key": "standard-api-key-22222",
            "description": "External API simulation - standard tier (1000/min)",
        },
    ]

    results = []
    all_passed = True

    for consumer in consumers:
        print(f"\n📊 {consumer['name']}")
        print(f"   Description: {consumer['description']}")

        result = test_consumer(consumer["name"], consumer["api_key"])
        print_result(result)
        results.append(result)

        if "AUTHENTICATION FAILED" in result["status"] or "ERROR" in result["status"]:
            all_passed = False

    print(f"\n{'=' * 60}")
    print("📋 SUMMARY")

    success_count = 0
    for result in results:
        if "AUTHENTICATION SUCCESS" in result["status"]:
            success_count += 1
            print(f"✅ {result['consumer']}: {result['status']}")
        else:
            print(f"❌ {result['consumer']}: {result['status']}")

    print(
        f"\n📈 Results: {success_count}/{len(consumers)} consumers authenticated successfully"
    )

    if all_passed:
        print("🎉 All test consumers are properly configured and working!")
        return 0
    else:
        print("⚠️ Some test consumers failed. Check gateway configuration and status.")
        return 1


def test_without_api_key():
    """Test request without API key (should return 401)."""
    print("\n🚫 Testing request without API key...")

    try:
        client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        response = client.get("/api/v1/registry/services")

        if response.status_code == 401:
            print("✅ Correctly rejected request without API key (401)")
        else:
            print(f"❌ Expected 401, got {response.status_code}")

        client.close()

    except httpx.ConnectError:
        print("🔌 Gateway not running")
    except Exception as e:
        print(f"💥 Error: {e}")


def test_invalid_api_key():
    """Test request with invalid API key (should return 403)."""
    print("\n🔒 Testing request with invalid API key...")

    try:
        client = httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "invalid-key-99999"},
            timeout=10.0,
        )
        response = client.get("/api/v1/registry/services")

        if response.status_code == 403:
            print("✅ Correctly rejected invalid API key (403)")
        else:
            print(f"❌ Expected 403, got {response.status_code}")

        client.close()

    except httpx.ConnectError:
        print("🔌 Gateway not running")
    except Exception as e:
        print(f"💥 Error: {e}")


if __name__ == "__main__":
    exit_code = main()

    # Additional security tests
    test_without_api_key()
    test_invalid_api_key()

    print("\n💡 To start the gateway for testing:")
    print("   docker compose -f docker-compose.infra.yaml up -d")
    print("   docker compose -f gateway/docker-compose.gateway.yaml up -d")

    sys.exit(exit_code)
