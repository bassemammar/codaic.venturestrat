"""Tests for TenantService proto definitions - TDD approach.

These tests validate the TenantService proto message structure,
enums, and gRPC service definitions.
"""

from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.timestamp_pb2 import Timestamp

# Import the generated tenant proto classes
from registry.grpc.tenant_pb2 import (
    # Request/Response Messages
    CreateTenantRequest,
    ExportStatusResponse,
    ExportTenantDataRequest,
    GetTenantRequest,
    # Health Messages
    HealthCheckRequest,
    HealthCheckResponse,
    ListTenantsRequest,
    ListTenantsResponse,
    QuotaInfo,
    # Data Models
    Tenant,
    TenantChangeEvent,
    TenantQuotasResponse,
    TenantStatus,
    UpdateTenantRequest,
)
from registry.grpc.tenant_pb2_grpc import (
    HealthServicer,
    TenantServiceServicer,
    TenantServiceStub,
    add_HealthServicer_to_server,
    add_TenantServiceServicer_to_server,
)

# =============================================================================
# Proto Message Structure Tests
# =============================================================================


class TestTenantProtoMessages:
    """Tests for tenant proto message structure and validation."""

    def test_create_tenant_request_structure(self):
        """CreateTenantRequest has all required fields."""
        request = CreateTenantRequest(
            slug="test-tenant",
            name="Test Tenant",
            config={"max_users": "100", "environment": "dev"},
            admin_email="admin@test.com",
        )

        assert request.slug == "test-tenant"
        assert request.name == "Test Tenant"
        assert request.config["max_users"] == "100"
        assert request.config["environment"] == "dev"
        assert request.admin_email == "admin@test.com"

    def test_tenant_message_structure(self):
        """Tenant message has all required fields and proper types."""
        # Create timestamps
        now = Timestamp()
        now.GetCurrentTime()

        tenant = Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="acme-corp",
            name="ACME Corporation",
            status=TenantStatus.TENANT_STATUS_ACTIVE,
            config={"theme": "dark", "max_users": "100"},
            keycloak_org_id="org-123",
            created_at=now,
            updated_at=now,
            created_by="system",
        )

        assert tenant.id == "550e8400-e29b-41d4-a716-446655440000"
        assert tenant.slug == "acme-corp"
        assert tenant.name == "ACME Corporation"
        assert tenant.status == TenantStatus.TENANT_STATUS_ACTIVE
        assert tenant.config["theme"] == "dark"
        assert tenant.keycloak_org_id == "org-123"
        assert tenant.created_by == "system"

    def test_tenant_status_enum_values(self):
        """TenantStatus enum has all expected values."""
        assert TenantStatus.TENANT_STATUS_UNKNOWN == 0
        assert TenantStatus.TENANT_STATUS_ACTIVE == 1
        assert TenantStatus.TENANT_STATUS_SUSPENDED == 2
        assert TenantStatus.TENANT_STATUS_DELETED == 3

    def test_list_tenants_request_optional_fields(self):
        """ListTenantsRequest handles optional fields correctly."""
        # Request with all fields
        request_full = ListTenantsRequest(
            page_size=50, page_token="token123", status="active", search="acme"
        )
        assert request_full.page_size == 50
        assert request_full.page_token == "token123"
        assert request_full.status == "active"
        assert request_full.search == "acme"

        # Request with minimal fields
        request_minimal = ListTenantsRequest(page_size=25, page_token="token456")
        assert request_minimal.page_size == 25
        assert request_minimal.page_token == "token456"
        # Optional fields should have defaults or be unset
        assert not request_minimal.HasField("status")
        assert not request_minimal.HasField("search")

    def test_update_tenant_request_optional_fields(self):
        """UpdateTenantRequest handles optional name field correctly."""
        # Request with name update
        request_with_name = UpdateTenantRequest(
            tenant_id="tenant-123", name="New Name", config={"updated": "true"}
        )
        assert request_with_name.tenant_id == "tenant-123"
        assert request_with_name.name == "New Name"
        assert request_with_name.config["updated"] == "true"
        assert request_with_name.HasField("name")

        # Request without name update
        request_without_name = UpdateTenantRequest(
            tenant_id="tenant-123", config={"updated": "true"}
        )
        assert request_without_name.tenant_id == "tenant-123"
        assert request_without_name.config["updated"] == "true"
        assert not request_without_name.HasField("name")

    def test_quota_info_structure(self):
        """QuotaInfo message has correct field types."""
        quota = QuotaInfo(limit=1000, current=750, usage_percentage=75.0)

        assert quota.limit == 1000
        assert quota.current == 750
        assert quota.usage_percentage == 75.0

    def test_tenant_quotas_response_structure(self):
        """TenantQuotasResponse handles map of quotas correctly."""
        response = TenantQuotasResponse(
            tenant_id="tenant-123",
            quotas={
                "max_users": QuotaInfo(limit=100, current=85, usage_percentage=85.0),
                "api_calls": QuotaInfo(limit=50000, current=12500, usage_percentage=25.0),
            },
        )

        assert response.tenant_id == "tenant-123"
        assert len(response.quotas) == 2
        assert response.quotas["max_users"].limit == 100
        assert response.quotas["api_calls"].current == 12500

    def test_tenant_change_event_structure(self):
        """TenantChangeEvent has all required fields."""
        now = Timestamp()
        now.GetCurrentTime()

        tenant = Tenant(
            id="tenant-123",
            slug="test-slug",
            name="Test Tenant",
            status=TenantStatus.TENANT_STATUS_ACTIVE,
        )

        event = TenantChangeEvent(
            event_type=TenantChangeEvent.EventType.CREATED,
            tenant=tenant,
            change_token="change-123",
            timestamp=now,
            changed_by="admin-user",
            reason="Initial creation",
        )

        assert event.event_type == TenantChangeEvent.EventType.CREATED
        assert event.tenant.id == "tenant-123"
        assert event.change_token == "change-123"
        assert event.changed_by == "admin-user"
        assert event.reason == "Initial creation"

    def test_tenant_change_event_enum_values(self):
        """TenantChangeEvent.EventType enum has all expected values."""
        assert TenantChangeEvent.EventType.UNKNOWN == 0
        assert TenantChangeEvent.EventType.CREATED == 1
        assert TenantChangeEvent.EventType.UPDATED == 2
        assert TenantChangeEvent.EventType.SUSPENDED == 3
        assert TenantChangeEvent.EventType.RESUMED == 4
        assert TenantChangeEvent.EventType.DELETED == 5

    def test_export_status_response_optional_fields(self):
        """ExportStatusResponse handles optional fields correctly."""
        # Completed export response
        response_completed = ExportStatusResponse(
            export_id="export-123",
            status="completed",
            download_url="https://example.com/download",
        )
        assert response_completed.export_id == "export-123"
        assert response_completed.status == "completed"
        assert response_completed.download_url == "https://example.com/download"
        assert response_completed.HasField("download_url")
        assert not response_completed.HasField("error_message")

        # Failed export response
        response_failed = ExportStatusResponse(
            export_id="export-456", status="failed", error_message="Export timeout"
        )
        assert response_failed.export_id == "export-456"
        assert response_failed.status == "failed"
        assert response_failed.error_message == "Export timeout"
        assert response_failed.HasField("error_message")
        assert not response_failed.HasField("download_url")

    def test_health_check_messages(self):
        """Health check messages follow standard gRPC health protocol."""
        request = HealthCheckRequest(service="TenantService")
        assert request.service == "TenantService"

        response = HealthCheckResponse(status=HealthCheckResponse.ServingStatus.SERVING)
        assert response.status == HealthCheckResponse.ServingStatus.SERVING

    def test_health_check_serving_status_enum(self):
        """HealthCheckResponse.ServingStatus has standard values."""
        assert HealthCheckResponse.ServingStatus.UNKNOWN == 0
        assert HealthCheckResponse.ServingStatus.SERVING == 1
        assert HealthCheckResponse.ServingStatus.NOT_SERVING == 2
        assert HealthCheckResponse.ServingStatus.SERVICE_UNKNOWN == 3


