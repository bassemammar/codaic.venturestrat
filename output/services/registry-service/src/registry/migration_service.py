"""
Migration service for adding multi-tenant support to registry database.

This service provides programmatic migration execution and verification
for adding tenant_id fields to existing registry tables.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)

# System tenant constant
SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000000"


class MigrationError(Exception):
    """Raised when migration fails."""

    pass


class MigrationVerificationError(Exception):
    """Raised when migration verification fails."""

    pass


class RegistryMigrationService:
    """
    Service for executing and verifying multi-tenant migration.

    This service handles:
    - Pre-migration validation
    - Migration execution
    - Post-migration verification
    - Rollback operations
    """

    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.migration_file = (
            Path(__file__).parent.parent.parent / "migrations" / "003_add_tenant_isolation.sql"
        )

    async def execute_migration(self, dry_run: bool = False) -> dict:
        """
        Execute the tenant isolation migration.

        Args:
            dry_run: If True, performs validation only without executing

        Returns:
            Migration result dictionary with statistics and status
        """
        logger.info(f"Starting tenant isolation migration (dry_run={dry_run})")

        # Pre-migration validation
        validation_result = await self._validate_pre_migration()
        if not validation_result["valid"]:
            raise MigrationError(f"Pre-migration validation failed: {validation_result['errors']}")

        pre_stats = await self._collect_pre_migration_stats()
        logger.info(f"Pre-migration stats: {pre_stats}")

        if dry_run:
            logger.info("Dry run mode - migration validation complete")
            return {
                "status": "dry_run_success",
                "pre_stats": pre_stats,
                "validation": validation_result,
            }

        # Execute migration
        start_time = datetime.utcnow()
        try:
            migration_result = await self._execute_migration_sql()
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            logger.info(f"Migration executed in {execution_time:.2f} seconds")

        except Exception as e:
            logger.error(f"Migration execution failed: {e}")
            raise MigrationError(f"Migration execution failed: {e}")

        # Post-migration verification
        try:
            post_stats = await self._collect_post_migration_stats()
            verification_result = await self._verify_migration(pre_stats, post_stats)

            if not verification_result["valid"]:
                raise MigrationVerificationError(
                    f"Migration verification failed: {verification_result['errors']}"
                )

        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            # Attempt automatic rollback
            logger.info("Attempting automatic rollback...")
            await self._rollback_migration()
            raise MigrationVerificationError(f"Migration verified failed, rolled back: {e}")

        result = {
            "status": "success",
            "execution_time": execution_time,
            "pre_stats": pre_stats,
            "post_stats": post_stats,
            "verification": verification_result,
            "migration_result": migration_result,
        }

        logger.info("Migration completed successfully")
        return result

    async def verify_migration(self) -> dict:
        """
        Verify current migration status without executing.

        Returns:
            Verification result dictionary
        """
        logger.info("Verifying current migration status")

        # Check if migration has been applied
        schema_check = await self._check_tenant_schema()

        if not schema_check["has_tenant_columns"]:
            return {
                "status": "not_migrated",
                "message": "Tenant columns not found - migration not applied",
                "schema_check": schema_check,
            }

        # Verify data integrity
        data_check = await self._verify_data_integrity()

        return {
            "status": "migrated" if data_check["valid"] else "migration_incomplete",
            "schema_check": schema_check,
            "data_check": data_check,
        }

    async def rollback_migration(self) -> dict:
        """
        Rollback the tenant isolation migration.

        Returns:
            Rollback result dictionary
        """
        logger.warning("Starting migration rollback")

        start_time = datetime.utcnow()
        try:
            result = await self._rollback_migration()
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            logger.info(f"Rollback completed in {execution_time:.2f} seconds")

            return {
                "status": "rollback_success",
                "execution_time": execution_time,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise MigrationError(f"Rollback failed: {e}")

    async def _validate_pre_migration(self) -> dict:
        """Validate system state before migration."""
        errors = []

        try:
            conn = await asyncpg.connect(self.connection_url, ssl=False)

            # Check if tenant table exists
            tenant_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'tenants'
                )
            """
            )

            if not tenant_exists:
                errors.append("Tenants table does not exist - run migration 002 first")

            # Check if system tenant exists
            system_tenant = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM tenants
                    WHERE id = $1
                )
            """,
                SYSTEM_TENANT_ID,
            )

            if not system_tenant:
                errors.append("System tenant does not exist")

            # Check if tenant columns already exist
            existing_columns = await conn.fetch(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_name IN ('service_registrations', 'service_health_events', 'service_dependencies')
                AND column_name = 'tenant_id'
            """
            )

            if existing_columns:
                errors.append(
                    f"Tenant columns already exist: {[row['table_name'] for row in existing_columns]}"
                )

            # Check database connectivity and permissions
            try:
                await conn.execute("SELECT 1")
            except Exception as e:
                errors.append(f"Database connectivity issue: {e}")

            await conn.close()

        except Exception as e:
            errors.append(f"Validation error: {e}")

        return {"valid": len(errors) == 0, "errors": errors}

    async def _collect_pre_migration_stats(self) -> dict:
        """Collect statistics before migration."""
        conn = await asyncpg.connect(self.connection_url, ssl=False)

        stats = {}

        # Count records in each table
        for table in ["service_registrations", "service_health_events", "service_dependencies"]:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = count

        # Check constraints
        constraints = await conn.fetch(
            """
            SELECT table_name, constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name IN ('service_registrations', 'service_health_events', 'service_dependencies')
        """
        )

        stats["existing_constraints"] = [dict(row) for row in constraints]

        # Check indexes
        indexes = await conn.fetch(
            """
            SELECT schemaname, tablename, indexname
            FROM pg_indexes
            WHERE tablename IN ('service_registrations', 'service_health_events', 'service_dependencies')
        """
        )

        stats["existing_indexes"] = [dict(row) for row in indexes]

        await conn.close()
        return stats

    async def _execute_migration_sql(self) -> dict:
        """Execute the migration SQL file."""
        if not self.migration_file.exists():
            raise MigrationError(f"Migration file not found: {self.migration_file}")

        migration_sql = self.migration_file.read_text()

        conn = await asyncpg.connect(self.connection_url, ssl=False)

        try:
            # Execute migration in a transaction
            async with conn.transaction():
                result = await conn.execute(migration_sql)

            logger.info(f"Migration SQL executed: {result}")

            return {"sql_result": result}

        except Exception as e:
            logger.error(f"Migration SQL execution failed: {e}")
            raise
        finally:
            await conn.close()

    async def _collect_post_migration_stats(self) -> dict:
        """Collect statistics after migration."""
        conn = await asyncpg.connect(self.connection_url, ssl=False)

        stats = {}

        # Count records in each table (should be same as before)
        for table in ["service_registrations", "service_health_events", "service_dependencies"]:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            system_tenant_count = await conn.fetchval(
                f"SELECT COUNT(*) FROM {table} WHERE tenant_id = $1", SYSTEM_TENANT_ID
            )

            stats[f"{table}_count"] = count
            stats[f"{table}_system_tenant_count"] = system_tenant_count

        # Check new constraints
        constraints = await conn.fetch(
            """
            SELECT table_name, constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name IN ('service_registrations', 'service_health_events', 'service_dependencies')
            AND constraint_name LIKE '%tenant%'
        """
        )

        stats["new_tenant_constraints"] = [dict(row) for row in constraints]

        # Check new indexes
        indexes = await conn.fetch(
            """
            SELECT schemaname, tablename, indexname
            FROM pg_indexes
            WHERE tablename IN ('service_registrations', 'service_health_events', 'service_dependencies')
            AND indexname LIKE '%tenant%'
        """
        )

        stats["new_tenant_indexes"] = [dict(row) for row in indexes]

        await conn.close()
        return stats

    async def _verify_migration(self, pre_stats: dict, post_stats: dict) -> dict:
        """Verify migration completed successfully."""
        errors = []

        # Verify record counts unchanged
        for table in ["service_registrations", "service_health_events", "service_dependencies"]:
            pre_count = pre_stats[f"{table}_count"]
            post_count = post_stats[f"{table}_count"]
            system_count = post_stats[f"{table}_system_tenant_count"]

            if pre_count != post_count:
                errors.append(f"{table}: record count changed from {pre_count} to {post_count}")

            if post_count != system_count:
                errors.append(
                    f"{table}: {post_count - system_count} records not assigned to system tenant"
                )

        # Verify constraints added
        expected_constraints = [
            "fk_service_registrations_tenant",
            "fk_service_health_events_tenant",
            "fk_service_dependencies_tenant",
        ]

        actual_constraints = [
            c["constraint_name"] for c in post_stats.get("new_tenant_constraints", [])
        ]

        for constraint in expected_constraints:
            if constraint not in actual_constraints:
                errors.append(f"Missing constraint: {constraint}")

        # Verify indexes added
        expected_indexes = [
            "idx_service_registrations_tenant_id",
            "idx_service_health_events_tenant_id",
            "idx_service_dependencies_tenant_id",
        ]

        actual_indexes = [i["indexname"] for i in post_stats.get("new_tenant_indexes", [])]

        for index in expected_indexes:
            if index not in actual_indexes:
                errors.append(f"Missing index: {index}")

        return {"valid": len(errors) == 0, "errors": errors}

    async def _check_tenant_schema(self) -> dict:
        """Check if tenant columns exist in tables."""
        conn = await asyncpg.connect(self.connection_url, ssl=False)

        # Check for tenant_id columns
        tenant_columns = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.columns
            WHERE table_name IN ('service_registrations', 'service_health_events', 'service_dependencies')
            AND column_name = 'tenant_id'
        """
        )

        tables_with_tenant = [row["table_name"] for row in tenant_columns]
        expected_tables = ["service_registrations", "service_health_events", "service_dependencies"]

        await conn.close()

        return {
            "has_tenant_columns": len(tables_with_tenant) == 3,
            "tables_with_tenant": tables_with_tenant,
            "expected_tables": expected_tables,
        }

    async def _verify_data_integrity(self) -> dict:
        """Verify data integrity after migration."""
        conn = await asyncpg.connect(self.connection_url, ssl=False)

        errors = []

        # Check for NULL tenant_id values
        for table in ["service_registrations", "service_health_events", "service_dependencies"]:
            null_count = await conn.fetchval(
                f"SELECT COUNT(*) FROM {table} WHERE tenant_id IS NULL"
            )
            if null_count > 0:
                errors.append(f"{table}: {null_count} records with NULL tenant_id")

        # Check foreign key constraints
        try:
            # Test inserting invalid tenant_id (should fail)
            await conn.execute(
                """
                INSERT INTO service_registrations (service_name, instance_id, version, address, port, protocol, tenant_id)
                VALUES ('test', 'test', '1.0', '127.0.0.1', 8080, 'http', '11111111-1111-1111-1111-111111111111')
            """
            )

            errors.append("Foreign key constraint not working - invalid tenant_id accepted")

        except asyncpg.ForeignKeyViolationError:
            # This is expected - constraint is working
            pass
        except Exception as e:
            errors.append(f"Unexpected error testing foreign key: {e}")

        await conn.close()

        return {"valid": len(errors) == 0, "errors": errors}

    async def _rollback_migration(self) -> dict:
        """Rollback the migration by dropping tenant columns."""
        conn = await asyncpg.connect(self.connection_url, ssl=False)

        rollback_sql = """
        BEGIN;

        -- Drop tenant columns
        ALTER TABLE service_registrations DROP COLUMN IF EXISTS tenant_id;
        ALTER TABLE service_health_events DROP COLUMN IF EXISTS tenant_id;
        ALTER TABLE service_dependencies DROP COLUMN IF EXISTS tenant_id;

        -- Restore original unique constraint on service_dependencies
        ALTER TABLE service_dependencies
        DROP CONSTRAINT IF EXISTS service_dependencies_tenant_service_depends_unique;

        ALTER TABLE service_dependencies
        ADD CONSTRAINT service_dependencies_service_name_depends_on_key
        UNIQUE(service_name, depends_on);

        -- Recreate original views without tenant_id
        DROP VIEW IF EXISTS active_services;
        DROP VIEW IF EXISTS service_uptime_24h;

        CREATE VIEW active_services AS
        SELECT
            service_name,
            COUNT(*) as instance_count,
            array_agg(DISTINCT version) as versions,
            MIN(registered_at) as first_registered,
            MAX(registered_at) as last_registration
        FROM service_registrations
        WHERE deregistered_at IS NULL
        GROUP BY service_name;

        CREATE VIEW service_uptime_24h AS
        SELECT
            service_name,
            COUNT(*) FILTER (WHERE new_status = 'healthy') as healthy_count,
            COUNT(*) FILTER (WHERE new_status = 'critical') as critical_count,
            ROUND(
                COUNT(*) FILTER (WHERE new_status = 'healthy')::numeric /
                NULLIF(COUNT(*), 0) * 100,
                2
            ) as health_percentage
        FROM service_health_events
        WHERE event_at > NOW() - INTERVAL '24 hours'
        GROUP BY service_name;

        COMMIT;
        """

        try:
            result = await conn.execute(rollback_sql)
            logger.info(f"Rollback SQL executed: {result}")

            return {"sql_result": result}

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise
        finally:
            await conn.close()


# CLI interface for migration service
async def main():
    """CLI interface for executing migrations."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Registry Migration Service")
    parser.add_argument(
        "action", choices=["migrate", "verify", "rollback"], help="Action to perform"
    )
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run (validation only)")
    parser.add_argument("--connection-url", required=True, help="Database connection URL")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    service = RegistryMigrationService(args.connection_url)

    try:
        if args.action == "migrate":
            result = await service.execute_migration(dry_run=args.dry_run)
            print(json.dumps(result, indent=2, default=str))

        elif args.action == "verify":
            result = await service.verify_migration()
            print(json.dumps(result, indent=2))

        elif args.action == "rollback":
            result = await service.rollback_migration()
            print(json.dumps(result, indent=2, default=str))

        sys.exit(0)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
