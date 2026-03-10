"""Alembic environment for registry-service.

This file provides the Alembic environment for registry-service with:
- Schema-aware table creation
- Cross-service model inheritance support
- Auto-discovery of models
"""

import importlib
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Import VentureStrat models
try:
    from venturestrat.models import ModelRegistry
    from venturestrat.models.base import BaseModel

    MODEL_REGISTRY_AVAILABLE = True
except ImportError:
    MODEL_REGISTRY_AVAILABLE = False

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Service configuration
SERVICE_NAME = "registry-service"
SCHEMA_NAME = "registry"


def get_models_metadata():
    """Get metadata with all registered models."""
    if not MODEL_REGISTRY_AVAILABLE:
        # Fallback: create empty metadata
        from sqlalchemy import MetaData

        return MetaData()

    # Auto-discover and import models from this service
    import sys
    from pathlib import Path

    service_dir = Path(__file__).parent.parent

    # Add VentureStrat SDK to path for BaseModel imports
    repo_root = service_dir.parent.parent
    sdk_path = repo_root / "sdk" / "venturestrat-models" / "src"
    if sdk_path.exists() and str(sdk_path) not in sys.path:
        sys.path.insert(0, str(sdk_path))

    # Add service directory to path for imports
    if str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))

    # Strategy 1: NEW codegen structure (infrastructure/orm/*.py)
    orm_dir = service_dir / "infrastructure" / "orm"
    if orm_dir.exists() and orm_dir.is_dir():
        imported_count = 0
        for py_file in sorted(orm_dir.glob("*.py")):
            if py_file.stem != "__init__" and not py_file.stem.startswith("_"):
                try:
                    module_name = f"infrastructure.orm.{py_file.stem}"
                    importlib.import_module(module_name)
                    imported_count += 1
                except ImportError as e:
                    print(f"  Warning: Could not import {module_name}: {e}")

        if imported_count > 0:
            models_imported = True
        else:
            models_imported = False
    else:
        # Strategy 2: Try OLD structure (src/*/models)
        if str(service_dir) not in sys.path:
            sys.path.insert(0, str(service_dir))

        model_paths = [
            "registry.models",  # Actual path for registry-service
            "models",
            "src.models",
            f"{SERVICE_NAME.replace('-', '_')}.models",
        ]

        models_imported = False
        for model_path in model_paths:
            try:
                importlib.import_module(model_path)
                models_imported = True
                break
            except ImportError:
                continue

    if not models_imported:
        print("WARNING - No models were imported!")

    # Get metadata from ModelRegistry
    metadata = ModelRegistry.get_metadata()
    if metadata is None:
        from sqlalchemy import MetaData

        metadata = MetaData()

        # Create tables for all registered models
        for model_name, model_class in ModelRegistry.get_all_models().items():
            if hasattr(model_class, "_schema") and model_class._schema == SCHEMA_NAME:
                try:
                    model_class._create_table(metadata)
                except Exception as e:
                    # Log error but continue
                    print(f"Warning: Could not create table for {model_name}: {e}")

    return metadata


# Set target_metadata at module level for autogenerate
target_metadata = get_models_metadata()


