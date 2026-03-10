#!/usr/bin/env python3
"""
Registry Migration CLI Tool

This script provides a command-line interface for executing and managing
the multi-tenant migration for the registry service.

Usage:
    python migrate.py migrate --connection-url <url>      # Execute migration
    python migrate.py verify --connection-url <url>       # Verify migration status
    python migrate.py rollback --connection-url <url>     # Rollback migration
    python migrate.py status --connection-url <url>       # Show current status

Examples:
    # Dry run migration
    python migrate.py migrate --connection-url postgresql://user:pass@localhost/registry --dry-run

    # Execute migration
    python migrate.py migrate --connection-url postgresql://user:pass@localhost/registry

    # Verify migration
    python migrate.py verify --connection-url postgresql://user:pass@localhost/registry

    # Check status
    python migrate.py status --connection-url postgresql://user:pass@localhost/registry
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Add the service source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from registry.migration_service import (
    MigrationError,
    MigrationVerificationError,
    RegistryMigrationService,
)


class MigrationCLI:
    """Command-line interface for migration operations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def migrate(self, connection_url: str, dry_run: bool = False) -> int:
        """Execute migration."""
        try:
            service = RegistryMigrationService(connection_url)

            print(f"🚀 Starting migration (dry_run={dry_run})")
            print("─" * 50)

            result = await service.execute_migration(dry_run=dry_run)

            if dry_run:
                print("✅ Dry run validation successful!")
                self._print_validation_summary(result)
            else:
                print("✅ Migration completed successfully!")
                self._print_migration_summary(result)

            return 0

        except MigrationError as e:
            print(f"❌ Migration failed: {e}")
            return 1
        except MigrationVerificationError as e:
            print(f"❌ Migration verification failed: {e}")
            return 1
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            self.logger.exception("Unexpected error during migration")
            return 1

    async def verify(self, connection_url: str) -> int:
        """Verify migration status."""
        try:
            service = RegistryMigrationService(connection_url)

            print("🔍 Verifying migration status")
            print("─" * 50)

            result = await service.verify_migration()

            if result["status"] == "migrated":
                print("✅ Migration verified successfully!")
                print("   All tenant columns and constraints are in place.")
            elif result["status"] == "not_migrated":
                print("ℹ️  Migration not applied yet.")
                print("   Use 'migrate' command to apply the migration.")
            else:
                print("⚠️  Migration incomplete or corrupted.")
                print("   Consider rolling back and re-running the migration.")

            self._print_verification_details(result)

            return 0

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            self.logger.exception("Verification error")
            return 1

    async def rollback(self, connection_url: str, force: bool = False) -> int:
        """Rollback migration."""
        try:
            if not force:
                print("⚠️  WARNING: This will remove tenant isolation from the registry service.")
                print("   All tenant_id columns and constraints will be dropped.")
                print("   This action cannot be undone without re-running the migration.")
                print()

                response = input("Are you sure you want to continue? [y/N]: ").strip().lower()
                if response not in ["y", "yes"]:
                    print("Rollback cancelled.")
                    return 0

            service = RegistryMigrationService(connection_url)

            print("🔄 Starting migration rollback")
            print("─" * 50)

            result = await service.rollback_migration()

            print("✅ Rollback completed successfully!")
            self._print_rollback_summary(result)

            return 0

        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            self.logger.exception("Rollback error")
            return 1

    async def status(self, connection_url: str) -> int:
        """Show current migration status."""
        try:
            service = RegistryMigrationService(connection_url)

            print("📊 Registry Migration Status")
            print("─" * 50)

            # Check migration status
            result = await service.verify_migration()

            print(f"Migration Status: {result['status'].upper()}")

            if result["status"] == "migrated":
                print("🟢 Migration is applied and verified")
            elif result["status"] == "not_migrated":
                print("🔴 Migration not applied")
            else:
                print("🟡 Migration partially applied or corrupted")

            # Show schema details
            schema = result.get("schema_check", {})
            if schema:
                print("\nSchema Status:")
                print(f"  Tables with tenant_id: {len(schema.get('tables_with_tenant', []))}/3")
                print(f"  Expected tables: {', '.join(schema.get('expected_tables', []))}")

            # Show data integrity status
            data_check = result.get("data_check", {})
            if data_check:
                if data_check["valid"]:
                    print("  Data integrity: ✅ Valid")
                else:
                    print("  Data integrity: ❌ Issues found")
                    for error in data_check.get("errors", []):
                        print(f"    - {error}")

            return 0

        except Exception as e:
            print(f"❌ Status check failed: {e}")
            self.logger.exception("Status check error")
            return 1

    def _print_validation_summary(self, result: dict[str, Any]):
        """Print dry run validation summary."""
        pre_stats = result.get("pre_stats", {})

        print("\nPre-Migration Statistics:")
        print(f"  Service Registrations: {pre_stats.get('service_registrations_count', 0)}")
        print(f"  Health Events: {pre_stats.get('service_health_events_count', 0)}")
        print(f"  Dependencies: {pre_stats.get('service_dependencies_count', 0)}")

        validation = result.get("validation", {})
        if validation.get("valid"):
            print("\nValidation: ✅ All checks passed")
        else:
            print("\nValidation: ❌ Issues found:")
            for error in validation.get("errors", []):
                print(f"  - {error}")

    def _print_migration_summary(self, result: dict[str, Any]):
        """Print migration execution summary."""
        pre_stats = result.get("pre_stats", {})
        post_stats = result.get("post_stats", {})

        print(f"\nExecution Time: {result.get('execution_time', 0):.2f} seconds")

        print("\nRecord Migration Summary:")
        for table in ["service_registrations", "service_health_events", "service_dependencies"]:
            pre_count = pre_stats.get(f"{table}_count", 0)
            post_count = post_stats.get(f"{table}_count", 0)
            system_count = post_stats.get(f"{table}_system_tenant_count", 0)

            if pre_count == post_count == system_count:
                status = "✅"
            else:
                status = "❌"

            print(
                f"  {table}: {pre_count} → {post_count} ({system_count} in system tenant) {status}"
            )

        # Show constraints added
        constraints = post_stats.get("new_tenant_constraints", [])
        print(f"\nConstraints Added: {len(constraints)}")
        for constraint in constraints[:3]:  # Show first 3
            print(f"  - {constraint.get('constraint_name', 'unknown')}")

        # Show indexes added
        indexes = post_stats.get("new_tenant_indexes", [])
        print(f"\nIndexes Added: {len(indexes)}")
        for index in indexes[:3]:  # Show first 3
            print(f"  - {index.get('indexname', 'unknown')}")

    def _print_rollback_summary(self, result: dict[str, Any]):
        """Print rollback summary."""
        print(f"\nExecution Time: {result.get('execution_time', 0):.2f} seconds")
        print("\nRollback Operations:")
        print("  ✅ Removed tenant_id columns")
        print("  ✅ Dropped foreign key constraints")
        print("  ✅ Restored original unique constraints")
        print("  ✅ Recreated original views")

    def _print_verification_details(self, result: dict[str, Any]):
        """Print detailed verification information."""
        schema = result.get("schema_check", {})
        if schema:
            print("\nSchema Details:")
            tables_with_tenant = schema.get("tables_with_tenant", [])
            expected_tables = schema.get("expected_tables", [])

            for table in expected_tables:
                if table in tables_with_tenant:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ❌ {table}")

        data_check = result.get("data_check", {})
        if data_check and not data_check["valid"]:
            print("\nData Issues:")
            for error in data_check.get("errors", []):
                print(f"  ❌ {error}")


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("migration.log")],
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Registry Migration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Execute migration")
    migrate_parser.add_argument("--connection-url", required=True, help="Database connection URL")
    migrate_parser.add_argument("--dry-run", action="store_true", help="Perform validation only")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify migration status")
    verify_parser.add_argument("--connection-url", required=True, help="Database connection URL")

    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migration")
    rollback_parser.add_argument("--connection-url", required=True, help="Database connection URL")
    rollback_parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show migration status")
    status_parser.add_argument("--connection-url", required=True, help="Database connection URL")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    setup_logging(args.verbose)

    cli = MigrationCLI()

    try:
        if args.command == "migrate":
            return asyncio.run(cli.migrate(args.connection_url, args.dry_run))
        elif args.command == "verify":
            return asyncio.run(cli.verify(args.connection_url))
        elif args.command == "rollback":
            return asyncio.run(cli.rollback(args.connection_url, args.force))
        elif args.command == "status":
            return asyncio.run(cli.status(args.connection_url))
        else:
            print(f"Unknown command: {args.command}")
            return 1

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logging.exception("Unexpected error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
