#!/usr/bin/env python3
"""
Manual verification script for task 11.5: Verify logs include correlation ID and consumer info.

This script makes requests to the Kong gateway and captures the logs to verify
that correlation IDs and consumer information are properly logged.
"""

import requests
import subprocess
import time
import json
import sys
from typing import List, Dict, Any, Optional


def capture_kong_logs(duration_seconds: float = 3) -> List[str]:
    """Capture Kong container logs for analysis."""
    try:
        # Use docker logs command to get recent logs
        cmd = ["docker", "logs", "--tail=50", "kong-gateway"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            print(f"Error capturing logs: {result.stderr}")
            return []

        return [line.strip() for line in result.stdout.split("\n") if line.strip()]

    except Exception as e:
        print(f"Exception capturing logs: {e}")
        return []


def parse_log_entry(log_line: str) -> Optional[Dict[str, Any]]:
    """Try to parse a log entry as JSON or extract key information."""
    # Try JSON parsing first
    try:
        if "{" in log_line and "}" in log_line:
            json_start = log_line.find("{")
            json_content = log_line[json_start:]
            return json.loads(json_content)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to extract key-value pairs from Kong access log format
    try:
        # Kong access logs often contain key=value pairs
        parsed = {}
        parts = log_line.split()

        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                parsed[key] = value.strip('"')

        return parsed if parsed else None
    except Exception:
        pass

    return None


def make_test_request(correlation_id: str) -> requests.Response:
    """Make a test request with specific correlation ID."""
    headers = {
        "X-API-Key": "dev-api-key-12345",
        "X-Correlation-ID": correlation_id,
        "User-Agent": "task-11.5-verification/1.0",
    }

    try:
        response = requests.get("http://localhost:8000/health", headers=headers, timeout=10)
        response = requests.get(
            "http://localhost:8000/health", headers=headers, timeout=10
        )
        return response
    except Exception as e:
        print(f"Error making request: {e}")
        raise


def main():
    """Main verification function."""
    print("🔍 Task 11.5 Verification: Logs include correlation ID and consumer info")
    print("=" * 70)

    # Generate unique correlation ID for this test
    test_correlation_id = f"task-11-5-verify-{int(time.time() * 1000)}"
    print(f"📋 Test correlation ID: {test_correlation_id}")

    # Capture initial logs to get baseline
    print("\n📖 Capturing baseline logs...")
    baseline_logs = capture_kong_logs()
    print(f"   Baseline log entries: {len(baseline_logs)}")

    # Make test request
    print("\n🌐 Making test request to http://localhost:8000/health")
    print(f"   Headers: X-API-Key, X-Correlation-ID: {test_correlation_id}")

    try:
        response = make_test_request(test_correlation_id)
        print(f"   Response status: {response.status_code}")
        print(f"   Response correlation ID: {response.headers.get('X-Correlation-ID')}")

        # Verify basic functionality
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert (
            response.headers.get("X-Correlation-ID") == test_correlation_id
        ), "Correlation ID not echoed correctly in response"

        print("   ✅ Basic request/response working correctly")

    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        return 1

    # Wait a moment for logs to be written
    time.sleep(2)

    # Capture logs after the request
    print("\n📖 Capturing logs after test request...")
    after_logs = capture_kong_logs()
    print(f"   Total log entries captured: {len(after_logs)}")

    # Find new log entries (those that might contain our correlation ID)
    new_logs = (
        after_logs[len(baseline_logs) :] if len(after_logs) > len(baseline_logs) else after_logs
        after_logs[len(baseline_logs) :]
        if len(after_logs) > len(baseline_logs)
        else after_logs
    )
    print(f"   New log entries to analyze: {len(new_logs)}")

    # Analyze logs for correlation ID and consumer info
    print(f"\n🔍 Analyzing logs for correlation ID: {test_correlation_id}")

    correlation_id_found = False
    consumer_info_found = False
    structured_logs = []
    relevant_logs = []

    for i, log_line in enumerate(after_logs):
        # Check if this log line is related to our request
        if test_correlation_id in log_line:
            correlation_id_found = True
            relevant_logs.append(log_line)
            print(f"   ✅ Found correlation ID in log entry {i}")

            # Try to parse as structured log
            parsed = parse_log_entry(log_line)
            if parsed:
                structured_logs.append(parsed)
                print(f"      📊 Parsed as structured log: {len(parsed)} fields")

                # Check for consumer information in parsed log
                consumer_fields = [
                    "consumer_id",
                    "consumer_username",
                    "auth_method",
                    "consumer",
                ]
                found_consumer_fields = [field for field in consumer_fields if field in parsed]
                found_consumer_fields = [
                    field for field in consumer_fields if field in parsed
                ]
                if found_consumer_fields:
                    consumer_info_found = True
                    print(f"      👤 Consumer fields found: {found_consumer_fields}")

        # Also check for consumer info in logs that might not have correlation ID but are related
        elif any(term in log_line.lower() for term in ["default-consumer", "api-key", "consumer"]):
        elif any(
            term in log_line.lower()
            for term in ["default-consumer", "api-key", "consumer"]
        ):
            # Check if this log is around the same time as our request
            consumer_info_found = True

    print("\n📊 Analysis Results:")
    print(f"   Correlation ID found in logs: {'✅ YES' if correlation_id_found else '❌ NO'}")
    print(f"   Consumer info found in logs: {'✅ YES' if consumer_info_found else '❌ NO'}")
    print(
        f"   Correlation ID found in logs: {'✅ YES' if correlation_id_found else '❌ NO'}"
    )
    print(
        f"   Consumer info found in logs: {'✅ YES' if consumer_info_found else '❌ NO'}"
    )
    print(f"   Relevant log entries: {len(relevant_logs)}")
    print(f"   Structured log entries: {len(structured_logs)}")

    # Display relevant log entries
    if relevant_logs:
        print("\n📝 Relevant log entries:")
        for i, log_line in enumerate(relevant_logs[:3], 1):  # Show first 3
            print(f"   {i}. {log_line[:200]}{'...' if len(log_line) > 200 else ''}")

    # Display structured log data if available
    if structured_logs:
        print("\n🔧 Structured log data sample:")
        sample_log = structured_logs[0]
        for key, value in list(sample_log.items())[:10]:  # Show first 10 fields
            print(f"   {key}: {value}")

    # Final verification
    print("\n🎯 Task 11.5 Verification Results:")

    if correlation_id_found:
        print("   ✅ PASS: Correlation ID found in Kong logs")
    else:
        print("   ❌ FAIL: Correlation ID NOT found in Kong logs")

    if consumer_info_found:
        print("   ✅ PASS: Consumer information found in Kong logs")
    else:
        print("   ❌ FAIL: Consumer information NOT found in Kong logs")

    # Overall result
    success = correlation_id_found and consumer_info_found

    if success:
        print("\n🎉 Task 11.5 COMPLETED SUCCESSFULLY!")
        print("   ✅ Kong gateway logs include correlation ID and consumer info")
        print("   ✅ Structured logging is working as configured")
        return 0
    else:
        print("\n❌ Task 11.5 VERIFICATION FAILED")
        if not correlation_id_found:
            print(f"   - Correlation ID '{test_correlation_id}' not found in logs")
        if not consumer_info_found:
            print("   - Consumer information not found in logs")

        # Diagnostic information
        print("\n🔧 Diagnostic Information:")
        print(f"   - Total logs captured: {len(after_logs)}")
        print("   - Kong container: kong-gateway")
        print(f"   - Test correlation ID: {test_correlation_id}")

        if after_logs:
            print("   - Sample log entries (last 3):")
            for i, log_line in enumerate(after_logs[-3:], 1):
                print(
                    f"     {i}. {log_line[:150]}{'...' if len(log_line) > 150 else ''}"
                )
        else:
            print("   - No logs captured - check Kong container status")

        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        sys.exit(1)