# =============================================================================
# Proto JSON Serialization Tests
# =============================================================================


class TestTenantProtoSerialization:
    """Tests for proto message JSON serialization/deserialization."""

    def test_tenant_to_json_conversion(self):
        """Tenant message converts to/from JSON correctly."""
        now = Timestamp()
        now.GetCurrentTime()

        tenant = Tenant(
            id="tenant-123",
            slug="test-tenant",
            name="Test Tenant",
            status=TenantStatus.TENANT_STATUS_ACTIVE,
            config={"env": "production"},
            created_at=now,
            updated_at=now,
            created_by="admin",
        )

        # Convert to dict/JSON
        tenant_dict = MessageToDict(tenant)
        assert tenant_dict["id"] == "tenant-123"
        assert tenant_dict["slug"] == "test-tenant"
        assert tenant_dict["status"] == "TENANT_STATUS_ACTIVE"
        assert tenant_dict["config"]["env"] == "production"

        # Convert back from dict
        tenant_restored = ParseDict(tenant_dict, Tenant())
        assert tenant_restored.id == "tenant-123"
        assert tenant_restored.slug == "test-tenant"
        assert tenant_restored.status == TenantStatus.TENANT_STATUS_ACTIVE

    def test_list_tenants_response_json(self):
        """ListTenantsResponse serializes correctly with tenant list."""
        tenant1 = Tenant(
            id="tenant-1",
            slug="tenant-one",
            name="Tenant One",
            status=TenantStatus.TENANT_STATUS_ACTIVE,
        )
        tenant2 = Tenant(
            id="tenant-2",
            slug="tenant-two",
            name="Tenant Two",
            status=TenantStatus.TENANT_STATUS_SUSPENDED,
        )

        response = ListTenantsResponse(
            tenants=[tenant1, tenant2], next_page_token="next-page-123", total_count=42
        )

        response_dict = MessageToDict(response)
        assert len(response_dict["tenants"]) == 2
        assert response_dict["tenants"][0]["id"] == "tenant-1"
        assert response_dict["tenants"][1]["status"] == "TENANT_STATUS_SUSPENDED"
        assert response_dict["nextPageToken"] == "next-page-123"
        assert response_dict["totalCount"] == 42


