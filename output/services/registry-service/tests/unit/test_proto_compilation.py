"""Tests for protobuf compilation and validation.

These tests ensure that the protobuf files can be compiled successfully
and that the generated messages have the expected structure.
"""
import pytest
import os
import subprocess
from pathlib import Path


class TestProtoCompilation:
    """Tests for protobuf compilation."""

    def test_tenant_service_proto_exists(self):
        """tenant_service.proto file exists in the correct location."""
        proto_file = Path("protos/tenant_service.proto")
        assert proto_file.exists(), f"Proto file not found at {proto_file}"

    def test_tenant_service_proto_syntax(self):
        """tenant_service.proto has valid protobuf syntax."""
        proto_file = Path("protos/tenant_service.proto")

        # Read the proto file and verify basic structure
        with open(proto_file, 'r') as f:
            content = f.read()

        # Check for required protobuf elements
        assert 'syntax = "proto3";' in content
        assert 'package venturestrat.registry.tenant.v1;' in content
        assert 'service TenantService' in content

        # Check for essential message types
        assert 'message Tenant' in content
        assert 'message CreateTenantRequest' in content
        assert 'message CreateTenantResponse' in content
        assert 'message ListTenantsRequest' in content
        assert 'message ListTenantsResponse' in content

        # Check for enum
        assert 'enum TenantStatus' in content

    def test_registry_proto_still_exists(self):
        """Original registry.proto file still exists."""
        proto_file = Path("protos/registry.proto")
        assert proto_file.exists(), f"Registry proto file not found at {proto_file}"

    def test_proto_file_structure(self):
        """Proto files have the expected structure and comments."""
        proto_file = Path("protos/tenant_service.proto")

        with open(proto_file, 'r') as f:
            content = f.read()

        # Check for proper documentation sections
        assert 'VentureStrat Tenant Service - gRPC API' in content
        assert 'Multi-tenancy management' in content

        # Check for organized sections
        assert 'Tenant Service' in content
        assert 'Tenant Messages' in content
        assert 'Create Tenant Messages' in content
        assert 'List Tenants Messages' in content
        assert 'Tenant Lifecycle Messages' in content
        assert 'Health Check Messages' in content

    def test_service_methods_defined(self):
        """All expected service methods are defined in the proto."""
        proto_file = Path("protos/tenant_service.proto")

        with open(proto_file, 'r') as f:
            content = f.read()

        # Check for all expected RPC methods
        expected_methods = [
            'rpc CreateTenant',
            'rpc GetTenant',
            'rpc GetTenantBySlug',
            'rpc ListTenants',
            'rpc UpdateTenant',
            'rpc SuspendTenant',
            'rpc ResumeTenant',
            'rpc DeleteTenant',
            'rpc PurgeTenant',
            'rpc GetSystemTenant',
            'rpc GetTenantsForPurge',
            'rpc HealthCheck'
        ]

        for method in expected_methods:
            assert method in content, f"Method {method} not found in proto file"

    def test_tenant_status_enum_values(self):
        """TenantStatus enum has all expected values."""
        proto_file = Path("protos/tenant_service.proto")

        with open(proto_file, 'r') as f:
            content = f.read()

        # Check for enum values
        assert 'TENANT_STATUS_UNSPECIFIED = 0' in content
        assert 'TENANT_STATUS_ACTIVE = 1' in content
        assert 'TENANT_STATUS_SUSPENDED = 2' in content
        assert 'TENANT_STATUS_DELETED = 3' in content

    def test_message_field_numbers_unique(self):
        """Proto message fields have unique field numbers."""
        proto_file = Path("protos/tenant_service.proto")

        with open(proto_file, 'r') as f:
            content = f.read()

        # This is a basic check - in practice, protoc would catch this
        # Check that we don't have obvious duplicates like "= 1;" appearing
        # too many times in the same message block

        # Split into message blocks and check each one
        lines = content.split('\n')
        in_message = False
        current_message = ""
        field_numbers = set()

        for line in lines:
            line = line.strip()

            if line.startswith('message ') and line.endswith(' {'):
                in_message = True
                current_message = line
                field_numbers = set()
            elif in_message and line == '}':
                in_message = False
                field_numbers = set()
            elif in_message and '=' in line and line.endswith(';'):
                # Extract field number
                try:
                    field_num = line.split('=')[1].strip().rstrip(';').strip()
                    if field_num.isdigit():
                        num = int(field_num)
                        assert num not in field_numbers, f"Duplicate field number {num} in {current_message}"
                        field_numbers.add(num)
                except (IndexError, ValueError):
                    # Skip lines that don't match expected pattern
                    pass

    def test_proto_package_consistency(self):
        """Proto package follows VentureStrat naming conventions."""
        proto_file = Path("protos/tenant_service.proto")

        with open(proto_file, 'r') as f:
            content = f.read()

        # Check package naming
        assert 'package venturestrat.registry.tenant.v1;' in content

        # Package should follow the pattern: venturestrat.<service>.<feature>.v<version>
        # Here: venturestrat.registry.tenant.v1 makes sense for tenant functionality in registry service

    @pytest.mark.skipif(
        subprocess.run(['which', 'protoc'], capture_output=True).returncode != 0,
        reason="protoc compiler not available"
    )
    def test_proto_compilation_with_protoc(self):
        """Proto file compiles successfully with protoc (if available)."""
        proto_file = Path("protos/tenant_service.proto")

        # Try to compile the proto file to check for syntax errors
        result = subprocess.run([
            'protoc',
            '--proto_path=protos',
            '--python_out=/tmp',  # Output to temp directory
            str(proto_file)
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Proto compilation failed: {result.stderr}"