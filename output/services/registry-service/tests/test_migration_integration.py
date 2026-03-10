"""
Integration tests for Registry Service migration workflows.

Tests comprehensive migration scenarios including:
- Multi-tenant migration execution
- Forward and rollback operations
- Data integrity verification
- Performance characteristics
- Error handling and recovery

These tests validate the complete migration stack from the Registry
Migration Service through to database operations.
"""

import asyncio
import pytest
import asyncpg
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, AsyncMock, Mock

from registry.migration_service import (
    RegistryMigrationService,
    MigrationError,
    MigrationVerificationError,
    SYSTEM_TENANT_ID
)


@pytest.mark.asyncio
@pytest.mark.integration
class TestRegistryMigrationIntegration:
    """Integration tests for complete registry migration workflows."""

    @pytest.fixture
    async def migration_service(self, test_db_url):
        """Create migration service with test database."""
        return RegistryMigrationService(test_db_url)

    @pytest.fixture
    async def populated_test_db(self, test_db_connection):
        """Set up test database with realistic data."""
        conn = test_db_connection

        # Create tenants table and system tenant
        await conn.execute("""
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
        """)

        await conn.execute("""
            INSERT INTO tenants (id, slug, name, status, config)
            VALUES ($1, 'system', 'System', 'active', '{"is_system": true}')
            ON CONFLICT (id) DO NOTHING
        """, SYSTEM_TENANT_ID)

        # Add test tenants
        await conn.execute("""
            INSERT INTO tenants (id, slug, name, status)
            VALUES
                ('11111111-1111-1111-1111-111111111111', 'tenant-a', 'Tenant A', 'active'),
                ('22222222-2222-2222-2222-222222222222', 'tenant-b', 'Tenant B', 'active')
            ON CONFLICT (id) DO NOTHING
        """)

        # Create registry tables without tenant_id (pre-migration state)
        await conn.execute("""
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
        """)

        await conn.execute("""
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
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS service_dependencies (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                service_name VARCHAR(100) NOT NULL,
                depends_on VARCHAR(100) NOT NULL,
                version_constraint VARCHAR(50) NOT NULL,
                discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_verified_at TIMESTAMPTZ,
                UNIQUE(service_name, depends_on)
            )
        """)

        # Insert realistic test data
        await conn.execute("""
            INSERT INTO service_registrations
            (service_name, instance_id, version, address, port, protocol, tags, metadata)
            VALUES
            ('pricing-service', 'pricing-001', '1.0.0', '192.168.1.10', 8080, 'http',
             ARRAY['finance', 'pricing'], '{"environment": "production"}'),
            ('pricing-service', 'pricing-002', '1.0.0', '192.168.1.11', 8080, 'http',
             ARRAY['finance', 'pricing'], '{"environment": "production"}'),
            ('trading-service', 'trading-001', '1.2.0', '192.168.1.20', 8081, 'http',
             ARRAY['finance', 'trading'], '{"environment": "production"}'),
            ('reference-data-service', 'refdata-001', '2.1.0', '192.168.1.30', 8082, 'grpc',
             ARRAY['reference', 'data'], '{"environment": "production"}'),
            ('risk-engine', 'risk-001', '0.9.0', '192.168.1.40', 8083, 'http',
             ARRAY['risk', 'analytics'], '{"environment": "staging"}')
        """)

        await conn.execute("""
            INSERT INTO service_health_events
            (service_name, instance_id, previous_status, new_status, check_name, check_output)
            VALUES
            ('pricing-service', 'pricing-001', 'unknown', 'healthy', 'health_check', 'OK'),
            ('pricing-service', 'pricing-002', 'unknown', 'healthy', 'health_check', 'OK'),
            ('trading-service', 'trading-001', 'healthy', 'warning', 'latency_check', 'High latency detected'),
            ('reference-data-service', 'refdata-001', 'unknown', 'healthy', 'health_check', 'OK'),
            ('risk-engine', 'risk-001', 'healthy', 'critical', 'memory_check', 'Memory usage at 95%')
        """)

        await conn.execute("""
            INSERT INTO service_dependencies
            (service_name, depends_on, version_constraint)
            VALUES
            ('trading-service', 'pricing-service', '>=1.0.0'),
            ('trading-service', 'reference-data-service', '>=2.0.0'),
            ('pricing-service', 'reference-data-service', '>=2.0.0'),
            ('risk-engine', 'trading-service', '>=1.0.0'),
            ('risk-engine', 'pricing-service', '>=1.0.0')
        """)

        return conn

    async def test_complete_migration_workflow_with_realistic_data(self, migration_service, populated_test_db):
        """Test complete migration workflow with realistic registry data."""
        # 1. Pre-migration validation
        validation = await migration_service._validate_pre_migration()
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0

        # 2. Collect pre-migration statistics
        pre_stats = await migration_service._collect_pre_migration_stats()

        # Verify realistic data counts
        assert pre_stats["service_registrations_count"] == 5
        assert pre_stats["service_health_events_count"] == 5
        assert pre_stats["service_dependencies_count"] == 5

        # Verify table structure
        assert "existing_constraints" in pre_stats
        assert "existing_indexes" in pre_stats

        # 3. Execute dry run
        dry_result = await migration_service.execute_migration(dry_run=True)
        assert dry_result["status"] == "dry_run_success"
        assert dry_result["pre_stats"]["service_registrations_count"] == 5

        # 4. Execute actual migration
        test_migration_sql = """
        BEGIN;

        -- Add tenant_id columns to all registry tables
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

        -- Create indexes for performance
        CREATE INDEX idx_service_registrations_tenant_service
        ON service_registrations(tenant_id, service_name);

        CREATE INDEX idx_service_health_events_tenant_service
        ON service_health_events(tenant_id, service_name);

        CREATE INDEX idx_service_dependencies_tenant_service
        ON service_dependencies(tenant_id, service_name);

        -- Create tenant-aware views
        CREATE OR REPLACE VIEW active_services AS
        SELECT
            tenant_id,
            service_name,
            COUNT(*) as instance_count,
            MAX(version) as latest_version,
            ARRAY_AGG(DISTINCT tags) as all_tags
        FROM service_registrations
        WHERE deregistered_at IS NULL
        GROUP BY tenant_id, service_name;

        COMMIT;
        """

        with patch.object(migration_service.migration_file, 'read_text', return_value=test_migration_sql):
            with patch.object(migration_service.migration_file, 'exists', return_value=True):
                migration_result = await migration_service.execute_migration(dry_run=False)

        # Verify migration success
        assert migration_result["status"] == "success"
        assert migration_result["verification"]["valid"] is True

        # Verify data preservation
        post_stats = migration_result["post_stats"]
        assert post_stats["service_registrations_count"] == 5
        assert post_stats["service_health_events_count"] == 5
        assert post_stats["service_dependencies_count"] == 5

        # Verify all records assigned to system tenant
        assert post_stats["service_registrations_system_tenant_count"] == 5
        assert post_stats["service_health_events_system_tenant_count"] == 5
        assert post_stats["service_dependencies_system_tenant_count"] == 5

        # 5. Verify migration completion
        verification = await migration_service.verify_migration()
        assert verification["status"] == "migrated"
        assert verification["schema_check"]["has_tenant_columns"] is True
        assert len(verification["schema_check"]["tables_with_tenant"]) == 3

        # 6. Test tenant isolation by inserting data for different tenants
        conn = populated_test_db

        # Insert data for tenant A
        await conn.execute("""
            INSERT INTO service_registrations
            (service_name, instance_id, version, address, port, protocol, tenant_id)
            VALUES ('tenant-a-service', 'ta-001', '1.0.0', '10.0.1.10', 9000, 'http', $1)
        """, '11111111-1111-1111-1111-111111111111')

        # Insert data for tenant B
        await conn.execute("""
            INSERT INTO service_registrations
            (service_name, instance_id, version, address, port, protocol, tenant_id)
            VALUES ('tenant-b-service', 'tb-001', '1.0.0', '10.0.2.10', 9001, 'http', $1)
        """, '22222222-2222-2222-2222-222222222222')

        # Verify tenant isolation in views
        system_services = await conn.fetch("""
            SELECT service_name, instance_count FROM active_services
            WHERE tenant_id = $1 ORDER BY service_name
        """, SYSTEM_TENANT_ID)

        assert len(system_services) == 4  # pricing, trading, reference-data, risk

        tenant_a_services = await conn.fetch("""
            SELECT service_name FROM active_services
            WHERE tenant_id = $1
        """, '11111111-1111-1111-1111-111111111111')

        assert len(tenant_a_services) == 1
        assert tenant_a_services[0]['service_name'] == 'tenant-a-service'

    async def test_migration_rollback_with_data_verification(self, migration_service, populated_test_db):
        """Test migration rollback with comprehensive data verification."""
        # First, apply migration (setup for rollback test)
        test_migration_sql = """
        BEGIN;
        ALTER TABLE service_registrations ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
        ALTER TABLE service_health_events ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
        ALTER TABLE service_dependencies ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
        COMMIT;
        """

        with patch.object(migration_service.migration_file, 'read_text', return_value=test_migration_sql):
            with patch.object(migration_service.migration_file, 'exists', return_value=True):
                await migration_service.execute_migration(dry_run=False)

        # Verify migration was applied
        verification = await migration_service.verify_migration()
        assert verification["status"] == "migrated"

        # Collect pre-rollback data
        conn = populated_test_db
        pre_rollback_counts = {}
        for table in ["service_registrations", "service_health_events", "service_dependencies"]:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            pre_rollback_counts[table] = count

        # Perform rollback
        rollback_result = await migration_service.rollback_migration()
        assert rollback_result["status"] == "rollback_success"

        # Verify rollback
        post_rollback_verification = await migration_service.verify_migration()
        assert post_rollback_verification["status"] == "not_migrated"

        # Verify data preservation during rollback
        post_rollback_counts = {}
        for table in ["service_registrations", "service_health_events", "service_dependencies"]:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            post_rollback_counts[table] = count

        # All data should be preserved
        assert pre_rollback_counts == post_rollback_counts

        # Verify tenant columns were removed
        for table in ["service_registrations", "service_health_events", "service_dependencies"]:
            columns = await conn.fetch("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = $1 AND column_name = 'tenant_id'
            """, table)
            assert len(columns) == 0

    async def test_migration_data_integrity_verification(self, migration_service, populated_test_db):
        """Test comprehensive data integrity verification during migration."""
        # Execute migration with detailed integrity tracking
        test_migration_sql = """
        BEGIN;

        -- Add tenant_id columns
        ALTER TABLE service_registrations ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
        ALTER TABLE service_health_events ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
        ALTER TABLE service_dependencies ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

        -- Add constraints with explicit names for testing
        ALTER TABLE service_registrations
        ADD CONSTRAINT fk_srv_reg_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);

        ALTER TABLE service_health_events
        ADD CONSTRAINT fk_srv_health_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);

        ALTER TABLE service_dependencies
        ADD CONSTRAINT fk_srv_deps_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);

        -- Add specific indexes for testing
        CREATE INDEX idx_srv_reg_tenant_perf ON service_registrations(tenant_id, service_name, registered_at);
        CREATE INDEX idx_srv_health_tenant_perf ON service_health_events(tenant_id, service_name, event_at);
        CREATE INDEX idx_srv_deps_tenant_perf ON service_dependencies(tenant_id, service_name);

        COMMIT;
        """

        with patch.object(migration_service.migration_file, 'read_text', return_value=test_migration_sql):
            with patch.object(migration_service.migration_file, 'exists', return_value=True):
                migration_result = await migration_service.execute_migration(dry_run=False)

        # Verify detailed integrity results
        assert migration_result["verification"]["valid"] is True

        post_stats = migration_result["post_stats"]

        # Verify constraint creation
        expected_constraints = ["fk_srv_reg_tenant", "fk_srv_health_tenant", "fk_srv_deps_tenant"]
        created_constraints = post_stats.get("new_tenant_constraints", [])

        for constraint in expected_constraints:
            assert any(constraint in c for c in created_constraints), f"Constraint {constraint} not found"

        # Verify index creation
        expected_indexes = ["idx_srv_reg_tenant_perf", "idx_srv_health_tenant_perf", "idx_srv_deps_tenant_perf"]
        created_indexes = post_stats.get("new_tenant_indexes", [])

        for index in expected_indexes:
            assert any(index in i for i in created_indexes), f"Index {index} not found"

        # Verify foreign key enforcement
        conn = populated_test_db

        # Test that invalid tenant_id is rejected
        with pytest.raises(asyncpg.ForeignKeyViolationError):
            await conn.execute("""
                INSERT INTO service_registrations
                (service_name, instance_id, version, address, port, protocol, tenant_id)
                VALUES ('test', 'test-001', '1.0', '127.0.0.1', 8080, 'http', '99999999-9999-9999-9999-999999999999')
            """)

    async def test_migration_performance_characteristics(self, migration_service, populated_test_db):
        """Test migration performance with timing and resource monitoring."""
        # Insert additional data for performance testing
        conn = populated_test_db

        # Add more test data to simulate realistic load
        batch_size = 100
        for batch in range(5):  # 500 additional records
            registrations = []
            for i in range(batch_size):
                registrations.append((
                    f'perf-service-{batch}', f'instance-{batch}-{i:03d}', '1.0.0',
                    '192.168.100.1', 8000 + i, 'http'
                ))

            await conn.executemany("""
                INSERT INTO service_registrations
                (service_name, instance_id, version, address, port, protocol)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, registrations)

        # Verify increased data volume
        total_registrations = await conn.fetchval("SELECT COUNT(*) FROM service_registrations")
        assert total_registrations == 505  # 5 original + 500 added

        # Execute migration with performance monitoring
        start_time = time.time()

        test_migration_sql = """
        BEGIN;
        ALTER TABLE service_registrations ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
        ALTER TABLE service_health_events ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
        ALTER TABLE service_dependencies ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

        CREATE INDEX CONCURRENTLY idx_srv_reg_tenant_concurrent ON service_registrations(tenant_id);
        CREATE INDEX CONCURRENTLY idx_srv_health_tenant_concurrent ON service_health_events(tenant_id);
        CREATE INDEX CONCURRENTLY idx_srv_deps_tenant_concurrent ON service_dependencies(tenant_id);
        COMMIT;
        """

        with patch.object(migration_service.migration_file, 'read_text', return_value=test_migration_sql):
            with patch.object(migration_service.migration_file, 'exists', return_value=True):
                migration_result = await migration_service.execute_migration(dry_run=False)

        end_time = time.time()
        migration_duration = end_time - start_time

        # Verify performance characteristics
        assert migration_result["status"] == "success"
        assert "execution_time" in migration_result

        # Migration should complete within reasonable time (adjust as needed)
        assert migration_duration < 30.0, f"Migration took {migration_duration}s, expected < 30s"

        # Verify all data migrated correctly
        post_stats = migration_result["post_stats"]
        assert post_stats["service_registrations_system_tenant_count"] == 505

    async def test_migration_error_recovery_scenarios(self, migration_service, populated_test_db):
        """Test migration error handling and recovery scenarios."""

        # Test 1: Invalid SQL in migration
        invalid_sql = """
        BEGIN;
        ALTER TABLE service_registrations ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
        ALTER TABLE nonexistent_table ADD COLUMN tenant_id UUID; -- This will fail
        COMMIT;
        """

        with patch.object(migration_service.migration_file, 'read_text', return_value=invalid_sql):
            with patch.object(migration_service.migration_file, 'exists', return_value=True):
                with pytest.raises(MigrationError):
                    await migration_service.execute_migration(dry_run=False)

        # Verify database state is unchanged after failed migration
        verification = await migration_service.verify_migration()
        assert verification["status"] == "not_migrated"

        # Test 2: Constraint violation during migration
        constraint_violation_sql = """
        BEGIN;
        ALTER TABLE service_registrations ADD COLUMN tenant_id UUID NOT NULL DEFAULT '99999999-9999-9999-9999-999999999999';
        ALTER TABLE service_registrations ADD CONSTRAINT fk_invalid_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
        COMMIT;
        """

        with patch.object(migration_service.migration_file, 'read_text', return_value=constraint_violation_sql):
            with patch.object(migration_service.migration_file, 'exists', return_value=True):
                with pytest.raises(MigrationError):
                    await migration_service.execute_migration(dry_run=False)

        # Test 3: Successful migration after fixing issues
        valid_sql = """
        BEGIN;
        ALTER TABLE service_registrations ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
        ALTER TABLE service_health_events ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
        ALTER TABLE service_dependencies ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';
        COMMIT;
        """

        with patch.object(migration_service.migration_file, 'read_text', return_value=valid_sql):
            with patch.object(migration_service.migration_file, 'exists', return_value=True):
                recovery_result = await migration_service.execute_migration(dry_run=False)

        assert recovery_result["status"] == "success"

    async def test_concurrent_migration_protection(self, migration_service, populated_test_db):
        """Test protection against concurrent migration execution."""
        # This test simulates what would happen if two migration processes tried to run simultaneously

        # Create a mock that simulates a database lock or concurrent transaction
        async def simulate_concurrent_migration(*args, **kwargs):
            # Simulate the first migration holding a lock
            await asyncio.sleep(0.1)
            raise asyncpg.DeadlockDetectedError("Deadlock detected: concurrent migration in progress")

        # Mock the database execution to simulate concurrency conflict
        original_execute = migration_service._execute_migration_sql

        with patch.object(migration_service, '_execute_migration_sql', side_effect=simulate_concurrent_migration):
            with pytest.raises(MigrationError) as exc_info:
                test_sql = "ALTER TABLE service_registrations ADD COLUMN tenant_id UUID;"
                with patch.object(migration_service.migration_file, 'read_text', return_value=test_sql):
                    with patch.object(migration_service.migration_file, 'exists', return_value=True):
                        await migration_service.execute_migration(dry_run=False)

        # Verify appropriate error handling for concurrent access
        assert "Deadlock detected" in str(exc_info.value) or "concurrent migration" in str(exc_info.value)

    async def test_migration_with_large_dataset_chunking(self, migration_service, populated_test_db):
        """Test migration behavior with large datasets that might require chunked processing."""
        conn = populated_test_db

        # Create a large dataset for testing
        large_dataset_size = 1000

        # Insert large dataset in chunks to avoid memory issues
        chunk_size = 100
        for chunk_start in range(0, large_dataset_size, chunk_size):
            chunk_data = []
            for i in range(chunk_start, min(chunk_start + chunk_size, large_dataset_size)):
                chunk_data.append((
                    f'large-service-{i//100:02d}', f'instance-{i:04d}', '2.0.0',
                    '10.0.0.1', 8000 + (i % 1000), 'http',
                    f'{{"batch": {i//100}, "index": {i}}}'
                ))

            await conn.executemany("""
                INSERT INTO service_registrations
                (service_name, instance_id, version, address, port, protocol, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, chunk_data)

        # Verify large dataset
        total_count = await conn.fetchval("SELECT COUNT(*) FROM service_registrations")
        assert total_count == 1005  # 5 original + 1000 added

        # Execute migration on large dataset
        start_time = time.time()

        large_dataset_migration_sql = """
        BEGIN;

        -- Add tenant_id column with default
        ALTER TABLE service_registrations
        ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

        -- Update records in batches to avoid long locks
        -- In a real implementation, this might be done in chunks
        UPDATE service_registrations SET tenant_id = '00000000-0000-0000-0000-000000000000' WHERE tenant_id IS NULL;

        -- Add foreign key constraint
        ALTER TABLE service_registrations
        ADD CONSTRAINT fk_service_registrations_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

        -- Create index for performance
        CREATE INDEX idx_service_registrations_tenant_large ON service_registrations(tenant_id, service_name);

        COMMIT;
        """

        with patch.object(migration_service.migration_file, 'read_text', return_value=large_dataset_migration_sql):
            with patch.object(migration_service.migration_file, 'exists', return_value=True):
                migration_result = await migration_service.execute_migration(dry_run=False)

        end_time = time.time()
        migration_duration = end_time - start_time

        # Verify successful migration of large dataset
        assert migration_result["status"] == "success"

        post_stats = migration_result["post_stats"]
        assert post_stats["service_registrations_system_tenant_count"] == 1005

        # Verify migration completed in reasonable time even with large dataset
        # Adjust threshold based on expected performance characteristics
        assert migration_duration < 60.0, f"Large dataset migration took {migration_duration}s, expected < 60s"

        # Verify data integrity after large dataset migration
        verification_result = await migration_service._verify_data_integrity()
        assert verification_result["valid"] is True


@pytest.mark.asyncio
@pytest.mark.integration
class TestMultiTenantMigrationScenarios:
    """Test migration scenarios specific to multi-tenant architecture."""

    @pytest.fixture
    async def multi_tenant_db(self, test_db_connection):
        """Set up test database with multiple tenants and complex data relationships."""
        conn = test_db_connection

        # Create tenants table with multiple test tenants
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id UUID PRIMARY KEY,
                slug VARCHAR(63) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                config JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        # Insert system tenant and multiple business tenants
        tenants_data = [
            (SYSTEM_TENANT_ID, 'system', 'System Tenant', '{"is_system": true}'),
            ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'acme-corp', 'ACME Corporation', '{"tier": "enterprise"}'),
            ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'widget-inc', 'Widget Inc', '{"tier": "professional"}'),
            ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'startup-xyz', 'Startup XYZ', '{"tier": "startup"}')
        ]

        for tenant_id, slug, name, config in tenants_data:
            await conn.execute("""
                INSERT INTO tenants (id, slug, name, config)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO NOTHING
            """, tenant_id, slug, name, config)

        # Create pre-migration registry tables
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS service_registrations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                service_name VARCHAR(100) NOT NULL,
                instance_id VARCHAR(200) NOT NULL,
                version VARCHAR(50) NOT NULL,
                address INET NOT NULL,
                port INTEGER NOT NULL,
                protocol VARCHAR(10) NOT NULL,
                environment VARCHAR(20) DEFAULT 'production',
                registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                deregistered_at TIMESTAMPTZ
            )
        """)

        # Insert services that will need to be assigned to appropriate tenants
        services_data = [
            # System services (shared infrastructure)
            ('system-monitor', 'sysmon-001', '1.0.0', '10.0.0.10', 9090, 'http', 'system'),
            ('log-aggregator', 'logs-001', '2.1.0', '10.0.0.11', 9091, 'http', 'system'),

            # ACME Corp services
            ('acme-trading-engine', 'acme-trade-001', '3.2.1', '10.1.0.10', 8080, 'http', 'production'),
            ('acme-risk-calculator', 'acme-risk-001', '2.0.0', '10.1.0.11', 8081, 'grpc', 'production'),
            ('acme-reporting', 'acme-report-001', '1.5.0', '10.1.0.12', 8082, 'http', 'production'),

            # Widget Inc services
            ('widget-inventory', 'widget-inv-001', '1.8.0', '10.2.0.10', 8080, 'http', 'production'),
            ('widget-shipping', 'widget-ship-001', '1.2.0', '10.2.0.11', 8081, 'http', 'production'),

            # Startup XYZ services
            ('xyz-prototype', 'xyz-proto-001', '0.3.0', '10.3.0.10', 8080, 'http', 'staging')
        ]

        await conn.executemany("""
            INSERT INTO service_registrations
            (service_name, instance_id, version, address, port, protocol, environment)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, services_data)

        return conn

    async def test_intelligent_tenant_assignment_migration(self, test_db_url, multi_tenant_db):
        """Test migration with intelligent tenant assignment based on service naming patterns."""
        migration_service = RegistryMigrationService(test_db_url)

        # Create migration that assigns tenants based on service name patterns
        intelligent_assignment_sql = """
        BEGIN;

        -- Add tenant_id column
        ALTER TABLE service_registrations
        ADD COLUMN tenant_id UUID;

        -- Assign tenants based on service naming patterns
        UPDATE service_registrations SET tenant_id = '00000000-0000-0000-0000-000000000000'
        WHERE service_name LIKE 'system-%' OR service_name LIKE 'log-%';

        UPDATE service_registrations SET tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        WHERE service_name LIKE 'acme-%';

        UPDATE service_registrations SET tenant_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
        WHERE service_name LIKE 'widget-%';

        UPDATE service_registrations SET tenant_id = 'cccccccc-cccc-cccc-cccc-cccccccccccc'
        WHERE service_name LIKE 'xyz-%';

        -- Set NOT NULL constraint after assignment
        ALTER TABLE service_registrations ALTER COLUMN tenant_id SET NOT NULL;

        -- Add foreign key constraint
        ALTER TABLE service_registrations
        ADD CONSTRAINT fk_service_registrations_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

        -- Create tenant-aware indexes
        CREATE INDEX idx_service_registrations_tenant_name ON service_registrations(tenant_id, service_name);

        COMMIT;
        """

        with patch.object(migration_service.migration_file, 'read_text', return_value=intelligent_assignment_sql):
            with patch.object(migration_service.migration_file, 'exists', return_value=True):
                migration_result = await migration_service.execute_migration(dry_run=False)

        assert migration_result["status"] == "success"

        # Verify tenant assignments
        conn = multi_tenant_db

        # Check system services
        system_services = await conn.fetch("""
            SELECT service_name FROM service_registrations
            WHERE tenant_id = $1 ORDER BY service_name
        """, SYSTEM_TENANT_ID)
        system_service_names = [row['service_name'] for row in system_services]
        assert 'system-monitor' in system_service_names
        assert 'log-aggregator' in system_service_names

        # Check ACME Corp services
        acme_services = await conn.fetch("""
            SELECT service_name FROM service_registrations
            WHERE tenant_id = $1 ORDER BY service_name
        """, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
        acme_service_names = [row['service_name'] for row in acme_services]
        assert 'acme-trading-engine' in acme_service_names
        assert 'acme-risk-calculator' in acme_service_names
        assert 'acme-reporting' in acme_service_names

        # Check Widget Inc services
        widget_services = await conn.fetch("""
            SELECT service_name FROM service_registrations
            WHERE tenant_id = $1 ORDER BY service_name
        """, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
        widget_service_names = [row['service_name'] for row in widget_services]
        assert 'widget-inventory' in widget_service_names
        assert 'widget-shipping' in widget_service_names

        # Check Startup XYZ services
        xyz_services = await conn.fetch("""
            SELECT service_name FROM service_registrations
            WHERE tenant_id = $1
        """, 'cccccccc-cccc-cccc-cccc-cccccccccccc')
        xyz_service_names = [row['service_name'] for row in xyz_services]
        assert 'xyz-prototype' in xyz_service_names

    async def test_tenant_isolation_verification_after_migration(self, test_db_url, multi_tenant_db):
        """Test thorough verification of tenant isolation after migration."""
        migration_service = RegistryMigrationService(test_db_url)

        # Apply basic tenant migration
        tenant_migration_sql = """
        BEGIN;
        ALTER TABLE service_registrations
        ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

        ALTER TABLE service_registrations
        ADD CONSTRAINT fk_service_registrations_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
        COMMIT;
        """

        with patch.object(migration_service.migration_file, 'read_text', return_value=tenant_migration_sql):
            with patch.object(migration_service.migration_file, 'exists', return_value=True):
                await migration_service.execute_migration(dry_run=False)

        conn = multi_tenant_db

        # Test tenant isolation by inserting tenant-specific data
        await conn.execute("""
            INSERT INTO service_registrations
            (service_name, instance_id, version, address, port, protocol, tenant_id)
            VALUES
            ('tenant-a-exclusive', 'ta-ex-001', '1.0.0', '192.168.1.100', 8100, 'http', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
            ('tenant-b-exclusive', 'tb-ex-001', '1.0.0', '192.168.1.101', 8101, 'http', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
        """)

        # Verify tenant A cannot see tenant B's data and vice versa
        tenant_a_exclusive_services = await conn.fetch("""
            SELECT service_name FROM service_registrations
            WHERE tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
            AND service_name LIKE '%-exclusive'
        """)
        assert len(tenant_a_exclusive_services) == 1
        assert tenant_a_exclusive_services[0]['service_name'] == 'tenant-a-exclusive'

        tenant_b_exclusive_services = await conn.fetch("""
            SELECT service_name FROM service_registrations
            WHERE tenant_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
            AND service_name LIKE '%-exclusive'
        """)
        assert len(tenant_b_exclusive_services) == 1
        assert tenant_b_exclusive_services[0]['service_name'] == 'tenant-b-exclusive'

        # Verify cross-tenant queries don't accidentally leak data
        cross_tenant_check = await conn.fetch("""
            SELECT DISTINCT tenant_id, COUNT(*) as service_count
            FROM service_registrations
            GROUP BY tenant_id
            ORDER BY tenant_id
        """)

        # Should have entries for system tenant and each business tenant
        tenant_ids_with_services = [row['tenant_id'] for row in cross_tenant_check]
        assert SYSTEM_TENANT_ID in tenant_ids_with_services
        assert 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' in tenant_ids_with_services
        assert 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' in tenant_ids_with_services

    async def test_migration_with_tenant_quotas_and_limits(self, test_db_url, multi_tenant_db):
        """Test migration scenarios involving tenant quotas and resource limits."""
        migration_service = RegistryMigrationService(test_db_url)

        # Create quota-aware migration
        quota_migration_sql = """
        BEGIN;

        -- Add tenant_id and quota tracking columns
        ALTER TABLE service_registrations
        ADD COLUMN tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
        ADD COLUMN resource_usage JSONB DEFAULT '{}';

        -- Create tenant quotas table
        CREATE TABLE tenant_quotas (
            tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
            max_services INTEGER DEFAULT 10,
            max_instances_per_service INTEGER DEFAULT 5,
            max_memory_mb INTEGER DEFAULT 1024,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- Insert default quotas for tenants
        INSERT INTO tenant_quotas (tenant_id, max_services, max_instances_per_service)
        VALUES
        ('00000000-0000-0000-0000-000000000000', 100, 20),  -- System tenant - high limits
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 50, 10),   -- Enterprise - high limits
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 20, 5),    -- Professional - medium limits
        ('cccccccc-cccc-cccc-cccc-cccccccccccc', 5, 2);     -- Startup - low limits

        -- Create quota enforcement view
        CREATE VIEW tenant_usage_summary AS
        SELECT
            t.id as tenant_id,
            t.slug as tenant_slug,
            COUNT(DISTINCT sr.service_name) as service_count,
            COUNT(sr.id) as instance_count,
            tq.max_services,
            tq.max_instances_per_service,
            (COUNT(DISTINCT sr.service_name) >= tq.max_services) as at_service_limit,
            (COUNT(sr.id) >= tq.max_services * tq.max_instances_per_service) as at_instance_limit
        FROM tenants t
        LEFT JOIN tenant_quotas tq ON t.id = tq.tenant_id
        LEFT JOIN service_registrations sr ON t.id = sr.tenant_id AND sr.deregistered_at IS NULL
        GROUP BY t.id, t.slug, tq.max_services, tq.max_instances_per_service;

        COMMIT;
        """

        with patch.object(migration_service.migration_file, 'read_text', return_value=quota_migration_sql):
            with patch.object(migration_service.migration_file, 'exists', return_value=True):
                migration_result = await migration_service.execute_migration(dry_run=False)

        assert migration_result["status"] == "success"

        # Verify quota system is working
        conn = multi_tenant_db

        # Check quota view functionality
        usage_summary = await conn.fetch("""
            SELECT tenant_slug, service_count, instance_count, max_services, at_service_limit
            FROM tenant_usage_summary
            ORDER BY tenant_slug
        """)

        summary_by_tenant = {row['tenant_slug']: dict(row) for row in usage_summary}

        # Verify system tenant has expected configuration
        assert 'system' in summary_by_tenant
        system_usage = summary_by_tenant['system']
        assert system_usage['max_services'] == 100
        assert system_usage['service_count'] >= 0
        assert system_usage['at_service_limit'] is False

        # Test quota enforcement by adding services to startup tenant
        startup_tenant_id = 'cccccccc-cccc-cccc-cccc-cccccccccccc'

        # Add services up to the limit (5 services for startup tier)
        for i in range(3):  # Add 3 more services (already has 1)
            await conn.execute("""
                INSERT INTO service_registrations
                (service_name, instance_id, version, address, port, protocol, tenant_id)
                VALUES ($1, $2, '1.0.0', '10.3.0.20', $3, 'http', $4)
            """, f'xyz-service-{i}', f'xyz-svc-{i}-001', 8200 + i, startup_tenant_id)

        # Check updated usage
        startup_usage = await conn.fetchrow("""
            SELECT service_count, max_services, at_service_limit
            FROM tenant_usage_summary
            WHERE tenant_id = $1
        """, startup_tenant_id)

        assert startup_usage['service_count'] == 4  # 1 original + 3 added
        assert startup_usage['max_services'] == 5
        assert startup_usage['at_service_limit'] is False  # Still under limit

        # Add one more to reach the limit
        await conn.execute("""
            INSERT INTO service_registrations
            (service_name, instance_id, version, address, port, protocol, tenant_id)
            VALUES ('xyz-service-final', 'xyz-final-001', '1.0.0', '10.3.0.25', 8250, 'http', $1)
        """, startup_tenant_id)

        # Check that we're now at the limit
        final_usage = await conn.fetchrow("""
            SELECT service_count, at_service_limit
            FROM tenant_usage_summary
            WHERE tenant_id = $1
        """, startup_tenant_id)

        assert final_usage['service_count'] == 5
        assert final_usage['at_service_limit'] is True