#!/usr/bin/env python3
"""
Test Migration with Sample Data Runner

This script implements Task 8.3: Test migration on sample data
It provides a standalone way to test the migration process with realistic sample data.

Usage:
    python test_migration_sample_data.py --connection-url <url>
    python test_migration_sample_data.py --connection-url <url> --verbose
    python test_migration_sample_data.py --connection-url <url> --cleanup-only
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the service source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncpg
from registry.migration_service import (
    SYSTEM_TENANT_ID,
    MigrationError,
    MigrationVerificationError,
    RegistryMigrationService,
)


class SampleDataMigrationTester:
    """Tests migration process with realistic sample data."""

    def __init__(self, connection_url: str, logger: logging.Logger):
        self.connection_url = connection_url
        self.logger = logger
        self.migration_service = RegistryMigrationService(connection_url)

    async def run_comprehensive_test(self) -> dict:
        """Run comprehensive migration test with sample data."""
        self.logger.info("Starting comprehensive migration test with sample data")

        try:
            # Step 1: Setup test environment
            setup_stats = await self._setup_test_environment()
            self.logger.info(f"Test environment setup complete: {setup_stats}")

            # Step 2: Run migration test
            test_result = await self._execute_migration_test()

            # Step 3: Cleanup
            await self._cleanup_test_environment()

            return {
                "status": "success",
                "setup_stats": setup_stats,
                "test_result": test_result,
                "message": "Migration test completed successfully with sample data",
            }

        except Exception as e:
            self.logger.error(f"Migration test failed: {e}")
            # Attempt cleanup on failure
            try:
                await self._cleanup_test_environment()
            except:
                pass
            raise

    async def cleanup_only(self) -> dict:
        """Clean up test environment only."""
        await self._cleanup_test_environment()
        return {"status": "cleanup_complete"}

    async def _setup_test_environment(self) -> dict:
        """Set up complete test environment with sample data."""
        conn = await asyncpg.connect(self.connection_url)

        try:
            # Clean any existing test tables
            await self._cleanup_tables(conn)

            # Create tenants table
            await conn.execute(
                """
                CREATE TABLE tenants (
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

            # Insert system tenant
            await conn.execute(
                """
                INSERT INTO tenants (id, slug, name, status, config)
                VALUES ($1, 'system', 'System', 'active', '{"is_system": true}')
            """,
                SYSTEM_TENANT_ID,
            )

            # Create registry tables (pre-migration schema)
            await self._create_registry_tables(conn)

            # Generate and insert comprehensive sample data
            stats = await self._generate_sample_data(conn)

            self.logger.info(f"Sample data created: {stats}")
            return stats

        finally:
            await conn.close()

    async def _create_registry_tables(self, conn):
        """Create registry service tables in pre-migration state."""
        await conn.execute(
            """
            CREATE TABLE service_registrations (
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
            CREATE TABLE service_health_events (
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
            CREATE TABLE service_dependencies (
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

        # Create original views (pre-migration)
        await conn.execute(
            """
            CREATE VIEW active_services AS
            SELECT
                service_name,
                COUNT(*) as instance_count,
                array_agg(DISTINCT version) as versions,
                MIN(registered_at) as first_registered,
                MAX(registered_at) as last_registration
            FROM service_registrations
            WHERE deregistered_at IS NULL
            GROUP BY service_name
        """
        )

        await conn.execute(
            """
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
            GROUP BY service_name
        """
        )

    async def _generate_sample_data(self, conn) -> dict:
        """Generate comprehensive realistic sample data."""
        stats = {"service_registrations": 0, "service_health_events": 0, "service_dependencies": 0}

        # Realistic financial services microservices
        services = [
            {
                "name": "pricing-service",
                "instances": [
                    ("pricing-001", "1.2.3", "10.0.1.10", 8080, "http", ["production", "pricing"]),
                    ("pricing-002", "1.2.3", "10.0.1.11", 8080, "http", ["production", "pricing"]),
                    (
                        "pricing-003",
                        "1.2.4",
                        "10.0.1.12",
                        8080,
                        "http",
                        ["production", "pricing"],
                    ),  # Newer version
                ],
            },
            {
                "name": "trading-service",
                "instances": [
                    ("trading-001", "2.1.0", "10.0.2.10", 8081, "grpc", ["production", "trading"]),
                    ("trading-002", "2.1.0", "10.0.2.11", 8081, "grpc", ["production", "trading"]),
                ],
            },
            {
                "name": "risk-service",
                "instances": [
                    ("risk-001", "1.8.2", "10.0.3.10", 8082, "http", ["production", "risk"]),
                    ("risk-002", "1.8.2", "10.0.3.11", 8082, "http", ["production", "risk"]),
                ],
            },
            {
                "name": "reference-data-service",
                "instances": [
                    (
                        "refdata-001",
                        "3.0.1",
                        "10.0.4.10",
                        8083,
                        "http",
                        ["production", "reference-data"],
                    )
                ],
            },
            {
                "name": "market-data-service",
                "instances": [
                    (
                        "mktdata-001",
                        "1.5.2",
                        "10.0.5.10",
                        8084,
                        "http",
                        ["production", "market-data"],
                    ),
                    (
                        "mktdata-002",
                        "1.5.1",
                        "10.0.5.11",
                        8084,
                        "http",
                        ["production", "market-data"],
                    ),  # Mixed versions
                ],
            },
            {
                "name": "auth-service",
                "instances": [
                    ("auth-001", "4.1.0", "10.0.6.10", 8085, "http", ["production", "security"]),
                    ("auth-002", "4.1.0", "10.0.6.11", 8085, "http", ["production", "security"]),
                ],
            },
            {
                "name": "notification-service",
                "instances": [
                    (
                        "notify-001",
                        "2.3.1",
                        "10.0.7.10",
                        8086,
                        "http",
                        ["production", "notification"],
                    )
                ],
            },
            {
                "name": "reporting-service",
                "instances": [
                    ("report-001", "1.4.3", "10.0.8.10", 8087, "http", ["production", "reporting"]),
                    ("report-002", "1.4.3", "10.0.8.11", 8087, "http", ["production", "reporting"]),
                ],
            },
        ]

        # Insert service registrations
        for service in services:
            for instance_id, version, address, port, protocol, tags in service["instances"]:
                await conn.execute(
                    """
                    INSERT INTO service_registrations
                    (service_name, instance_id, version, address, port, protocol, tags, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                    service["name"],
                    instance_id,
                    version,
                    address,
                    port,
                    protocol,
                    tags,
                    json.dumps(
                        {
                            "region": "us-east-1",
                            "zone": address.split(".")[-1],  # Use last octet as zone identifier
                            "environment": "production",
                        }
                    ),
                )
                stats["service_registrations"] += 1

        # Generate realistic health events (simulating a week of monitoring data)
        await self._generate_health_events(conn, services, stats)

        # Create realistic service dependencies
        dependencies = [
            ("trading-service", "pricing-service", ">=1.2.0"),
            ("trading-service", "risk-service", ">=1.8.0"),
            ("trading-service", "auth-service", ">=4.0.0"),
            ("trading-service", "reference-data-service", ">=3.0.0"),
            ("trading-service", "notification-service", ">=2.0.0"),
            ("pricing-service", "market-data-service", ">=1.5.0"),
            ("pricing-service", "reference-data-service", ">=3.0.0"),
            ("pricing-service", "auth-service", ">=4.0.0"),
            ("risk-service", "pricing-service", ">=1.2.0"),
            ("risk-service", "market-data-service", ">=1.5.0"),
            ("risk-service", "reference-data-service", ">=3.0.0"),
            ("risk-service", "auth-service", ">=4.0.0"),
            ("reporting-service", "trading-service", ">=2.1.0"),
            ("reporting-service", "risk-service", ">=1.8.0"),
            ("reporting-service", "auth-service", ">=4.0.0"),
            ("market-data-service", "reference-data-service", ">=3.0.0"),
            ("market-data-service", "auth-service", ">=4.0.0"),
            ("notification-service", "auth-service", ">=4.0.0"),
            ("reference-data-service", "auth-service", ">=4.0.0"),
        ]

        for service_name, depends_on, version_constraint in dependencies:
            await conn.execute(
                """
                INSERT INTO service_dependencies
                (service_name, depends_on, version_constraint)
                VALUES ($1, $2, $3)
            """,
                service_name,
                depends_on,
                version_constraint,
            )
            stats["service_dependencies"] += 1

        return stats

    async def _generate_health_events(self, conn, services, stats):
        """Generate realistic health event patterns."""
        base_time = datetime.utcnow() - timedelta(days=7)

        # Different health patterns for different service types
        health_patterns = {
            "pricing-service": [("healthy", 85), ("warning", 10), ("critical", 2), ("healthy", 50)],
            "trading-service": [("healthy", 92), ("warning", 5), ("healthy", 45)],
            "risk-service": [("healthy", 88), ("critical", 3), ("healthy", 35), ("warning", 8)],
            "reference-data-service": [("healthy", 95), ("warning", 3)],
            "market-data-service": [
                ("healthy", 75),
                ("warning", 15),
                ("critical", 5),
                ("healthy", 60),
            ],
            "auth-service": [("healthy", 98), ("warning", 2)],
            "notification-service": [("healthy", 90), ("warning", 8), ("healthy", 25)],
            "reporting-service": [
                ("healthy", 87),
                ("critical", 1),
                ("warning", 12),
                ("healthy", 40),
            ],
        }

        for service in services:
            service_name = service["name"]
            pattern = health_patterns.get(service_name, [("healthy", 50)])

            for instance_id, _, _, _, _, _ in service["instances"]:
                event_time = base_time
                prev_status = None

                for status, count in pattern:
                    for i in range(count):
                        check_output = None
                        if status == "warning":
                            check_output = "High response time detected"
                        elif status == "critical":
                            check_output = "Service unavailable"

                        await conn.execute(
                            """
                            INSERT INTO service_health_events
                            (service_name, instance_id, previous_status, new_status, check_name, check_output, event_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                            service_name,
                            instance_id,
                            prev_status,
                            status,
                            "health_check",
                            check_output,
                            event_time + timedelta(minutes=i * 15),  # Events every 15 minutes
                        )
                        stats["service_health_events"] += 1

                    prev_status = status
                    event_time += timedelta(hours=2)  # Move forward 2 hours for next pattern

    async def _execute_migration_test(self) -> dict:
        """Execute the actual migration test."""
        self.logger.info("Executing migration test")

        # Step 1: Pre-migration validation and stats
        validation_result = await self.migration_service._validate_pre_migration()
        if not validation_result["valid"]:
            raise MigrationError(f"Pre-migration validation failed: {validation_result['errors']}")

        pre_stats = await self.migration_service._collect_pre_migration_stats()
        self.logger.info(f"Pre-migration stats: {pre_stats}")

        # Step 2: Execute migration
        migration_result = await self.migration_service.execute_migration(dry_run=False)

        if migration_result["status"] != "success":
            raise MigrationError(f"Migration failed: {migration_result}")

        self.logger.info(f"Migration completed in {migration_result['execution_time']:.2f} seconds")

        # Step 3: Verify migration
        verification_result = await self.migration_service.verify_migration()
        if verification_result["status"] != "migrated":
            raise MigrationVerificationError(
                f"Migration verification failed: {verification_result}"
            )

        # Step 4: Test tenant-aware functionality
        await self._test_tenant_functionality()

        return {
            "pre_stats": pre_stats,
            "migration_result": migration_result,
            "verification_result": verification_result,
            "tenant_test": "passed",
        }

    async def _test_tenant_functionality(self):
        """Test that tenant-aware functionality works correctly."""
        conn = await asyncpg.connect(self.connection_url)

        try:
            # Test 1: Verify all records assigned to system tenant
            tables = ["service_registrations", "service_health_events", "service_dependencies"]

            for table in tables:
                total_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                system_tenant_count = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {table} WHERE tenant_id = $1", SYSTEM_TENANT_ID
                )

                if total_count != system_tenant_count:
                    raise Exception(
                        f"Not all {table} records assigned to system tenant: {total_count} != {system_tenant_count}"
                    )

            self.logger.info("✅ All records correctly assigned to system tenant")

            # Test 2: Verify foreign key constraints work
            try:
                await conn.execute(
                    """
                    INSERT INTO service_registrations
                    (service_name, instance_id, version, address, port, protocol, tenant_id)
                    VALUES ('test-service', 'test-001', '1.0.0', '127.0.0.1', 9999, 'http', $1)
                """,
                    "11111111-1111-1111-1111-111111111111",
                )  # Invalid tenant
                raise Exception("Foreign key constraint not working - invalid tenant_id accepted")
            except asyncpg.ForeignKeyViolationError:
                pass  # Expected

            self.logger.info("✅ Foreign key constraints working correctly")

            # Test 3: Verify tenant-aware views
            active_services = await conn.fetch("SELECT * FROM active_services LIMIT 5")
            for service in active_services:
                if service["tenant_id"] != SYSTEM_TENANT_ID:
                    raise Exception(f"Active service {service['service_name']} has wrong tenant_id")

            self.logger.info("✅ Tenant-aware views working correctly")

            # Test 4: Test insertion with valid tenant
            await conn.execute(
                """
                INSERT INTO service_registrations
                (service_name, instance_id, version, address, port, protocol, tenant_id)
                VALUES ('test-service', 'test-valid', '1.0.0', '127.0.0.1', 9998, 'http', $1)
            """,
                SYSTEM_TENANT_ID,
            )

            self.logger.info("✅ Can insert with valid tenant_id")

        finally:
            await conn.close()

    async def _cleanup_test_environment(self):
        """Clean up test environment."""
        conn = await asyncpg.connect(self.connection_url)
        try:
            await self._cleanup_tables(conn)
            self.logger.info("Test environment cleaned up")
        finally:
            await conn.close()

    async def _cleanup_tables(self, conn):
        """Drop all test tables."""
        tables = [
            "service_dependencies",
            "service_health_events",
            "service_registrations",
            "tenants",
        ]

        views = ["active_services", "service_uptime_24h"]

        # Drop views first
        for view in views:
            try:
                await conn.execute(f"DROP VIEW IF EXISTS {view} CASCADE")
            except:
                pass

        # Drop tables
        for table in tables:
            try:
                await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            except:
                pass


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Test Migration with Sample Data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--connection-url", required=True, help="Database connection URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument(
        "--cleanup-only", action="store_true", help="Only clean up test environment"
    )

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("migration_sample_test.log"),
        ],
    )

    logger = logging.getLogger(__name__)

    tester = SampleDataMigrationTester(args.connection_url, logger)

    try:
        print("🧪 Registry Migration Sample Data Test")
        print("=" * 50)

        if args.cleanup_only:
            result = await tester.cleanup_only()
            print("✅ Cleanup completed")
        else:
            result = await tester.run_comprehensive_test()

            print(f"\n✅ Test Status: {result['status']}")
            print(f"📊 Setup Stats: {result['setup_stats']}")

            if "test_result" in result:
                test_result = result["test_result"]
                print(
                    f"⏱️  Migration Time: {test_result['migration_result']['execution_time']:.2f}s"
                )
                print(f"🔍 Verification: {test_result['verification_result']['status']}")
                print(f"🎯 Tenant Test: {test_result['tenant_test']}")

            print(f"\n{result['message']}")

        return 0

    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