# =============================================================================
# gRPC Service Interface Tests
# =============================================================================


class TestTenantServiceInterface:
    """Tests for gRPC service interface definitions."""

    def test_tenant_service_stub_creation(self):
        """TenantServiceStub can be instantiated."""
        # Mock channel for testing
        from unittest.mock import Mock

        mock_channel = Mock()

        stub = TenantServiceStub(mock_channel)
        assert stub is not None

    def test_tenant_servicer_interface(self):
        """TenantServiceServicer has all required methods."""
        servicer = TenantServiceServicer()

        # Check that all RPC methods exist
        assert hasattr(servicer, "CreateTenant")
        assert hasattr(servicer, "GetTenant")
        assert hasattr(servicer, "GetTenantBySlug")
        assert hasattr(servicer, "UpdateTenant")
        assert hasattr(servicer, "DeleteTenant")
        assert hasattr(servicer, "ListTenants")
        assert hasattr(servicer, "SuspendTenant")
        assert hasattr(servicer, "ResumeTenant")
        assert hasattr(servicer, "ExportTenantData")
        assert hasattr(servicer, "GetExportStatus")
        assert hasattr(servicer, "GetTenantQuotas")
        assert hasattr(servicer, "UpdateTenantQuotas")
        assert hasattr(servicer, "WatchTenantChanges")

    def test_health_service_interface(self):
        """Health service has standard gRPC health interface."""
        servicer = HealthServicer()

        assert hasattr(servicer, "Check")
        assert hasattr(servicer, "Watch")

    def test_server_registration_functions_exist(self):
        """Server registration functions are available."""
        # These functions should exist for registering servicers
        assert callable(add_TenantServiceServicer_to_server)
        assert callable(add_HealthServicer_to_server)


# =============================================================================
# Proto Validation Tests
# =============================================================================


class TestTenantProtoValidation:
    """Tests for proto message validation edge cases."""

    def test_empty_messages_handle_gracefully(self):
        """Empty proto messages can be created without errors."""
        # These should not raise exceptions
        empty_request = GetTenantRequest()
        empty_tenant = Tenant()
        empty_response = ListTenantsResponse()

        assert empty_request is not None
        assert empty_tenant is not None
        assert empty_response is not None

    def test_config_map_field_operations(self):
        """Config map fields support standard dict operations."""
        tenant = Tenant()

        # Add config items
        tenant.config["key1"] = "value1"
        tenant.config["key2"] = "value2"

        assert len(tenant.config) == 2
        assert "key1" in tenant.config
        assert tenant.config["key1"] == "value1"

        # Remove config item
        del tenant.config["key1"]
        assert len(tenant.config) == 1
        assert "key1" not in tenant.config

    def test_repeated_fields_operations(self):
        """Repeated fields support list operations."""
        request = ExportTenantDataRequest(tenant_id="tenant-123", format="json")

        # Add data types
        request.data_types.append("quotes")
        request.data_types.append("trades")
        request.data_types.extend(["curves", "users"])

        assert len(request.data_types) == 4
        assert "quotes" in request.data_types
        assert request.data_types[1] == "trades"

    def test_timestamp_field_handling(self):
        """Timestamp fields work with google.protobuf.Timestamp."""
        tenant = Tenant(id="tenant-123", slug="test", name="Test")

        # Set current time
        now = Timestamp()
        now.GetCurrentTime()

        tenant.created_at.CopyFrom(now)
        tenant.updated_at.CopyFrom(now)

        assert tenant.created_at.seconds > 0
        assert tenant.updated_at.seconds > 0

    def test_oneof_field_behavior(self):
        """Optional fields behave correctly with HasField."""
        request = UpdateTenantRequest(tenant_id="tenant-123")

        # Initially no name set
        assert not request.HasField("name")

        # Set name
        request.name = "New Name"
        assert request.HasField("name")
        assert request.name == "New Name"

        # Clear name
        request.ClearField("name")
        assert not request.HasField("name")
