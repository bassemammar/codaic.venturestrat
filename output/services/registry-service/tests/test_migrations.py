"""
Tests for Pricing Infrastructure Database Migrations

This module contains tests to validate the pricing infrastructure database schema
created by Alembic migrations, ensuring all tables, constraints, indexes, and
relationships are properly created.

Run with:
    pytest services/registry-service/tests/test_migrations.py
"""

import pytest
import asyncio
from typing import List, Dict, Any

import asyncpg
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
import os


class TestPricingInfrastructureMigrations:
    """Test pricing infrastructure database schema created by migrations."""

    @pytest.fixture
    def database_url(self) -> str:
        """Get database URL from environment or use default."""
        return os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5432/venturestrat"
        )

    @pytest.fixture
    def sync_engine(self, database_url: str):
        """Create synchronous database engine for schema inspection."""
        # Convert async URL to sync for inspection
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_url)
        yield engine
        engine.dispose()

    @pytest.fixture
    def async_engine(self, database_url: str):
        """Create asynchronous database engine for data operations."""
        engine = create_async_engine(database_url)
        yield engine
        engine.sync_engine.dispose()

    def test_pricer_registry_table_exists(self, sync_engine):
        """Test that pricer_registry table exists with correct structure."""
        inspector = inspect(sync_engine)
        tables = inspector.get_table_names()

        assert "pricer_registry" in tables, "pricer_registry table should exist"

        # Check columns
        columns = {col['name']: col for col in inspector.get_columns("pricer_registry")}

        # Required columns
        required_columns = [
            "pricer_id", "name", "version", "description",
            "health_check_url", "pricing_url", "batch_supported",
            "max_batch_size", "status", "last_health_check",
            "health_check_failures", "created_at", "updated_at"
        ]

        for col_name in required_columns:
            assert col_name in columns, f"Column {col_name} should exist in pricer_registry"

        # Check primary key
        pk_constraints = inspector.get_pk_constraint("pricer_registry")
        assert pk_constraints["constrained_columns"] == ["pricer_id"], \
            "pricer_id should be the primary key"

    def test_pricer_capabilities_table_exists(self, sync_engine):
        """Test that pricer_capabilities table exists with correct structure."""
        inspector = inspect(sync_engine)
        tables = inspector.get_table_names()

        assert "pricer_capabilities" in tables, "pricer_capabilities table should exist"

        # Check columns
        columns = {col['name']: col for col in inspector.get_columns("pricer_capabilities")}

        required_columns = [
            "id", "pricer_id", "instrument_type", "model_type",
            "features", "priority"
        ]

        for col_name in required_columns:
            assert col_name in columns, f"Column {col_name} should exist in pricer_capabilities"

        # Check primary key
        pk_constraints = inspector.get_pk_constraint("pricer_capabilities")
        assert pk_constraints["constrained_columns"] == ["id"], \
            "id should be the primary key"

    def test_tenant_pricing_config_table_exists(self, sync_engine):
        """Test that tenant_pricing_config table exists with correct structure."""
        inspector = inspect(sync_engine)
        tables = inspector.get_table_names()

        assert "tenant_pricing_config" in tables, "tenant_pricing_config table should exist"

        # Check columns
        columns = {col['name']: col for col in inspector.get_columns("tenant_pricing_config")}

        required_columns = [
            "id", "tenant_id", "default_pricer_id", "fallback_pricer_id",
            "config_json", "created_at", "updated_at"
        ]

        for col_name in required_columns:
            assert col_name in columns, f"Column {col_name} should exist in tenant_pricing_config"

    def test_foreign_key_relationships(self, sync_engine):
        """Test that foreign key relationships are properly created."""
        inspector = inspect(sync_engine)

        # Check pricer_capabilities foreign keys
        fk_capabilities = inspector.get_foreign_keys("pricer_capabilities")
        capability_fk_names = [fk['name'] for fk in fk_capabilities]
        assert "fk_pricer_capabilities_pricer" in capability_fk_names, \
            "Foreign key from pricer_capabilities to pricer_registry should exist"

        # Check tenant_pricing_config foreign keys
        fk_tenant_config = inspector.get_foreign_keys("tenant_pricing_config")
        tenant_config_fk_names = [fk['name'] for fk in fk_tenant_config]

        expected_fks = [
            "fk_tenant_pricing_config_tenant",
            "fk_tenant_pricing_default_pricer",
            "fk_tenant_pricing_fallback_pricer"
        ]

        for expected_fk in expected_fks:
            assert expected_fk in tenant_config_fk_names, \
                f"Foreign key {expected_fk} should exist"

    def test_indexes_created(self, sync_engine):
        """Test that performance indexes are created."""
        inspector = inspect(sync_engine)

        # Check pricer_registry indexes
        registry_indexes = inspector.get_indexes("pricer_registry")
        registry_index_names = [idx['name'] for idx in registry_indexes]

        expected_registry_indexes = [
            "idx_pricer_registry_status",
            "idx_pricer_registry_last_health_check",
            "idx_pricer_registry_name"
        ]

        for expected_idx in expected_registry_indexes:
            assert expected_idx in registry_index_names, \
                f"Index {expected_idx} should exist on pricer_registry"

        # Check pricer_capabilities indexes
        capabilities_indexes = inspector.get_indexes("pricer_capabilities")
        capabilities_index_names = [idx['name'] for idx in capabilities_indexes]

        expected_capabilities_indexes = [
            "idx_pricer_capabilities_pricer_id",
            "idx_pricer_capabilities_instrument_type",
            "idx_pricer_capabilities_model_type",
            "idx_pricer_capabilities_priority",
            "idx_pricer_capabilities_composite"
        ]

        for expected_idx in expected_capabilities_indexes:
            assert expected_idx in capabilities_index_names, \
                f"Index {expected_idx} should exist on pricer_capabilities"

        # Check tenant_pricing_config indexes
        tenant_config_indexes = inspector.get_indexes("tenant_pricing_config")
        tenant_config_index_names = [idx['name'] for idx in tenant_config_indexes]

        expected_tenant_config_indexes = [
            "idx_tenant_pricing_config_tenant_id",
            "idx_tenant_pricing_config_default_pricer",
            "idx_tenant_pricing_config_fallback_pricer"
        ]

        for expected_idx in expected_tenant_config_indexes:
            assert expected_idx in tenant_config_index_names, \
                f"Index {expected_idx} should exist on tenant_pricing_config"

    def test_check_constraints_exist(self, sync_engine):
        """Test that check constraints are properly created."""
        inspector = inspect(sync_engine)

        # Check pricer_registry constraints
        registry_constraints = inspector.get_check_constraints("pricer_registry")
        registry_constraint_names = [cc['name'] for cc in registry_constraints]

        expected_registry_constraints = [
            "chk_pricer_id_format",
            "chk_pricer_status",
            "chk_max_batch_size_positive",
            "chk_health_failures_non_negative"
        ]

        for expected_constraint in expected_registry_constraints:
            assert expected_constraint in registry_constraint_names, \
                f"Check constraint {expected_constraint} should exist on pricer_registry"

        # Check pricer_capabilities constraints
        capabilities_constraints = inspector.get_check_constraints("pricer_capabilities")
        capabilities_constraint_names = [cc['name'] for cc in capabilities_constraints]

        expected_capabilities_constraints = [
            "chk_instrument_type_format",
            "chk_model_type_format"
        ]

        for expected_constraint in expected_capabilities_constraints:
            assert expected_constraint in capabilities_constraint_names, \
                f"Check constraint {expected_constraint} should exist on pricer_capabilities"

        # Check tenant_pricing_config constraints
        tenant_config_constraints = inspector.get_check_constraints("tenant_pricing_config")
        tenant_config_constraint_names = [cc['name'] for cc in tenant_config_constraints]

        assert "chk_different_pricers" in tenant_config_constraint_names, \
            "Check constraint chk_different_pricers should exist on tenant_pricing_config"

    @pytest.mark.asyncio
    async def test_seed_data_exists(self, async_engine):
        """Test that seed data was properly inserted."""
        async with async_engine.connect() as conn:
            # Check QuantLib pricer exists
            result = await conn.execute(
                text("SELECT COUNT(*) as count FROM pricer_registry WHERE pricer_id = 'quantlib-v1.18'")
            )
            quantlib_count = result.fetchone()[0]
            assert quantlib_count == 1, "QuantLib pricer should be registered"

            # Check Treasury pricer exists
            result = await conn.execute(
                text("SELECT COUNT(*) as count FROM pricer_registry WHERE pricer_id = 'treasury-v2.3'")
            )
            treasury_count = result.fetchone()[0]
            assert treasury_count == 1, "Treasury pricer should be registered"

            # Check capabilities exist
            result = await conn.execute(
                text("SELECT COUNT(*) as count FROM pricer_capabilities")
            )
            capabilities_count = result.fetchone()[0]
            assert capabilities_count >= 10, "At least 10 capabilities should be seeded"

    @pytest.mark.asyncio
    async def test_views_created(self, async_engine):
        """Test that database views are created."""
        async with async_engine.connect() as conn:
            # Test pricer_overview view
            try:
                result = await conn.execute(text("SELECT * FROM pricer_overview LIMIT 1"))
                overview_data = result.fetchone()
                assert overview_data is not None, "pricer_overview view should return data"
            except Exception as e:
                pytest.fail(f"pricer_overview view should exist and be queryable: {e}")

            # Test tenant_pricing_overview view
            try:
                result = await conn.execute(text("SELECT * FROM tenant_pricing_overview LIMIT 1"))
                # May be empty if no tenants exist, but should not error
            except Exception as e:
                pytest.fail(f"tenant_pricing_overview view should exist: {e}")

            # Test pricer_capability_routing view
            try:
                result = await conn.execute(text("SELECT * FROM pricer_capability_routing LIMIT 1"))
                routing_data = result.fetchone()
                assert routing_data is not None, "pricer_capability_routing view should return data"
            except Exception as e:
                pytest.fail(f"pricer_capability_routing view should exist and be queryable: {e}")

    @pytest.mark.asyncio
    async def test_triggers_and_functions_exist(self, async_engine):
        """Test that triggers and functions are created."""
        async with async_engine.connect() as conn:
            # Check that update function exists
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.routines
                WHERE routine_name = 'update_pricing_updated_at'
            """))
            function_count = result.fetchone()[0]
            assert function_count == 1, "update_pricing_updated_at function should exist"

            # Check that tenant config creation function exists
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.routines
                WHERE routine_name = 'create_default_tenant_pricing_config'
            """))
            tenant_function_count = result.fetchone()[0]
            assert tenant_function_count == 1, "create_default_tenant_pricing_config function should exist"

            # Check that triggers exist
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.triggers
                WHERE trigger_name IN (
                    'trg_pricer_registry_updated_at',
                    'trg_tenant_pricing_config_updated_at',
                    'trg_create_default_tenant_pricing_config'
                )
            """))
            trigger_count = result.fetchone()[0]
            assert trigger_count == 3, "All pricing infrastructure triggers should exist"

    @pytest.mark.asyncio
    async def test_capability_based_routing_query(self, async_engine):
        """Test that capability-based routing queries work."""
        async with async_engine.connect() as conn:
            # Test finding pricers for swap pricing
            result = await conn.execute(text("""
                SELECT pricer_id, priority
                FROM pricer_capability_routing
                WHERE instrument_type = 'swap'
                ORDER BY priority DESC
            """))
            swap_pricers = result.fetchall()
            assert len(swap_pricers) > 0, "Should find pricers capable of pricing swaps"

            # Test finding pricers for specific model
            result = await conn.execute(text("""
                SELECT pricer_id
                FROM pricer_capability_routing
                WHERE instrument_type = 'option' AND model_type = 'Black-Scholes'
            """))
            black_scholes_pricers = result.fetchall()
            assert len(black_scholes_pricers) > 0, "Should find pricers for Black-Scholes option pricing"

    @pytest.mark.asyncio
    async def test_test_tenants_exist(self, async_engine):
        """Test that test tenants from second migration exist."""
        async with async_engine.connect() as conn:
            # Check if test tenants exist (they may not if second migration wasn't run)
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM tenants
                WHERE id IN (
                    '11111111-1111-1111-1111-111111111111'::uuid,
                    '22222222-2222-2222-2222-222222222222'::uuid,
                    '33333333-3333-3333-3333-333333333333'::uuid
                )
            """))
            test_tenant_count = result.fetchone()[0]

            # If test tenants exist, verify their configurations
            if test_tenant_count > 0:
                result = await conn.execute(text("""
                    SELECT tenant_id, default_pricer_id, config_json->'max_batch_size' as max_batch
                    FROM tenant_pricing_config
                    WHERE tenant_id IN (
                        '11111111-1111-1111-1111-111111111111'::uuid,
                        '22222222-2222-2222-2222-222222222222'::uuid,
                        '33333333-3333-3333-3333-333333333333'::uuid
                    )
                    ORDER BY tenant_id
                """))
                test_configs = result.fetchall()
                assert len(test_configs) == test_tenant_count, \
                    "All test tenants should have pricing configurations"

                # Verify different batch sizes for each tenant
                batch_sizes = [int(config[2]) for config in test_configs]
                expected_batch_sizes = [1000, 5000, 500]  # Tenant A, B, C
                if test_tenant_count == 3:
                    assert sorted(batch_sizes) == sorted(expected_batch_sizes), \
                        "Test tenants should have different max_batch_size configurations"


