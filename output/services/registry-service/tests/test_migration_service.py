"""
Tests for the registry migration service.

These tests verify the multi-tenant migration process including:
- Pre-migration validation
- Migration execution
- Post-migration verification
- Rollback functionality
"""

from unittest.mock import patch

import asyncpg
import pytest
from registry.migration_service import SYSTEM_TENANT_ID, RegistryMigrationService


class TestRegistryMigrationService:
    """Test cases for the registry migration service."""

    @pytest.fixture
    async def migration_service(self, test_db_url):
        """Create migration service with test database."""
        return RegistryMigrationService(test_db_url)

    @pytest.fixture
    async def test_db_connection(self, test_db_url):
        """Create test database connection."""
        conn = await asyncpg.connect(test_db_url)
        yield conn
        await conn.close()

    @pytest.fixture
    async def setup_pre_migration_state(self, test_db_connection):
        """Set up database state before migration."""
        conn = test_db_connection

        # Create tenants table and system tenant
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tenants (
                id UUID PRIMARY KEY,
                slug VARCHAR(63) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                config JSONB DEFAULT '{}',
                keycloak_org_id VARCHAR(36),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                deleted_at TIMESTAMPTZ,
                CONSTRAINT valid_tenant_status CHECK (status IN ('active', 'suspended', 'deleted'))
            )
        """
        )

        await conn.execute(
            """
            INSERT INTO tenants (id, slug, name, status, config)
            VALUES ($1, 'system', 'System', 'active', '{"is_system": true}')
            ON CONFLICT (id) DO NOTHING
        """,
            SYSTEM_TENANT_ID,
        )

        # Create registry tables without tenant_id
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS service_registrations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                service_name VARCHAR(100) NOT NULL,
                instance_id VARCHAR(200) NOT NULL,
                version VARCHAR(50) NOT NULL,
                address INET NOT NULL,
                port INTEGER NOT NULL,
                protocol VARCHAR(10) NOT NULL,
                tags TEXT[] DEFAULT '{}',
                metadata JSONB DEFAULT '{}',
                manifest JSONB,
                registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                deregistered_at TIMESTAMPTZ,
                deregistration_reason VARCHAR(50),
                CONSTRAINT valid_protocol CHECK (protocol IN ('http', 'grpc', 'tcp')),
                CONSTRAINT valid_port CHECK (port > 0 AND port < 65536)
            )
        """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS service_health_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                service_name VARCHAR(100) NOT NULL,
                instance_id VARCHAR(200) NOT NULL,
                previous_status VARCHAR(20),
                new_status VARCHAR(20) NOT NULL,
                check_name VARCHAR(100),
                check_output TEXT,
                event_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT valid_status CHECK (new_status IN ('healthy', 'warning', 'critical'))
            )
        """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS service_dependencies (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                service_name VARCHAR(100) NOT NULL,
                depends_on VARCHAR(100) NOT NULL,
                version_constraint VARCHAR(50) NOT NULL,
                discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_verified_at TIMESTAMPTZ,
                UNIQUE(service_name, depends_on)
            )
        """
        )

        # Insert test data
        await conn.execute(
            """
            INSERT INTO service_registrations
            (service_name, instance_id, version, address, port, protocol)
            VALUES
            ('pricing-service', 'pricing-001', '1.0.0', '192.168.1.10', 8080, 'http'),
            ('trading-service', 'trading-001', '1.2.0', '192.168.1.11', 8081, 'http')
        """
        )

        await conn.execute(
            """
            INSERT INTO service_health_events
            (service_name, instance_id, new_status, check_name)
            VALUES
            ('pricing-service', 'pricing-001', 'healthy', 'health_check'),
            ('trading-service', 'trading-001', 'healthy', 'health_check')
        """
        )

        await conn.execute(
            """
            INSERT INTO service_dependencies
            (service_name, depends_on, version_constraint)
            VALUES
            ('trading-service', 'pricing-service', '>=1.0.0'),
            ('pricing-service', 'reference-data-service', '>=2.0.0')
        """
        )

    @pytest.mark.asyncio
    async def test_validate_pre_migration_success(
        self, migration_service, setup_pre_migration_state
    ):
        """Test successful pre-migration validation."""
        result = await migration_service._validate_pre_migration()

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_pre_migration_no_tenant_table(
        self, migration_service, test_db_connection
    ):
        """Test validation failure when tenant table doesn't exist."""
        result = await migration_service._validate_pre_migration()

        assert result["valid"] is False
        assert any("Tenants table does not exist" in error for error in result["errors"])

    @pytest.mark.asyncio
    async def test_validate_pre_migration_no_system_tenant(
        self, migration_service, test_db_connection
    ):
        """Test validation failure when system tenant doesn't exist."""
        # Create tenants table but no system tenant
        await test_db_connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tenants (
                id UUID PRIMARY KEY,
                slug VARCHAR(63) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active'
            )
        """
        )

        result = await migration_service._validate_pre_migration()

        assert result["valid"] is False
        assert any("System tenant does not exist" in error for error in result["errors"])

    @pytest.mark.asyncio
    async def test_collect_pre_migration_stats(self, migration_service, setup_pre_migration_state):
        """Test collection of pre-migration statistics."""
        stats = await migration_service._collect_pre_migration_stats()

        # Check record counts
        assert stats["service_registrations_count"] == 2
        assert stats["service_health_events_count"] == 2
        assert stats["service_dependencies_count"] == 2

        # Check that constraints and indexes exist
        assert "existing_constraints" in stats
        assert "existing_indexes" in stats

    @pytest.mark.asyncio
    async def test_dry_run_migration(self, migration_service, setup_pre_migration_state):
        """Test dry run migration (validation only)."""
        result = await migration_service.execute_migration(dry_run=True)

        assert result["status"] == "dry_run_success"
        assert "pre_stats" in result
        assert "validation" in result
        assert result["validation"]["valid"] is True

        # Verify no changes were made
        stats = await migration_service._collect_pre_migration_stats()
        assert stats["service_registrations_count"] == 2

    @pytest.mark.asyncio
    async def test_migration_execution_success(self, migration_service, setup_pre_migration_state):
        """Test successful migration execution."""
        # Mock the migration file to return our test SQL
        test_sql = """
        BEGIN;

        ALTER TABLE service_registrations
        ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

        ALTER TABLE service_health_events
        ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

        ALTER TABLE service_dependencies
        ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

        -- Add foreign key constraints
        ALTER TABLE service_registrations
        ADD CONSTRAINT fk_service_registrations_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

        ALTER TABLE service_health_events
        ADD CONSTRAINT fk_service_health_events_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

        ALTER TABLE service_dependencies
        ADD CONSTRAINT fk_service_dependencies_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

        -- Add indexes
        CREATE INDEX idx_service_registrations_tenant_id ON service_registrations(tenant_id);
        CREATE INDEX idx_service_health_events_tenant_id ON service_health_events(tenant_id);
        CREATE INDEX idx_service_dependencies_tenant_id ON service_dependencies(tenant_id);

        COMMIT;
        """

        with patch.object(migration_service.migration_file, "read_text", return_value=test_sql):
            with patch.object(migration_service.migration_file, "exists", return_value=True):
                result = await migration_service.execute_migration(dry_run=False)

        assert result["status"] == "success"
        assert "execution_time" in result
        assert "pre_stats" in result
        assert "post_stats" in result
        assert "verification" in result
        assert result["verification"]["valid"] is True

        # Verify changes were made
        post_stats = result["post_stats"]
        assert post_stats["service_registrations_system_tenant_count"] == 2
        assert post_stats["service_health_events_system_tenant_count"] == 2
        assert post_stats["service_dependencies_system_tenant_count"] == 2

    @pytest.mark.asyncio
    async def test_verify_migration_success(
        self, migration_service, setup_pre_migration_state, test_db_connection
    ):
        """Test verification of completed migration."""
        # Manually add tenant columns to simulate migration
        await test_db_connection.execute(
            """
            ALTER TABLE service_registrations
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        await test_db_connection.execute(
            """
            ALTER TABLE service_health_events
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        await test_db_connection.execute(
            """
            ALTER TABLE service_dependencies
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        result = await migration_service.verify_migration()

        assert result["status"] == "migrated"
        assert result["schema_check"]["has_tenant_columns"] is True

    @pytest.mark.asyncio
    async def test_verify_migration_not_applied(self, migration_service, setup_pre_migration_state):
        """Test verification when migration hasn't been applied."""
        result = await migration_service.verify_migration()

        assert result["status"] == "not_migrated"
        assert result["schema_check"]["has_tenant_columns"] is False

    @pytest.mark.asyncio
    async def test_rollback_migration(
        self, migration_service, setup_pre_migration_state, test_db_connection
    ):
        """Test migration rollback functionality."""
        # First apply migration
        await test_db_connection.execute(
            """
            ALTER TABLE service_registrations
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        await test_db_connection.execute(
            """
            ALTER TABLE service_health_events
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        await test_db_connection.execute(
            """
            ALTER TABLE service_dependencies
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        # Now test rollback
        result = await migration_service.rollback_migration()

        assert result["status"] == "rollback_success"
        assert "execution_time" in result

        # Verify tenant columns were removed
        columns = await test_db_connection.fetch(
            """
            SELECT table_name
            FROM information_schema.columns
            WHERE table_name IN ('service_registrations', 'service_health_events', 'service_dependencies')
            AND column_name = 'tenant_id'
        """
        )

        assert len(columns) == 0

    @pytest.mark.asyncio
    async def test_data_integrity_verification(
        self, migration_service, setup_pre_migration_state, test_db_connection
    ):
        """Test data integrity verification."""
        # Add tenant columns
        await test_db_connection.execute(
            """
            ALTER TABLE service_registrations
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        await test_db_connection.execute(
            """
            ALTER TABLE service_health_events
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        await test_db_connection.execute(
            """
            ALTER TABLE service_dependencies
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        # Add foreign key constraints
        await test_db_connection.execute(
            """
            ALTER TABLE service_registrations
            ADD CONSTRAINT fk_service_registrations_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT
        """
        )

        result = await migration_service._verify_data_integrity()

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_foreign_key_constraint_enforcement(
        self, migration_service, setup_pre_migration_state, test_db_connection
    ):
        """Test that foreign key constraints are properly enforced."""
        # Add tenant column and constraint
        await test_db_connection.execute(
            """
            ALTER TABLE service_registrations
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        await test_db_connection.execute(
            """
            ALTER TABLE service_registrations
            ADD CONSTRAINT fk_service_registrations_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT
        """
        )

        # Try to insert with invalid tenant_id (should fail)
        with pytest.raises(asyncpg.ForeignKeyViolationError):
            await test_db_connection.execute(
                """
                INSERT INTO service_registrations
                (service_name, instance_id, version, address, port, protocol, tenant_id)
                VALUES ('test', 'test', '1.0', '127.0.0.1', 8080, 'http', '11111111-1111-1111-1111-111111111111')
            """
            )

    @pytest.mark.asyncio
    async def test_migration_verification_failure(
        self, migration_service, setup_pre_migration_state
    ):
        """Test migration verification failure scenarios."""
        pre_stats = {
            "service_registrations_count": 2,
            "service_health_events_count": 2,
            "service_dependencies_count": 2,
        }

        # Post stats with different record count (simulating data loss)
        post_stats = {
            "service_registrations_count": 1,  # Lost a record!
            "service_health_events_count": 2,
            "service_dependencies_count": 2,
            "service_registrations_system_tenant_count": 1,
            "service_health_events_system_tenant_count": 2,
            "service_dependencies_system_tenant_count": 2,
            "new_tenant_constraints": [],
            "new_tenant_indexes": [],
        }

        result = await migration_service._verify_migration(pre_stats, post_stats)

        assert result["valid"] is False
        assert any("record count changed" in error for error in result["errors"])

    @pytest.mark.asyncio
    async def test_schema_check(
        self, migration_service, setup_pre_migration_state, test_db_connection
    ):
        """Test schema checking functionality."""
        # Before adding columns
        result = await migration_service._check_tenant_schema()
        assert result["has_tenant_columns"] is False
        assert len(result["tables_with_tenant"]) == 0

        # Add tenant column to one table
        await test_db_connection.execute(
            """
            ALTER TABLE service_registrations
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        result = await migration_service._check_tenant_schema()
        assert result["has_tenant_columns"] is False  # Not all tables have it
        assert len(result["tables_with_tenant"]) == 1

        # Add to remaining tables
        await test_db_connection.execute(
            """
            ALTER TABLE service_health_events
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        await test_db_connection.execute(
            """
            ALTER TABLE service_dependencies
            ADD COLUMN tenant_id UUID NOT NULL DEFAULT $1
        """,
            SYSTEM_TENANT_ID,
        )

        result = await migration_service._check_tenant_schema()
        assert result["has_tenant_columns"] is True
        assert len(result["tables_with_tenant"]) == 3


@pytest.mark.integration
class TestMigrationIntegration:
    """Integration tests for the migration process."""

    @pytest.mark.asyncio
    async def test_complete_migration_workflow(self, test_db_url):
        """Test complete migration workflow from start to finish."""
        service = RegistryMigrationService(test_db_url)

        # Set up initial state
        conn = await asyncpg.connect(test_db_url)

        try:
            # Create initial schema (simulating state before migration)
            await self._setup_initial_schema(conn)

            # 1. Dry run validation
            dry_result = await service.execute_migration(dry_run=True)
            assert dry_result["status"] == "dry_run_success"

            # 2. Execute migration
            test_sql = await self._get_test_migration_sql()
            with patch.object(service.migration_file, "read_text", return_value=test_sql):
                with patch.object(service.migration_file, "exists", return_value=True):
                    migration_result = await service.execute_migration(dry_run=False)

            assert migration_result["status"] == "success"

            # 3. Verify migration
            verify_result = await service.verify_migration()
            assert verify_result["status"] == "migrated"

            # 4. Test rollback
            rollback_result = await service.rollback_migration()
            assert rollback_result["status"] == "rollback_success"

            # 5. Verify rollback
            verify_rollback = await service.verify_migration()
            assert verify_rollback["status"] == "not_migrated"

        finally:
            await conn.close()

    async def _setup_initial_schema(self, conn):
        """Set up initial database schema for integration test."""
        # Create tenants table
        await conn.execute(
            """
            CREATE TABLE tenants (
                id UUID PRIMARY KEY,
                slug VARCHAR(63) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """
        )

        await conn.execute(
            """
            INSERT INTO tenants (id, slug, name)
            VALUES ($1, 'system', 'System')
        """,
            SYSTEM_TENANT_ID,
        )

        # Create registry tables
        await conn.execute(
            """
            CREATE TABLE service_registrations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                service_name VARCHAR(100) NOT NULL,
                instance_id VARCHAR(200) NOT NULL,
                version VARCHAR(50) NOT NULL,
                address INET NOT NULL,
                port INTEGER NOT NULL,
                protocol VARCHAR(10) NOT NULL
            )
        """
        )

        await conn.execute(
            """
            CREATE TABLE service_health_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                service_name VARCHAR(100) NOT NULL,
                instance_id VARCHAR(200) NOT NULL,
                new_status VARCHAR(20) NOT NULL
            )
        """
        )

        await conn.execute(
            """
            CREATE TABLE service_dependencies (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                service_name VARCHAR(100) NOT NULL,
                depends_on VARCHAR(100) NOT NULL,
                version_constraint VARCHAR(50) NOT NULL,
                UNIQUE(service_name, depends_on)
            )
        """
        )

    async def _get_test_migration_sql(self):
        """Get simplified migration SQL for testing."""
        return """
        BEGIN;

        ALTER TABLE service_registrations
        ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

        ALTER TABLE service_health_events
        ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

        ALTER TABLE service_dependencies
        ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

        ALTER TABLE service_registrations
        ADD CONSTRAINT fk_service_registrations_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

        ALTER TABLE service_health_events
        ADD CONSTRAINT fk_service_health_events_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

        ALTER TABLE service_dependencies
        ADD CONSTRAINT fk_service_dependencies_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

        CREATE INDEX idx_service_registrations_tenant_id ON service_registrations(tenant_id);
        CREATE INDEX idx_service_health_events_tenant_id ON service_health_events(tenant_id);
        CREATE INDEX idx_service_dependencies_tenant_id ON service_dependencies(tenant_id);

        COMMIT;
        """


# Fixtures for pytest
@pytest.fixture(scope="session")
def test_db_url():
    """Database URL for testing."""
    return "postgresql://test_user:test_pass@localhost:5432/test_registry_migration"


@pytest.fixture(scope="function")
async def clean_test_db(test_db_url):
    """Clean test database before each test."""
    conn = await asyncpg.connect(test_db_url)

    try:
        # Drop all test tables
        await conn.execute("DROP TABLE IF EXISTS service_dependencies CASCADE")
        await conn.execute("DROP TABLE IF EXISTS service_health_events CASCADE")
        await conn.execute("DROP TABLE IF EXISTS service_registrations CASCADE")
        await conn.execute("DROP TABLE IF EXISTS tenants CASCADE")

        # Drop views
        await conn.execute("DROP VIEW IF EXISTS active_services CASCADE")
        await conn.execute("DROP VIEW IF EXISTS service_uptime_24h CASCADE")

    except Exception:
        pass  # Ignore errors if tables don't exist

    finally:
        await conn.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
