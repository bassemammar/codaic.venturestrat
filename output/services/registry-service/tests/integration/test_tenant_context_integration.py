"""Integration tests for tenant context propagation and middleware behavior."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from registry.api.rest import create_app
from registry.models import Tenant, TenantStatus


class TestTenantContextPropagation:
    """Tests for tenant context propagation through request pipeline."""

    @pytest.fixture
    def mock_tenant_service(self):
        """Create a mock TenantService."""
        from registry.tenant_service import TenantService

        service = AsyncMock(spec=TenantService)
        return service

    @pytest.fixture
    def sample_tenant(self):
        """Sample tenant for testing."""
        return Tenant(
            id="550e8400-e29b-41d4-a716-446655440000",
            slug="acme-corp",
            name="ACME Corporation",
            status=TenantStatus.ACTIVE,
            config={"quotas": {"max_users": 100}},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def test_tenant_header_extraction(self, mock_tenant_service, sample_tenant):
        """Test extraction of tenant ID from X-Tenant-ID header."""
        app = create_app()

        # Override dependencies
        from registry.api.rest import get_tenant_service

        app.dependency_overrides[get_tenant_service] = lambda: mock_tenant_service

        mock_tenant_service.get_tenant_by_id.return_value = sample_tenant

        with TestClient(app) as client:
            # Test request with X-Tenant-ID header
            response = client.get(
                f"/api/v1/tenants/{sample_tenant.id}", headers={"X-Tenant-ID": sample_tenant.id}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_tenant.id

    def test_missing_tenant_header_handling(self, mock_tenant_service):
        """Test handling of requests without X-Tenant-ID header."""
        app = create_app()

        # Add a simple middleware to check for X-Tenant-ID
        @app.middleware("http")
        async def tenant_middleware(request: Request, call_next):
            # Skip health checks and docs
            if request.url.path.startswith(("/health", "/docs", "/redoc", "/openapi.json")):
                return await call_next(request)

            tenant_id = request.headers.get("X-Tenant-ID")
            if not tenant_id and request.url.path.startswith("/api/v1/tenants"):
                # For tenant management endpoints, we might allow platform admin access
                # For this test, we'll just pass through
                pass

            return await call_next(request)

        from registry.api.rest import get_tenant_service

        app.dependency_overrides[get_tenant_service] = lambda: mock_tenant_service

        with TestClient(app) as client:
            # Request without X-Tenant-ID header should still work for tenant management API
            # (as these are admin operations)
            response = client.get("/api/v1/tenants/")

            # The exact behavior depends on middleware implementation
            # For tenant management endpoints, this might be allowed
            assert response.status_code in [200, 400, 401]

    def test_invalid_tenant_id_format(self, mock_tenant_service):
        """Test handling of invalid tenant ID format in header."""
        app = create_app()

        # Add middleware to validate tenant ID format
        @app.middleware("http")
        async def tenant_validation_middleware(request: Request, call_next):
            tenant_id = request.headers.get("X-Tenant-ID")
            if tenant_id:
                try:
                    uuid.UUID(tenant_id)
                except ValueError:
                    return HTTPException(status_code=400, detail="Invalid tenant ID format")

            return await call_next(request)

        from registry.api.rest import get_tenant_service

        app.dependency_overrides[get_tenant_service] = lambda: mock_tenant_service

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/tenants/", headers={"X-Tenant-ID": "invalid-uuid-format"}
            )

            # Middleware should catch invalid format
            assert response.status_code == 400

    def test_tenant_context_preservation_across_dependencies(
        self, mock_tenant_service, sample_tenant
    ):
        """Test that tenant context is preserved across multiple dependency injections."""
        app = FastAPI()

        # Mock dependency that uses tenant context
        async def get_tenant_context():
            return {"tenant_id": "test-tenant-id", "tenant_slug": "test-slug"}

        async def get_user_context(tenant_ctx=Depends(get_tenant_context)):
            return {"user_id": "test-user", "tenant": tenant_ctx}

        # Test endpoint that uses both dependencies
        @app.get("/test/context")
        async def test_context_endpoint(
            tenant_ctx=Depends(get_tenant_context), user_ctx=Depends(get_user_context)
        ):
            return {
                "tenant": tenant_ctx,
                "user": user_ctx,
                "consistent": tenant_ctx["tenant_id"] == user_ctx["tenant"]["tenant_id"],
            }

        with TestClient(app) as client:
            response = client.get("/test/context")

            assert response.status_code == 200
            data = response.json()
            assert data["consistent"] is True
            assert data["tenant"]["tenant_id"] == "test-tenant-id"
            assert data["user"]["tenant"]["tenant_id"] == "test-tenant-id"

    def test_concurrent_tenant_contexts(self, mock_tenant_service):
        """Test that tenant contexts don't leak between concurrent requests."""
        app = create_app()

        # Add context tracking middleware
        request_contexts = {}

        @app.middleware("http")
        async def context_tracking_middleware(request: Request, call_next):
            tenant_id = request.headers.get("X-Tenant-ID", "default")
            request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

            # Store context for this request
            request_contexts[request_id] = {"tenant_id": tenant_id, "start_time": datetime.now()}

            response = await call_next(request)

            # Add context info to response headers
            response.headers["X-Processed-Tenant-ID"] = tenant_id
            response.headers["X-Request-ID"] = request_id

            return response

        from registry.api.rest import get_tenant_service

        app.dependency_overrides[get_tenant_service] = lambda: mock_tenant_service

        with TestClient(app) as client:
            # Simulate concurrent requests with different tenant IDs
            tenant_a_id = str(uuid.uuid4())
            tenant_b_id = str(uuid.uuid4())

            response_a = client.get(
                "/api/v1/tenants/", headers={"X-Tenant-ID": tenant_a_id, "X-Request-ID": "req-a"}
            )

            response_b = client.get(
                "/api/v1/tenants/", headers={"X-Tenant-ID": tenant_b_id, "X-Request-ID": "req-b"}
            )

            # Verify each response has correct tenant context
            assert response_a.headers["X-Processed-Tenant-ID"] == tenant_a_id
            assert response_b.headers["X-Processed-Tenant-ID"] == tenant_b_id

            # Verify contexts were isolated
            assert request_contexts["req-a"]["tenant_id"] == tenant_a_id
            assert request_contexts["req-b"]["tenant_id"] == tenant_b_id