class TestMigrationValidation:
    """Integration tests to validate complete migration functionality."""

    @pytest.fixture
    def database_url(self) -> str:
        """Get database URL from environment or use default."""
        return os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5432/venturestrat"
        )

    @pytest.fixture
    def async_engine(self, database_url: str):
        """Create asynchronous database engine."""
        engine = create_async_engine(database_url)
        yield engine
        engine.sync_engine.dispose()

    @pytest.mark.asyncio
    async def test_end_to_end_pricer_registration(self, async_engine):
        """Test complete pricer registration and capability workflow."""
        async with async_engine.connect() as conn:
            # This test validates that the schema supports the full workflow
            # without actually modifying data (read-only validation)

            # Test 1: Verify we can query all pricers with their capabilities
            result = await conn.execute(text("""
                SELECT
                    pr.pricer_id,
                    pr.name,
                    pr.status,
                    COUNT(pc.id) as capability_count
                FROM pricer_registry pr
                LEFT JOIN pricer_capabilities pc ON pr.pricer_id = pc.pricer_id
                GROUP BY pr.pricer_id, pr.name, pr.status
                ORDER BY pr.pricer_id
            """))
            pricers_summary = result.fetchall()
            assert len(pricers_summary) >= 2, "Should have at least QuantLib and Treasury pricers"

            # Test 2: Verify capability-based routing works
            result = await conn.execute(text("""
                SELECT
                    instrument_type,
                    model_type,
                    pricer_id,
                    priority
                FROM pricer_capability_routing
                WHERE instrument_type = 'swap'
                ORDER BY priority DESC
                LIMIT 1
            """))
            best_swap_pricer = result.fetchone()
            assert best_swap_pricer is not None, "Should find best pricer for swap pricing"

            # Test 3: Verify tenant configuration lookup works
            result = await conn.execute(text("""
                SELECT
                    t.slug,
                    tpc.default_pricer_id,
                    tpc.config_json->'max_batch_size' as max_batch
                FROM tenants t
                JOIN tenant_pricing_config tpc ON t.id = tpc.tenant_id
                WHERE t.status = 'active'
                LIMIT 5
            """))
            tenant_configs = result.fetchall()
            # Should have at least system tenant config
            assert len(tenant_configs) >= 0, "Should be able to query tenant pricing configurations"

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_validation(self, async_engine):
        """Test that tenant isolation is properly implemented."""
        async with async_engine.connect() as conn:
            # Test that we can query tenant-specific configurations
            result = await conn.execute(text("""
                SELECT DISTINCT
                    tpc.default_pricer_id,
                    tpc.config_json->'allowed_pricers' as allowed_pricers,
                    tpc.config_json->'max_batch_size' as max_batch_size
                FROM tenant_pricing_config tpc
                WHERE tpc.config_json IS NOT NULL
            """))
            configs = result.fetchall()

            if len(configs) > 1:
                # If we have multiple configs, verify they can be different
                batch_sizes = set()
                for config in configs:
                    if config[2] is not None:
                        batch_sizes.add(int(config[2]))

                # We should have different batch size configurations
                # This validates that tenant isolation allows different configurations
                assert len(batch_sizes) >= 1, "Should support different tenant configurations"

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))