#!/usr/bin/env python3
"""
Test script to validate pricing infrastructure migration setup.

This script performs basic validation of the Alembic migration setup
without requiring a full database connection.

Run: python test_migration_setup.py
"""

import os
import sys
from pathlib import Path


def test_migration_files_exist():
    """Test that migration files are created."""
    base_dir = Path(__file__).parent

    # Check Alembic configuration
    alembic_ini = base_dir / "alembic.ini"
    assert alembic_ini.exists(), "alembic.ini should exist"

    # Check migrations directory
    migrations_dir = base_dir / "migrations"
    assert migrations_dir.exists(), "migrations directory should exist"

    # Check migration structure
    env_py = migrations_dir / "env.py"
    assert env_py.exists(), "migrations/env.py should exist"

    script_mako = migrations_dir / "script.py.mako"
    assert script_mako.exists(), "migrations/script.py.mako should exist"

    versions_dir = migrations_dir / "versions"
    assert versions_dir.exists(), "migrations/versions directory should exist"

    print("✅ All migration directory structure files exist")


def test_migration_versions_exist():
    """Test that migration version files are created."""
    base_dir = Path(__file__).parent
    versions_dir = base_dir / "migrations" / "versions"

    # Check first migration
    pricing_infrastructure_migration = versions_dir / "20260110_1400_001_create_pricing_infrastructure.py"
    assert pricing_infrastructure_migration.exists(), \
        "Pricing infrastructure migration should exist"

    # Check second migration
    test_data_migration = versions_dir / "20260110_1500_002_add_pricing_test_data.py"
    assert test_data_migration.exists(), \
        "Test data migration should exist"

    print("✅ Migration version files exist")


def test_migration_content():
    """Test that migration files contain expected content."""
    base_dir = Path(__file__).parent
    versions_dir = base_dir / "migrations" / "versions"

    # Check first migration content
    pricing_migration = versions_dir / "20260110_1400_001_create_pricing_infrastructure.py"
    content = pricing_migration.read_text()

    # Check for key tables
    assert "op.create_table" in content, "Migration should create tables"
    assert "pricer_registry" in content, "Should create pricer_registry table"
    assert "pricer_capabilities" in content, "Should create pricer_capabilities table"
    assert "tenant_pricing_config" in content, "Should create tenant_pricing_config table"

    # Check for constraints
    assert "CheckConstraint" in content, "Should include CHECK constraints"
    assert "ForeignKeyConstraint" in content, "Should include foreign key constraints"

    # Check for indexes
    assert "op.create_index" in content, "Should create indexes"

    # Check for seed data
    assert "quantlib-v1.18" in content, "Should include QuantLib seed data"
    assert "treasury-v2.3" in content, "Should include Treasury seed data"

    # Check for views (created via op.execute)
    assert "op.execute" in content, "Should execute SQL for views and triggers"
    assert "pricer_overview" in content, "Should create pricer_overview view"

    # Check for triggers
    assert "CREATE TRIGGER" in content, "Should create triggers via op.execute"
    assert "update_pricing_updated_at" in content, "Should create update trigger function"

    print("✅ Migration content validation passed")


def test_alembic_configuration():
    """Test that Alembic configuration is valid."""
    base_dir = Path(__file__).parent
    alembic_ini = base_dir / "alembic.ini"

    content = alembic_ini.read_text()

    # Check key configuration
    assert "script_location = migrations" in content, "Should set script location"
    assert "file_template" in content, "Should set file template"
    assert "postgresql" in content, "Should configure for PostgreSQL"

    print("✅ Alembic configuration is valid")


def test_env_py_configuration():
    """Test that env.py is properly configured."""
    base_dir = Path(__file__).parent
    env_py = base_dir / "migrations" / "env.py"

    content = env_py.read_text()

    # Check imports
    assert "from registry.models" in content, "Should import registry models"
    assert "BaseModel" in content, "Should import BaseModel"

    # Check configuration
    assert "target_metadata" in content, "Should configure target metadata"
    assert "include_schemas" in content, "Should include schemas"

    print("✅ env.py configuration is valid")


def test_test_files_exist():
    """Test that test files are created."""
    base_dir = Path(__file__).parent

    # Check test file
    test_file = base_dir / "tests" / "test_migrations.py"
    assert test_file.exists(), "Migration tests should exist"

    # Check pytest config
    pytest_ini = base_dir / "pytest.ini"
    assert pytest_ini.exists(), "pytest.ini should exist"

    print("✅ Test files exist")


def main():
    """Run all validation tests."""
    print("🔍 Validating pricing infrastructure migration setup...")
    print()

    try:
        test_migration_files_exist()
        test_migration_versions_exist()
        test_migration_content()
        test_alembic_configuration()
        test_env_py_configuration()
        test_test_files_exist()

        print()
        print("🎉 All validation tests passed!")
        print()
        print("Migration setup is complete and ready for deployment.")
        print()
        print("Next steps:")
        print("1. Run migrations: alembic upgrade head")
        print("2. Run tests: pytest tests/test_migrations.py")
        print("3. Verify database schema manually")

        return 0

    except AssertionError as e:
        print(f"❌ Validation failed: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())