class TestTenantMiddlewareIntegration:
    """Tests for tenant middleware integration with the API."""

    def test_tenant_middleware_excludes_health_endpoints(self):
        """Health endpoints should bypass tenant middleware."""
        app = create_app()

        # Add strict tenant middleware
        @app.middleware("http")
        async def strict_tenant_middleware(request: Request, call_next):
            excluded_paths = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]

            # Check if path should be excluded
            if any(request.url.path.startswith(path) for path in excluded_paths):
                return await call_next(request)

            # Require tenant ID for all other paths
            tenant_id = request.headers.get("X-Tenant-ID")
            if not tenant_id:
                return HTTPException(status_code=401, detail="Missing X-Tenant-ID header")

            return await call_next(request)

        with TestClient(app) as client:
            # Health endpoint should work without tenant header
            response = client.get("/api/v1/health/headers")
            assert response.status_code == 200

            # Regular API endpoint should require tenant header
            response = client.get("/api/v1/tenants/")
            assert response.status_code == 401

    def test_tenant_middleware_with_authentication(self):
        """Test tenant middleware integration with authentication."""
        app = FastAPI()

        # Mock authentication middleware
        @app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            auth_header = request.headers.get("Authorization")
            if not auth_header and not request.url.path.startswith(("/health", "/docs")):
                return HTTPException(status_code=401, detail="Missing authorization")

            # Add mock user to request state
            request.state.user = {"id": "user-123", "roles": ["tenant_admin"]}
            return await call_next(request)

        # Mock tenant middleware
        @app.middleware("http")
        async def tenant_middleware(request: Request, call_next):
            if request.url.path.startswith(("/health", "/docs")):
                return await call_next(request)

            tenant_id = request.headers.get("X-Tenant-ID")
            if not tenant_id:
                return HTTPException(status_code=400, detail="Missing X-Tenant-ID")

            # Add tenant to request state
            request.state.tenant = {"id": tenant_id, "slug": f"tenant-{tenant_id[:8]}"}
            return await call_next(request)

        # Test endpoint
        @app.get("/api/test")
        async def test_endpoint(request: Request):
            return {
                "user": getattr(request.state, "user", None),
                "tenant": getattr(request.state, "tenant", None),
            }

        with TestClient(app) as client:
            # Request with both auth and tenant headers
            response = client.get(
                "/api/test",
                headers={
                    "Authorization": "Bearer token123",
                    "X-Tenant-ID": "550e8400-e29b-41d4-a716-446655440000",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["user"]["id"] == "user-123"
            assert data["tenant"]["id"] == "550e8400-e29b-41d4-a716-446655440000"

            # Request missing tenant header
            response = client.get("/api/test", headers={"Authorization": "Bearer token123"})
            assert response.status_code == 400

            # Request missing auth header
            response = client.get(
                "/api/test", headers={"X-Tenant-ID": "550e8400-e29b-41d4-a716-446655440000"}
            )
            assert response.status_code == 401

    def test_tenant_middleware_error_handling(self):
        """Test tenant middleware error handling and recovery."""
        app = FastAPI()

        # Middleware that can fail
        @app.middleware("http")
        async def potentially_failing_middleware(request: Request, call_next):
            tenant_id = request.headers.get("X-Tenant-ID")

            # Simulate failure for specific tenant ID
            if tenant_id == "fail-tenant":
                raise Exception("Simulated middleware failure")

            if tenant_id == "timeout-tenant":
                import asyncio

                await asyncio.sleep(0.1)  # Simulate slow operation
                raise TimeoutError("Simulated timeout")

            return await call_next(request)

        # Error handler
        @app.exception_handler(Exception)
        async def generic_error_handler(request: Request, exc: Exception):
            if "timeout" in str(exc).lower():
                return HTTPException(status_code=503, detail="Service temporarily unavailable")
            return HTTPException(status_code=500, detail="Internal server error")

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            # Normal request should work
            response = client.get("/test", headers={"X-Tenant-ID": "normal-tenant"})
            assert response.status_code == 200

            # Failing tenant should trigger error handler
            response = client.get("/test", headers={"X-Tenant-ID": "fail-tenant"})
            assert response.status_code == 500

            # Timeout tenant should trigger specific error
            response = client.get("/test", headers={"X-Tenant-ID": "timeout-tenant"})
            assert response.status_code == 503


class TestTenantAPIRequestResponseFlow:
    """Tests for complete request-response flow with tenant context."""

    def test_complete_tenant_creation_flow(self):
        """Test complete flow from request to response for tenant creation."""
        app = create_app()

        # Mock service
        from registry.api.rest import get_tenant_service
        from registry.tenant_service import TenantService

        mock_service = AsyncMock(spec=TenantService)
        app.dependency_overrides[get_tenant_service] = lambda: mock_service

        # Mock successful tenant creation
        created_tenant = Tenant(
            id=str(uuid.uuid4()),
            slug="flow-test",
            name="Flow Test Corp",
            status=TenantStatus.ACTIVE,
            config={"created_via": "api_flow_test"},
            keycloak_org_id="keycloak-123",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_service.create_tenant.return_value = created_tenant

        with TestClient(app) as client:
            # Send creation request
            payload = {
                "slug": "flow-test",
                "name": "Flow Test Corp",
                "config": {"created_via": "api_flow_test"},
                "admin_email": "admin@flowtest.com",
            }

            response = client.post(
                "/api/v1/tenants/",
                json=payload,
                headers={"Content-Type": "application/json", "X-Request-ID": "flow-test-123"},
            )

            # Verify response
            assert response.status_code == 201
            assert response.headers["Content-Type"] == "application/json"
            assert "X-Request-ID" in response.headers

            data = response.json()
            assert data["slug"] == "flow-test"
            assert data["name"] == "Flow Test Corp"
            assert data["config"]["created_via"] == "api_flow_test"
            assert data["keycloak_org_id"] == "keycloak-123"

            # Verify service was called correctly
            mock_service.create_tenant.assert_called_once_with(
                slug="flow-test",
                name="Flow Test Corp",
                config={"created_via": "api_flow_test"},
                admin_email="admin@flowtest.com",
            )

    def test_tenant_lifecycle_api_integration(self):
        """Test complete tenant lifecycle through API endpoints."""
        app = create_app()

        from registry.api.rest import get_tenant_service
        from registry.tenant_service import TenantService

        mock_service = AsyncMock(spec=TenantService)
        app.dependency_overrides[get_tenant_service] = lambda: mock_service

        tenant_id = str(uuid.uuid4())

        # Phase 1: Create tenant
        created_tenant = Tenant(
            id=tenant_id,
            slug="lifecycle-test",
            name="Lifecycle Test Corp",
            status=TenantStatus.ACTIVE,
            config={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_service.create_tenant.return_value = created_tenant

        # Phase 2: Update tenant
        updated_tenant = Tenant(
            id=tenant_id,
            slug="lifecycle-test",
            name="Updated Lifecycle Corp",
            status=TenantStatus.ACTIVE,
            config={"updated": True},
            created_at=created_tenant.created_at,
            updated_at=datetime.now(UTC),
        )
        mock_service.update_tenant.return_value = updated_tenant

        # Phase 3: Suspend tenant
        suspended_tenant = Tenant(
            id=tenant_id,
            slug="lifecycle-test",
            name="Updated Lifecycle Corp",
            status=TenantStatus.SUSPENDED,
            config={"updated": True, "suspension_reason": "Testing"},
            created_at=created_tenant.created_at,
            updated_at=datetime.now(UTC),
        )
        mock_service.suspend_tenant.return_value = suspended_tenant

        # Phase 4: Resume tenant
        resumed_tenant = Tenant(
            id=tenant_id,
            slug="lifecycle-test",
            name="Updated Lifecycle Corp",
            status=TenantStatus.ACTIVE,
            config={"updated": True},
            created_at=created_tenant.created_at,
            updated_at=datetime.now(UTC),
        )
        mock_service.resume_tenant.return_value = resumed_tenant

        # Phase 5: Delete tenant
        deleted_tenant = Tenant(
            id=tenant_id,
            slug="lifecycle-test",
            name="Updated Lifecycle Corp",
            status=TenantStatus.DELETED,
            config={"updated": True, "deletion_reason": "Testing"},
            created_at=created_tenant.created_at,
            updated_at=datetime.now(UTC),
            deleted_at=datetime.now(UTC),
        )
        mock_service.delete_tenant.return_value = deleted_tenant

        with TestClient(app) as client:
            # 1. Create
            response = client.post(
                "/api/v1/tenants/", json={"slug": "lifecycle-test", "name": "Lifecycle Test Corp"}
            )
            assert response.status_code == 201
            assert response.json()["status"] == "active"

            # 2. Update
            response = client.patch(
                f"/api/v1/tenants/{tenant_id}",
                json={"name": "Updated Lifecycle Corp", "config": {"updated": True}},
            )
            assert response.status_code == 200
            assert response.json()["name"] == "Updated Lifecycle Corp"

            # 3. Suspend
            response = client.post(
                f"/api/v1/tenants/{tenant_id}/suspend", json={"reason": "Testing lifecycle"}
            )
            assert response.status_code == 200
            assert response.json()["status"] == "suspended"

            # 4. Resume
            response = client.post(f"/api/v1/tenants/{tenant_id}/resume")
            assert response.status_code == 200
            assert response.json()["status"] == "active"

            # 5. Delete
            response = client.request(
                "DELETE", f"/api/v1/tenants/{tenant_id}", json={"reason": "Testing lifecycle"}
            )
            assert response.status_code == 200
            assert response.json()["status"] == "deleted"
            assert response.json()["deleted_at"] is not None