def process_revision_directives(context, revision, directives):
    """Reorder table creation operations based on foreign key dependencies.

    This hook is required for Alembic autogenerate to populate migration operations.
    Without it, autogenerate produces empty migration files.
    """
    import logging
    from collections import defaultdict
    from graphlib import CycleError, TopologicalSorter

    from alembic.operations import ops

    logger = logging.getLogger("alembic.env")

    print("[DEBUG] process_revision_directives CALLED")

    # Process directives (this hook is only called during autogenerate)
    if directives and len(directives) > 0:
        script = directives[0]
        if script.upgrade_ops:
            # Debug: log total operations before filtering
            total_ops = len(script.upgrade_ops.ops)
            print(f"[DEBUG] Total operations before filtering: {total_ops}")
            print(f"[DEBUG] Target schema: {SCHEMA_NAME}")

            # Filter operations - only keep those for this service's schema
            filtered_ops = []

            for i, op in enumerate(script.upgrade_ops.ops):
                # Get operation schema
                op_schema = getattr(op, "schema", None)
                op_type = type(op).__name__

                # Debug: log first few operations
                if i < 3:
                    print(
                        f"[DEBUG] Op[{i}]: type={op_type}, schema={op_schema}, matches={op_schema == SCHEMA_NAME}"
                    )

                # Keep only operations for this service's schema
                if op_schema == SCHEMA_NAME:
                    filtered_ops.append(op)

            # Replace with filtered operations
            script.upgrade_ops.ops = filtered_ops

            print(f"[DEBUG] Filtered to {len(filtered_ops)} operations for schema {SCHEMA_NAME}")

            # Separate operations by type for reordering
            create_table_ops = []
            other_ops = []

            for op in filtered_ops:
                if isinstance(op, ops.CreateTableOp):
                    create_table_ops.append(op)
                else:
                    other_ops.append(op)

            print(
                f"[DEBUG] After type separation: {len(create_table_ops)} create_table, {len(other_ops)} other"
            )

            if len(create_table_ops) >= 1:
                print("[DEBUG] Entering reordering logic")
                try:
                    # Build dependency graph from metadata
                    table_deps = defaultdict(set)
                    table_ops_map = {op.table_name: op for op in create_table_ops}

                    # Use metadata to find FK dependencies (only for tables in this schema)
                    for table in target_metadata.tables.values():
                        table_name = table.name
                        if table_name in table_ops_map:
                            table_deps[table_name] = set()

                            # Check all foreign keys
                            try:
                                for fk in table.foreign_keys:
                                    ref_table = fk.column.table.name
                                    # Only track dependencies if ref_table is also being created in this migration
                                    if ref_table != table_name and ref_table in table_ops_map:
                                        table_deps[table_name].add(ref_table)
                            except Exception:
                                # Skip FK processing if reference table not in metadata
                                pass

                    # Topologically sort tables by dependencies
                    ts = TopologicalSorter(table_deps)
                    sorted_tables = list(ts.static_order())

                    # Reorder create_table operations
                    sorted_create_ops = [
                        table_ops_map[t] for t in sorted_tables if t in table_ops_map
                    ]

                    # Replace operations with sorted version
                    script.upgrade_ops.ops = sorted_create_ops + other_ops

                    print(f"[DEBUG] After reordering: {len(script.upgrade_ops.ops)} operations")
                    logger.info(f"Reordered {len(sorted_create_ops)} tables by dependencies")

                except CycleError as e:
                    # Circular dependency detected - keep filtered ops
                    print(f"[DEBUG] CycleError: {e}, keeping filtered ops")
                    script.upgrade_ops.ops = create_table_ops + other_ops
                    logger.warning(f"Circular dependency detected: {e}")
                    logger.warning("Tables will be created in original order")

                except Exception as e:
                    # Other errors - keep filtered ops
                    print(f"[DEBUG] Exception in reordering: {e}")
                    import traceback

                    traceback.print_exc()
                    script.upgrade_ops.ops = create_table_ops + other_ops

        # Filter downgrade operations as well
        print(f"[DEBUG] Checking downgrade_ops: {script.downgrade_ops}")
        if script.downgrade_ops:
            print(f"[DEBUG] downgrade_ops exists, has {len(script.downgrade_ops.ops)} operations")
            downgrade_filtered = []
            for i, op in enumerate(script.downgrade_ops.ops):
                op_schema = getattr(op, "schema", None)
                op_type = type(op).__name__
                if i < 3:
                    print(
                        f"[DEBUG] Downgrade Op[{i}]: type={op_type}, schema={op_schema}, matches={op_schema == SCHEMA_NAME}"
                    )
                if op_schema == SCHEMA_NAME:
                    downgrade_filtered.append(op)
            script.downgrade_ops.ops = downgrade_filtered
            print(
                f"[DEBUG] Filtered downgrade to {len(downgrade_filtered)} operations for schema {SCHEMA_NAME}"
            )
        else:
            print("[DEBUG] No downgrade_ops to filter")


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema=SCHEMA_NAME,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Get database URL from environment or config
    database_url = (
        config.get_main_option("sqlalchemy.url")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("VENTURESTRAT_DATABASE_URL")
        or "postgresql://venturestrat:venturestrat@localhost/venturestrat"
    )

    # Escape % characters to avoid ConfigParser interpolation issues
    escaped_database_url = database_url.replace("%", "%%")
    config.set_main_option("sqlalchemy.url", escaped_database_url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=SCHEMA_NAME,
            compare_type=True,
            compare_server_default=True,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            # Set schema search path inside transaction
            connection.execute(text(f"SET search_path TO {SCHEMA_NAME}, public"))
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
