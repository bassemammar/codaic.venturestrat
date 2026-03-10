# Registry Service Multi-Tenant Migration

This directory contains the complete migration strategy and tooling for adding multi-tenant support to the VentureStrat Registry Service.

## Overview

The migration adds `tenant_id` fields to existing registry tables while preserving data integrity and ensuring zero-downtime deployment. All existing records are automatically assigned to the system tenant for backwards compatibility.

## Files Structure

```
services/registry-service/
├── migrations/
│   ├── 001_initial_schema.sql           # Original registry schema
│   ├── 002_add_tenant_table.sql         # Tenant table creation
│   └── 003_add_tenant_isolation.sql     # ✨ NEW: Tenant isolation migration
├── src/registry/
│   └── migration_service.py             # ✨ NEW: Python migration service
├── scripts/
│   └── migrate.py                       # ✨ NEW: CLI migration tool
├── tests/
│   └── test_migration_service.py        # ✨ NEW: Migration tests
├── migration_strategy.md                # ✨ NEW: Detailed strategy document
└── MIGRATION_README.md                  # ✨ NEW: This file
```

## Quick Start

### 1. Verify Prerequisites

Before running the migration, ensure:

- ✅ Database backup is available
- ✅ Registry service is running normally
- ✅ System tenant exists (from migration 002)
- ✅ Python dependencies are installed

```bash
# Backup database
pg_dump registry_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Verify system tenant
psql registry_db -c "SELECT id, slug, name FROM tenants WHERE slug = 'system';"
```

### 2. Dry Run Migration

Always perform a dry run first to validate the migration:

```bash
cd services/registry-service
python scripts/migrate.py migrate \
    --connection-url postgresql://user:pass@localhost/registry_db \
    --dry-run
```

Expected output:
```
🚀 Starting migration (dry_run=True)
──────────────────────────────────────────────────
✅ Dry run validation successful!

Pre-Migration Statistics:
  Service Registrations: 245
  Health Events: 1,532
  Dependencies: 12

Validation: ✅ All checks passed
```

### 3. Execute Migration

If dry run succeeds, execute the migration:

```bash
python scripts/migrate.py migrate \
    --connection-url postgresql://user:pass@localhost/registry_db
```

Expected output:
```
🚀 Starting migration (dry_run=False)
──────────────────────────────────────────────────
✅ Migration completed successfully!

Execution Time: 2.34 seconds

Record Migration Summary:
  service_registrations: 245 → 245 (245 in system tenant) ✅
  service_health_events: 1,532 → 1,532 (1,532 in system tenant) ✅
  service_dependencies: 12 → 12 (12 in system tenant) ✅

Constraints Added: 3
  - fk_service_registrations_tenant
  - fk_service_health_events_tenant
  - fk_service_dependencies_tenant

Indexes Added: 6
  - idx_service_registrations_tenant_id
  - idx_service_health_events_tenant_id
  - idx_service_dependencies_tenant_id
```

### 4. Verify Migration

Verify the migration was successful:

```bash
python scripts/migrate.py verify \
    --connection-url postgresql://user:pass@localhost/registry_db
```

Expected output:
```
🔍 Verifying migration status
──────────────────────────────────────────────────
✅ Migration verified successfully!
   All tenant columns and constraints are in place.

Schema Details:
  ✅ service_registrations
  ✅ service_health_events
  ✅ service_dependencies
```

## Migration Details

### What Changes Are Made

1. **Database Schema**
   - Adds `tenant_id UUID NOT NULL` to three tables
   - Sets default value to system tenant UUID
   - Adds foreign key constraints with `RESTRICT` on delete
   - Creates indexes for tenant-scoped queries

2. **Constraints**
   - `fk_service_registrations_tenant`
   - `fk_service_health_events_tenant`
   - `fk_service_dependencies_tenant`
   - Updated unique constraint on dependencies to include tenant

3. **Indexes**
   - Individual tenant indexes for filtering
   - Composite indexes for tenant + service queries
   - Covering indexes for performance optimization

4. **Views**
   - Updates `active_services` view to include `tenant_id`
   - Updates `service_uptime_24h` view to include `tenant_id`

### Tables Affected

| Table | Records | Change |
|-------|---------|---------|
| `service_registrations` | Preserved | +tenant_id, +indexes, +FK |
| `service_health_events` | Preserved | +tenant_id, +indexes, +FK |
| `service_dependencies` | Preserved | +tenant_id, +indexes, +FK |

### System Tenant Strategy

All existing records are assigned to the system tenant:
- **UUID:** `00000000-0000-0000-0000-000000000000`
- **Slug:** `system`
- **Purpose:** Backwards compatibility and platform services

## CLI Commands

### Check Status

```bash
python scripts/migrate.py status \
    --connection-url postgresql://user:pass@localhost/registry_db
```

### Rollback Migration

If you need to rollback the migration:

```bash
python scripts/migrate.py rollback \
    --connection-url postgresql://user:pass@localhost/registry_db
```

⚠️ **Warning:** Rollback will remove all tenant isolation. Use with caution.

## Programmatic API

You can also use the migration service directly in Python:

```python
from registry.migration_service import RegistryMigrationService

# Create service
service = RegistryMigrationService("postgresql://user:pass@localhost/registry_db")

# Execute migration
result = await service.execute_migration(dry_run=False)

# Verify migration
verify_result = await service.verify_migration()

# Rollback if needed
rollback_result = await service.rollback_migration()
```

## Testing

Run the comprehensive test suite:

```bash
# Unit tests
pytest services/registry-service/tests/test_migration_service.py -v

# Integration tests
pytest services/registry-service/tests/test_migration_service.py::TestMigrationIntegration -v
```

## Performance Impact

### Storage
- **Additional space:** ~16 bytes per record (UUID column)
- **Index overhead:** ~20% increase in index size
- **Constraint overhead:** Minimal

### Query Performance
- **Tenant-scoped queries:** Improved (uses tenant indexes)
- **Cross-tenant queries:** Require platform_admin role
- **Migration time:** ~2-5 seconds per 100K records

### Memory
- **Connection overhead:** None
- **Cache impact:** Minimal (new indexes may improve cache hit rate)

## Monitoring

### Key Metrics to Monitor

1. **Migration Execution Time**
   - Target: <30 seconds for typical workloads
   - Alert if >5 minutes

2. **Record Count Verification**
   - Pre/post migration counts must match exactly
   - Alert on any discrepancy

3. **Query Performance**
   - Monitor tenant-scoped queries
   - Alert if >2x baseline response time

4. **Constraint Violations**
   - Monitor foreign key violations
   - Alert on any constraint errors

### SQL Monitoring Queries

```sql
-- Verify all records have tenant_id
SELECT
  table_name,
  (SELECT COUNT(*) FROM service_registrations WHERE tenant_id IS NULL) as null_tenants
FROM information_schema.tables
WHERE table_name IN ('service_registrations', 'service_health_events', 'service_dependencies');

-- Check tenant distribution
SELECT
  t.slug,
  COUNT(sr.*) as registrations,
  COUNT(she.*) as health_events,
  COUNT(sd.*) as dependencies
FROM tenants t
LEFT JOIN service_registrations sr ON t.id = sr.tenant_id
LEFT JOIN service_health_events she ON t.id = she.tenant_id
LEFT JOIN service_dependencies sd ON t.id = sd.tenant_id
GROUP BY t.id, t.slug;

-- Query performance check
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM service_registrations
WHERE tenant_id = '00000000-0000-0000-0000-000000000000'
AND service_name = 'pricing-service';
```

## Troubleshooting

### Common Issues

1. **Migration Fails with Constraint Violation**
   ```
   Error: foreign key constraint violation
   ```

   **Solution:** Verify system tenant exists:
   ```sql
   SELECT * FROM tenants WHERE id = '00000000-0000-0000-0000-000000000000';
   ```

2. **Record Count Mismatch**
   ```
   Error: service_registrations: record count changed from 245 to 244
   ```

   **Solution:** Check for concurrent modifications during migration. Rollback and retry.

3. **Performance Degradation**
   ```
   Warning: Query response time >2x baseline
   ```

   **Solution:** Verify indexes were created:
   ```sql
   SELECT indexname FROM pg_indexes
   WHERE tablename LIKE 'service_%' AND indexname LIKE '%tenant%';
   ```

### Recovery Procedures

1. **If Migration Fails Mid-Execution**
   ```bash
   # Check current state
   python scripts/migrate.py status --connection-url <url>

   # Rollback if needed
   python scripts/migrate.py rollback --connection-url <url> --force

   # Restore from backup if necessary
   pg_restore -d registry_db backup_file.sql
   ```

2. **If Data Integrity Issues Found**
   ```bash
   # Immediate rollback
   python scripts/migrate.py rollback --connection-url <url> --force

   # Investigate root cause
   # Re-run migration with verbose logging
   python scripts/migrate.py migrate --connection-url <url> --verbose
   ```

## Next Steps

After successful migration:

1. **Service Integration**
   - Update registry service to use tenant context
   - Add tenant middleware to FastAPI app
   - Test tenant-scoped queries

2. **Documentation Updates**
   - Update API documentation
   - Add tenant examples to service docs
   - Update deployment guides

3. **Monitoring Setup**
   - Add tenant-specific metrics
   - Create tenant isolation dashboards
   - Set up alerting for constraint violations

## Support

For issues with the migration:

1. **Check logs:** Look in `migration.log` for detailed error information
2. **Run diagnostics:** Use `status` command to check current state
3. **Review strategy:** Read `migration_strategy.md` for detailed background
4. **Test in staging:** Always test migration in staging environment first

## Migration Checklist

Before production deployment:

- [ ] Database backup completed
- [ ] Dry run executed successfully in staging
- [ ] Performance impact assessed
- [ ] Rollback procedure tested
- [ ] Monitoring configured
- [ ] Team notified of maintenance window
- [ ] Emergency contacts available

During migration:

- [ ] Pre-migration statistics collected
- [ ] Migration executed successfully
- [ ] Post-migration verification passed
- [ ] Query performance validated
- [ ] Service functionality tested

Post-migration:

- [ ] Migration marked as complete in tracking
- [ ] Documentation updated
- [ ] Team notified of completion
- [ ] Follow-up monitoring scheduled
